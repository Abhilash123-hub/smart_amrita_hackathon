"""Ingestion Gateway: Asset discovery, byte inspection, track routing, and cryptographic resolution."""

import asyncio
import logging
import time
from pathlib import Path
from typing import Optional

from traceai.config import DEFAULT_CONFIG, GatewayConfig
from traceai.crypto.lineage import build_prov_lineage
from traceai.crypto.signer import CryptoSigner
from traceai.schemas.asset import AssetInput, TrackType
from traceai.schemas.certificate import ClearanceCertificate
from traceai.schemas.report import AssetEvaluation, AssetStatus, ScanReport, ScanSummary
from traceai.tracks.image_track import ImageTrack
from traceai.tracks.text_track import TextTrack

logger = logging.getLogger(__name__)


class IngestionGateway:
    """Core gateway orchestrator for multimodal ingestion and copyright clearance."""

    def __init__(
        self,
        config: Optional[GatewayConfig] = None,
        signer: Optional[CryptoSigner] = None,
        text_track: Optional[TextTrack] = None,
        image_track: Optional[ImageTrack] = None,
    ):
        self.config = config or DEFAULT_CONFIG
        self.signer = signer or CryptoSigner()
        self.text_track = text_track or TextTrack(self.config)
        self.image_track = image_track or ImageTrack(self.config)

    def discover_assets(self, target_path: Path | str) -> list[AssetInput]:
        """Traverse directory or single file, inspect bytes, and instantiate AssetInputs."""
        path = Path(target_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Input path does not exist: {path}")

        assets: list[AssetInput] = []
        files_to_scan = [path] if path.is_file() else sorted([p for p in path.rglob("*") if p.is_file()])
        base_dir = path if path.is_dir() else path.parent

        for file_p in files_to_scan:
            try:
                asset = AssetInput.from_file(file_p, base_dir=base_dir)
                if asset.track != TrackType.UNSUPPORTED:
                    assets.append(asset)
                else:
                    logger.warning("Skipping unsupported file type: %s (mime: %s)", file_p.name, asset.mime_type)
            except Exception as e:
                logger.error("Failed to inspect asset %s: %s", file_p, e)

        return assets

    async def _evaluate_single_asset(
        self,
        asset: AssetInput,
        index_dir: Optional[Path] = None,
    ) -> AssetEvaluation:
        """Evaluate a single asset through its designated track and resolve clearance."""
        try:
            if asset.track == TrackType.TEXT:
                match = await self.text_track.evaluate(asset, index_dir)
            elif asset.track == TrackType.IMAGE:
                match = await self.image_track.evaluate(asset, index_dir)
            else:
                return AssetEvaluation(
                    asset_id=asset.asset_id,
                    status=AssetStatus.ERROR,
                    track=asset.track,
                    asset_hash=asset.sha256_hash,
                    details=f"Unsupported track modality: {asset.track}",
                )

            if match.is_match:
                # Copyright risk identified: Block asset
                lineage = build_prov_lineage(
                    asset=asset,
                    status="BLOCKED",
                    matched_source=match.matched_source,
                    similarity_score=match.similarity_score,
                    certificate_id=None,
                )
                return AssetEvaluation(
                    asset_id=asset.asset_id,
                    status=AssetStatus.BLOCKED,
                    track=asset.track,
                    matched_source=match.matched_source,
                    similarity_score=match.similarity_score,
                    asset_hash=asset.sha256_hash,
                    certificate_id=None,
                    lineage=lineage,
                    details=match.details,
                )
            else:
                # Clean asset: Issue cryptographic clearance certificate
                certificate = self.signer.issue_certificate(asset.asset_id, asset.sha256_hash)
                lineage = build_prov_lineage(
                    asset=asset,
                    status="PASSED",
                    matched_source=None,
                    similarity_score=None,
                    certificate_id=certificate.certificate_id,
                )
                return AssetEvaluation(
                    asset_id=asset.asset_id,
                    status=AssetStatus.PASSED,
                    track=asset.track,
                    matched_source=None,
                    similarity_score=None,
                    asset_hash=asset.sha256_hash,
                    certificate_id=certificate.certificate_id,
                    certificate=certificate,
                    lineage=lineage,
                    details=match.details,
                )

        except Exception as e:
            logger.exception("Error during asset evaluation %s: %s", asset.asset_id, e)
            return AssetEvaluation(
                asset_id=asset.asset_id,
                status=AssetStatus.ERROR,
                track=asset.track,
                asset_hash=asset.sha256_hash,
                details=f"Evaluation exception: {str(e)}",
            )

    async def scan(
        self,
        input_path: Path | str,
        index_dir: Optional[Path | str] = None,
    ) -> ScanReport:
        """Scan target files/directory asynchronously and assemble the clearance report."""
        start_time = time.perf_counter()
        target = Path(input_path).resolve()
        idx = Path(index_dir).resolve() if index_dir else None

        assets = self.discover_assets(target)
        
        # Execute Text and Image track evaluations asynchronously
        tasks = [self._evaluate_single_asset(asset, idx) for asset in assets]
        evaluations: list[AssetEvaluation] = await asyncio.gather(*tasks)

        duration = round(time.perf_counter() - start_time, 4)

        passed = sum(1 for e in evaluations if e.status == AssetStatus.PASSED)
        blocked = sum(1 for e in evaluations if e.status == AssetStatus.BLOCKED)
        errors = sum(1 for e in evaluations if e.status == AssetStatus.ERROR)

        summary = ScanSummary(
            total_assets=len(evaluations),
            passed_count=passed,
            blocked_count=blocked,
            error_count=errors,
            duration_seconds=duration,
        )

        return ScanReport(
            input_directory=str(target),
            index_directory=str(idx) if idx else None,
            summary=summary,
            results=evaluations,
        )
