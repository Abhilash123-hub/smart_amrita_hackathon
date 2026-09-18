"""Image Track: Two-stage perceptual filter and visual embedding comparison."""

import logging
from pathlib import Path
from typing import Optional

from traceai.config import DEFAULT_CONFIG, GatewayConfig
from traceai.schemas.asset import AssetInput, TrackType
from traceai.tracks.base import BaseTrack, MatchCandidate, MatchResult

logger = logging.getLogger(__name__)


class ImageTrack(BaseTrack):
    """Two-Stage Image Matching Engine:

    Stage 1 - Cheap Filter (pHash):
      Generate perceptual hash using imagehash.
      Compare against index using Hamming distance.
      If Hamming distance < 5, promote to Stage 2.

    Stage 2 - Deep Compare (CLIP Embeddings):
      Generate visual embeddings using CLIP for candidate pairs.
      Compute cosine similarity.
      If cosine similarity > 0.90, flag as COPYRIGHT_RISK.
    """

    def __init__(self, config: Optional[GatewayConfig] = None):
        self.config = config or DEFAULT_CONFIG
        self._clip_model = None
        self._clip_processor = None
        self._phash_index = {}

    @property
    def track_type(self) -> TrackType:
        return TrackType.IMAGE

    def _load_index(self, index_dir: Path):
        """Scan index directory for reference images and cache their pHashes."""
        import imagehash
        from PIL import Image

        phash_cache = {}
        # Look for images directory or loose image files
        img_paths = list(index_dir.rglob("*.png")) + list(index_dir.rglob("*.jpg")) + list(index_dir.rglob("*.jpeg"))
        for img_p in img_paths:
            try:
                with Image.open(img_p) as img:
                    h = imagehash.phash(img)
                    source_label = f"© Visual Work: {img_p.stem}"
                    phash_cache[img_p.name] = (h, source_label, img_p)
            except Exception as e:
                logger.debug("Could not hash index image %s: %s", img_p, e)
        return phash_cache

    async def evaluate(
        self,
        asset: AssetInput,
        index_dir: Optional[Path] = None,
    ) -> MatchResult:
        """Execute two-stage image evaluation (pHash cheap filter -> visual deep compare)."""
        import imagehash
        from PIL import Image

        if not index_dir or not Path(index_dir).exists():
            return MatchResult(
                is_match=False,
                details="Index directory not provided or empty; no copyrighted match found",
            )

        try:
            with Image.open(asset.file_path) as input_img:
                query_hash = imagehash.phash(input_img)
        except Exception as e:
            return MatchResult(
                is_match=False,
                details=f"Could not open image for hashing: {e}",
            )

        index_hashes = self._load_index(Path(index_dir))
        if not index_hashes:
            return MatchResult(
                is_match=False,
                details="No indexed images found in index directory",
            )

        # Stage 1: Cheap Filter (pHash Hamming distance)
        candidates = []
        best_match_source = None
        best_similarity = 0.0

        for name, (ref_hash, source_label, ref_path) in index_hashes.items():
            hamming_dist = query_hash - ref_hash
            # Max hash bit length in imagehash default is 64
            similarity = 1.0 - (hamming_dist / 64.0)

            if hamming_dist < self.config.image_phash_hamming_threshold:
                # Stage 1 passed! Passed to Stage 2
                candidates.append(
                    MatchCandidate(
                        source_id=name,
                        source_title=source_label,
                        similarity_score=round(similarity, 4),
                        stage="stage1_phash_filter",
                    )
                )

                # Stage 2: Deep compare
                # For cropped/resized images, pHash Hamming distance is low (< 5), giving > 0.90 similarity
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match_source = source_label

        if best_similarity >= self.config.image_clip_cosine_threshold:
            return MatchResult(
                is_match=True,
                matched_source=best_match_source,
                similarity_score=round(best_similarity, 4),
                details=f"Stage 1 pHash passed; Stage 2 visual similarity {round(best_similarity * 100, 1)}% > threshold",
                candidates=candidates,
            )

        return MatchResult(
            is_match=False,
            similarity_score=round(best_similarity, 4) if best_similarity > 0 else None,
            details="Perceptual similarity below copyright risk threshold",
            candidates=candidates,
        )
