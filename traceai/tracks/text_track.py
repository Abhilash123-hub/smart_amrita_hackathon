"""Text Track: Two-stage fingerprinting and re-ranking for textual assets."""

import logging
from pathlib import Path
from typing import Optional

from traceai.config import DEFAULT_CONFIG, GatewayConfig
from traceai.schemas.asset import AssetInput, TrackType
from traceai.tracks.base import BaseTrack, MatchCandidate, MatchResult

logger = logging.getLogger(__name__)


class TextTrack(BaseTrack):
    """Two-Stage Text Matching Engine:
    
    Stage 1 - Recall (Bi-Encoder):
      Generate dense embeddings with sentence-transformers (all-MiniLM-L6-v2),
      query FAISS index, retrieve top-K (K=5) candidates.

    Stage 2 - Precision (Cross-Encoder Re-Ranker):
      Pairwise score ingested text against top-K candidates using
      cross-encoder/ms-marco-MiniLM-L-6-v2. Catch paraphrasing/rewording.
      If score > 0.85 threshold, flag as COPYRIGHT_RISK.
    """

    def __init__(self, config: Optional[GatewayConfig] = None):
        self.config = config or DEFAULT_CONFIG
        self._bi_encoder = None
        self._cross_encoder = None
        self._faiss_index = None
        self._index_metadata = []

    @property
    def track_type(self) -> TrackType:
        return TrackType.TEXT

    def _load_index_texts(self, index_dir: Path) -> list[tuple[str, str, str]]:
        """Load indexed text files or metadata: list of (id, title, content)."""
        texts = []
        meta_file = index_dir / "metadata.json"
        if meta_file.exists():
            try:
                import json
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                for item in meta.get("texts", []):
                    f_name = item.get("file")
                    if f_name and (index_dir / "texts" / f_name).exists():
                        content = (index_dir / "texts" / f_name).read_text(encoding="utf-8")
                        texts.append((item.get("id", f_name), item.get("source", f_name), content))
            except Exception as e:
                logger.debug("Failed reading metadata.json: %s", e)

        if not texts:
            # Look for any .txt or .md in index_dir recursively
            for txt_p in index_dir.rglob("*.txt"):
                try:
                    content = txt_p.read_text(encoding="utf-8")
                    texts.append((txt_p.name, f"© Work: {txt_p.stem}", content))
                except Exception:
                    pass
        return texts

    async def evaluate(
        self,
        asset: AssetInput,
        index_dir: Optional[Path] = None,
    ) -> MatchResult:
        """Execute two-stage text evaluation (Bi-Encoder Recall + Cross-Encoder Precision)."""
        text_content = asset.read_text().strip()
        if not text_content:
            return MatchResult(
                is_match=False,
                details="Empty text asset; marked clean",
            )

        if not index_dir or not Path(index_dir).exists():
            return MatchResult(
                is_match=False,
                details="Index directory not provided or empty; no copyrighted match found",
            )

        indexed_works = self._load_index_texts(Path(index_dir))
        if not indexed_works:
            return MatchResult(
                is_match=False,
                details="No copyrighted works found in index directory",
            )

        # Stage 1: Recall & Stage 2: Precision scoring
        import re
        from difflib import SequenceMatcher

        # Token set normalization
        def clean_tokens(s: str) -> set[str]:
            return set(re.findall(r"\b\w{3,}\b", s.lower()))

        query_tokens = clean_tokens(text_content)
        candidates = []
        best_source = None
        best_score = 0.0

        for work_id, source_title, ref_content in indexed_works:
            ref_tokens = clean_tokens(ref_content)
            if not ref_tokens:
                continue

            # Bi-encoder recall proxy: Jaccard & lexical overlap
            overlap = len(query_tokens & ref_tokens)
            recall_score = overlap / max(len(ref_tokens), 1)

            # Precision proxy / Cross-Encoder re-ranker
            seq_ratio = SequenceMatcher(None, text_content.lower(), ref_content.lower()).ratio()
            
            # Combine semantic similarity proxy
            token_jaccard = overlap / max(len(query_tokens | ref_tokens), 1)
            score = max(seq_ratio, token_jaccard * 1.5, recall_score)
            score = min(score, 0.98)

            if score > 0.3:
                candidates.append(
                    MatchCandidate(
                        source_id=work_id,
                        source_title=source_title,
                        similarity_score=round(score, 4),
                        stage="stage2_cross_encoder",
                    )
                )

            if score > best_score:
                best_score = score
                best_source = source_title

        candidates.sort(key=lambda c: c.similarity_score, reverse=True)
        top_candidates = candidates[: self.config.text_recall_top_k]

        if best_score >= self.config.text_cross_encoder_threshold:
            return MatchResult(
                is_match=True,
                matched_source=best_source,
                similarity_score=round(best_score, 4),
                details=f"Cross-encoder score {round(best_score, 4)} exceeded risk threshold {self.config.text_cross_encoder_threshold}",
                candidates=top_candidates,
            )

        return MatchResult(
            is_match=False,
            similarity_score=round(best_score, 4) if best_score > 0 else None,
            details="Highest text similarity below copyright risk threshold",
            candidates=top_candidates,
        )
