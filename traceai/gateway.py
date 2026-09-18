"""Ingestion Gateway: Asset discovery, byte inspection, multimodal routing, dedup, and clearance resolution."""

import asyncio
import logging
import time
from pathlib import Path
from typing import Optional

from traceai.config import DEFAULT_CONFIG, GatewayConfig
from traceai.crypto.lineage import build_prov_lineage
from traceai.crypto.signer import CryptoSigner
from traceai.governance.blockchain import BlockchainLedger
from traceai.governance.confidence_router import ConfidenceBandRouter
from traceai.governance.dmca import DmcaIndexManager
from traceai.governance.rules_engine import JurisdictionRulesEngine
from traceai.schemas.asset import AssetInput, TrackType
from traceai.schemas.certificate import ClearanceCertificate
from traceai.schemas.report import AssetEvaluation, AssetStatus, ScanReport, ScanSummary
from traceai.tracks.audio_track import AudioTrack
from traceai.tracks.code_track import CodeTrack
from traceai.tracks.image_track import ImageTrack
from traceai.tracks.text_track import TextTrack
from traceai.tracks.video_track import VideoTrack
from traceai.web_ingestion.dedup import ChangeAwareDedup

logger = logging.getLogger(__name__)


class IngestionGateway:
    """Enterprise gateway orchestrating multimodal ingestion, change-aware dedup, and tri-band resolution."""

    def __init__(
        self,
        config: Optional[GatewayConfig] = None,
        signer: Optional[CryptoSigner] = None,
        text_track: Optional[TextTrack] = None,
        image_track: Optional[ImageTrack] = None,
        audio_track: Optional[AudioTrack] = None,
        video_track: Optional[VideoTrack] = None,
        code_track: Optional[CodeTrack] = None,
        dedup_gate: Optional[ChangeAwareDedup] = None,
        confidence_router: Optional[ConfidenceBandRouter] = None,
        rules_engine: Optional[JurisdictionRulesEngine] = None,
        blockchain_ledger: Optional[BlockchainLedger] = None,
        dmca_manager: Optional[DmcaIndexManager] = None,
    ):
        self.config = config or DEFAULT_CONFIG
        self.signer = signer or CryptoSigner()
        self.text_track = text_track or TextTrack(self.config)
        self.image_track = image_track or ImageTrack(self.config)
        self.audio_track = audio_track or AudioTrack(self.config)
        self.video_track = video_track or VideoTrack(self.config, image_track=self.image_track)
        self.code_track = code_track or CodeTrack(self.config)

        self.dedup_gate = dedup_gate or ChangeAwareDedup()
        self.confidence_router = confidence_router or ConfidenceBandRouter()
        self.rules_engine = rules_engine or JurisdictionRulesEngine()
        self.blockchain_ledger = blockchain_ledger or BlockchainLedger()
        self.dmca_manager = dmca_manager or DmcaIndexManager()

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
        jurisdiction: str = "GLOBAL",
    ) -> AssetEvaluation:
        """Evaluate a single asset through dedup gate, designated modal track, rules, and confidence band."""
        try:
            # 1. Change-Aware Dedup Gate (A5 pre-fingerprint cost gate)
            is_dup, prior_status, prior_cert_id, prior_source, dup_sim = self.dedup_gate.check_dedup(asset)
            if is_dup and prior_status == AssetStatus.PASSED:
                # Shortcut to certificate issuance without re-running Stage 2
                cert = self.signer.issue_certificate(asset.asset_id, asset.sha256_hash)
                lineage = build_prov_lineage(
                    asset=asset,
                    status="PASSED",
                    certificate_id=cert.certificate_id,
                    activity_name="TraceAI-Dedup-FastPath",
                )
                return AssetEvaluation(
                    asset_id=asset.asset_id,
                    status=AssetStatus.PASSED,
                    track=asset.track,
                    matched_source=None,
                    similarity_score=None,
                    asset_hash=asset.sha256_hash,
                    certificate_id=cert.certificate_id,
                    certificate=cert,
                    lineage=lineage,
                    details=f"A5 Dedup hit: Bypassed Stage 2 (matches previously cleared asset with similarity {dup_sim})",
                    risk_band="CLEAR",
                )
            elif is_dup and prior_status == AssetStatus.BLOCKED:
                # Shortcut to BLOCKED
                lineage = build_prov_lineage(
                    asset=asset,
                    status="BLOCKED",
                    matched_source=prior_source,
                    similarity_score=dup_sim,
                    activity_name="TraceAI-Dedup-FastPath",
                )
                return AssetEvaluation(
                    asset_id=asset.asset_id,
                    status=AssetStatus.BLOCKED,
                    track=asset.track,
                    matched_source=prior_source,
                    similarity_score=dup_sim,
                    asset_hash=asset.sha256_hash,
                    certificate_id=None,
                    lineage=lineage,
                    details="A5 Dedup hit: Bypassed Stage 2 (matches previously blocked copyright)",
                    risk_band="BLOCKED",
                )

            # 2. Dispatch to designated modal track
            if asset.track == TrackType.TEXT:
                match = await self.text_track.evaluate(asset, index_dir)
            elif asset.track == TrackType.IMAGE:
                match = await self.image_track.evaluate(asset, index_dir)
            elif asset.track == TrackType.AUDIO:
                match = await self.audio_track.evaluate(asset, index_dir)
            elif asset.track == TrackType.VIDEO:
                match = await self.video_track.evaluate(asset, index_dir)
            elif asset.track == TrackType.CODE:
                match = await self.code_track.evaluate(asset, index_dir)
            else:
                return AssetEvaluation(
                    asset_id=asset.asset_id,
                    status=AssetStatus.ERROR,
                    track=asset.track,
                    asset_hash=asset.sha256_hash,
                    details=f"Unsupported track modality: {asset.track}",
                )

            # 3. Confidence-Band Routing (B4)
            band, initial_status = self.confidence_router.route_asset(
                asset=asset,
                match=match,
                trust_tier=asset.source_trust_tier,
            )

            # 4. Jurisdiction-Aware Rules Engine (B12)
            is_tdm_opted_out = bool(asset.prefilter_decision and asset.prefilter_decision.get("tdm_opted_out"))
            final_outcome, matched_rule_id = self.rules_engine.evaluate_jurisdiction(
                jurisdiction=jurisdiction,
                confidence_score=match.similarity_score or 0.0,
                tdm_opted_out=is_tdm_opted_out,
                trust_tier=asset.source_trust_tier,
                default_outcome=initial_status.value,
            )
            final_status = AssetStatus(final_outcome)

            # 5. Resolution & Cryptography
            if final_status == AssetStatus.BLOCKED:
                lineage = build_prov_lineage(
                    asset=asset,
                    status="BLOCKED",
                    matched_source=match.matched_source,
                    similarity_score=match.similarity_score,
                    certificate_id=None,
                    jurisdiction=jurisdiction,
                )
                self.dedup_gate.record_evaluation(
                    asset=asset,
                    status=AssetStatus.BLOCKED,
                    matched_source=match.matched_source,
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
                    details=f"{match.details or ''} [Rule: {matched_rule_id or 'Model Threshold'}]",
                    risk_band="BLOCKED",
                )

            elif final_status == AssetStatus.HUMAN_REVIEW:
                lineage = build_prov_lineage(
                    asset=asset,
                    status="HUMAN_REVIEW",
                    matched_source=match.matched_source,
                    similarity_score=match.similarity_score,
                    certificate_id=None,
                    jurisdiction=jurisdiction,
                )
                return AssetEvaluation(
                    asset_id=asset.asset_id,
                    status=AssetStatus.HUMAN_REVIEW,
                    track=asset.track,
                    matched_source=match.matched_source,
                    similarity_score=match.similarity_score,
                    asset_hash=asset.sha256_hash,
                    certificate_id=None,
                    lineage=lineage,
                    details=f"Mid-confidence match ({match.similarity_score}) queued for human review. [Rule: {matched_rule_id or 'B4 Band'}]",
                    risk_band="HUMAN_REVIEW",
                )

            else:
                # Clean asset: Issue cryptographic clearance certificate
                certificate = self.signer.issue_certificate(asset.asset_id, asset.sha256_hash)
                certificate.confidence_score = match.similarity_score
                certificate.jurisdiction = jurisdiction

                # Anchor to optional blockchain ledger (B8)
                tx_id = self.blockchain_ledger.anchor_certificate(
                    certificate_id=certificate.certificate_id,
                    asset_hash=certificate.asset_hash,
                    signature_b64=certificate.signature_b64,
                )
                certificate.blockchain_tx_id = tx_id

                lineage = build_prov_lineage(
                    asset=asset,
                    status="PASSED",
                    matched_source=None,
                    similarity_score=None,
                    certificate_id=certificate.certificate_id,
                    jurisdiction=jurisdiction,
                )

                # Record in dedup gate & DMCA registry
                self.dedup_gate.record_evaluation(
                    asset=asset,
                    status=AssetStatus.PASSED,
                    certificate_id=certificate.certificate_id,
                )
                self.dmca_manager.register_cleared_asset(asset, status="PASSED")

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
                    risk_band="CLEAR",
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
        jurisdiction: str = "GLOBAL",
    ) -> ScanReport:
        """Scan target files/directory asynchronously across all modal tracks and assemble clearance report."""
        start_time = time.perf_counter()
        target = Path(input_path).resolve()
        idx = Path(index_dir).resolve() if index_dir else None

        assets = self.discover_assets(target)

        # Concurrently evaluate all discovered assets across modal tracks
        tasks = [self._evaluate_single_asset(asset, idx, jurisdiction=jurisdiction) for asset in assets]
        evaluations: list[AssetEvaluation] = await asyncio.gather(*tasks)

        duration = round(time.perf_counter() - start_time, 4)

        passed = sum(1 for e in evaluations if e.status == AssetStatus.PASSED)
        blocked = sum(1 for e in evaluations if e.status == AssetStatus.BLOCKED)
        reviews = sum(1 for e in evaluations if e.status == AssetStatus.HUMAN_REVIEW)
        errors = sum(1 for e in evaluations if e.status == AssetStatus.ERROR)

        summary = ScanSummary(
            total_assets=len(evaluations),
            passed_count=passed,
            blocked_count=blocked,
            review_count=reviews,
            error_count=errors,
            duration_seconds=duration,
        )

        return ScanReport(
            input_directory=str(target),
            index_directory=str(idx) if idx else None,
            summary=summary,
            results=evaluations,
        )
