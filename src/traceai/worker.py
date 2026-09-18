"""Async Batch Pipeline Worker for TraceAI Gateway (Task Card T1.7)."""

import asyncio
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.traceai.config import DEFAULT_CONFIG, GatewayConfig
from src.traceai.core.models import AssetInput, IngestRequest, ScanResult, Track, Verdict
from src.traceai.pipelines.text_track import TextTrackPipeline
from src.traceai.pipelines.image_track import ImageTrackPipeline


class BatchWorker:
    """Dispatches assets by MIME type to Text and Image pipeline tracks."""

    def __init__(self, config: Optional[GatewayConfig] = None, index_dir: Optional[Path] = None):
        self.config = config or DEFAULT_CONFIG
        self.index_dir = index_dir or Path("mock_data/copyright_index")
        self.text_pipeline = TextTrackPipeline(config=self.config)
        self.image_pipeline = ImageTrackPipeline(config=self.config)
        self._load_phash_seed_dictionary()

    def _load_phash_seed_dictionary(self):
        """Batch-load the 50-image seed dictionary at worker start (T1.4)."""
        import imagehash
        from PIL import Image
        img_dir = self.index_dir / "images"
        if img_dir.exists():
            phash_map = {}
            for p in list(img_dir.glob("*.png")) + list(img_dir.glob("*.jpg")):
                try:
                    with Image.open(p) as im:
                        phash_map[p.name] = str(imagehash.phash(im))
                except Exception:
                    pass
            self.image_pipeline.cache.load_dictionary(phash_map)

    def process_asset(self, asset: AssetInput, raw_bytes: bytes) -> ScanResult:
        """Process a single asset synchronously or in a thread pool."""
        asset_hash = f"sha256:{hashlib.sha256(raw_bytes).hexdigest()}"
        now = datetime.now(timezone.utc)

        # Dispatch by MIME
        if asset.mime_type in ("text/plain", "application/pdf"):
            text_content = raw_bytes.decode("utf-8", errors="replace")
            # Load text corpus from index
            text_corpus = []
            text_dir = self.index_dir / "texts"
            if text_dir.exists():
                for p in text_dir.glob("*.txt"):
                    text_corpus.append((p.name, p.read_text(encoding="utf-8", errors="replace")))

            verdict, score, matched_source, telemetry = self.text_pipeline.evaluate_text(
                text=text_content,
                candidate_corpus=text_corpus,
                asset_id=asset.asset_id,
            )
            return ScanResult(
                asset_id=asset.asset_id,
                track=Track.TEXT,
                verdict=verdict,
                score=min(max(score, 0.0), 1.0),
                matched_source=matched_source,
                asset_hash=asset_hash,
                evidence_uri=None,
                scanned_at=now,
            )

        elif asset.mime_type in ("image/png", "image/jpeg", "image/webp"):
            import io
            from PIL import Image
            img = Image.open(io.BytesIO(raw_bytes))
            img_dir = self.index_dir / "images"

            verdict, score, matched_source, telemetry = self.image_pipeline.evaluate_image(
                img=img,
                ref_images_dir=img_dir,
                asset_id=asset.asset_id,
            )
            return ScanResult(
                asset_id=asset.asset_id,
                track=Track.IMAGE,
                verdict=verdict,
                score=min(max(score, 0.0), 1.0),
                matched_source=matched_source,
                asset_hash=asset_hash,
                evidence_uri=None,
                scanned_at=now,
            )

        # Unsupported fallback
        return ScanResult(
            asset_id=asset.asset_id,
            track=Track.TEXT,
            verdict=Verdict.PASSED,
            score=0.0,
            matched_source=None,
            asset_hash=asset_hash,
            evidence_uri=None,
            scanned_at=now,
        )
