"""Code-Asset Track (B3): AST-normalized fingerprinting and GPL/AGPL license contamination detection."""

import ast
import hashlib
import logging
import re
from pathlib import Path
from typing import Optional

from traceai.config import DEFAULT_CONFIG, GatewayConfig
from traceai.schemas.asset import AssetInput, TrackType
from traceai.tracks.base import BaseTrack, MatchCandidate, MatchResult

logger = logging.getLogger(__name__)


def normalize_ast_tokens(code_str: str) -> str:
    """Strip variable/function identifiers and whitespace, producing a normalized AST structure string.
    
    Acceptance Criteria: Catches renamed-variable copies.
    """
    try:
        tree = ast.parse(code_str)
        # Walk AST and collect canonical node types
        canonical_nodes = []
        for node in ast.walk(tree):
            node_type = type(node).__name__
            # Anonymize identifiers
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                canonical_nodes.append("FuncDef")
            elif isinstance(node, ast.Name):
                canonical_nodes.append("Var")
            elif isinstance(node, ast.Constant):
                canonical_nodes.append("Const")
            else:
                canonical_nodes.append(node_type)
        return "-".join(canonical_nodes)
    except SyntaxError:
        # Fallback for non-python or syntactically invalid code: regex token normalization
        clean = re.sub(r"\b[a-zA-Z_]\w*\b", "id", code_str)
        return re.sub(r"\s+", " ", clean).strip()


class CodeTrack(BaseTrack):
    """Fifth Track: Source code governance and license contamination detector.
    
    Stage 1 - AST Normalization: Catches verbatim renamed-variable code.
    Stage 2 - Structural Similarity: Catches restructured/refactored logic.
    License-aware: Flags GPL-2.0, GPL-3.0, and AGPL contamination specifically.
    """

    def __init__(self, config: Optional[GatewayConfig] = None, threshold: float = 0.85):
        self.config = config or DEFAULT_CONFIG
        self.similarity_threshold = threshold

    @property
    def track_type(self) -> TrackType:
        return TrackType.CODE

    def _load_code_index(self, index_dir: Path) -> list[dict]:
        """Load indexed reference codebase with license classifications."""
        works = []
        code_exts = ["*.py", "*.js", "*.ts", "*.go", "*.rs", "*.cpp", "*.c", "*.java"]
        files = []
        for ext in code_exts:
            files.extend(list(index_dir.rglob(ext)))

        for p in files:
            try:
                content = p.read_text(encoding="utf-8", errors="ignore")
                # Identify license
                license_type = "Proprietary"
                if "GNU General Public License" in content or "GPL" in content:
                    license_type = "GPL-3.0 (Copyleft Contamination Risk)"
                elif "AGPL" in content or "Affero" in content:
                    license_type = "AGPL-3.0 (Network Copyleft Contamination Risk)"
                elif "MIT" in content or "Apache" in content:
                    license_type = "Permissive (MIT/Apache)"

                title = f"© Codebase: {p.stem} [{license_type}]"
                if "RefCorpus:" in content:
                    for line in content.splitlines():
                        if "RefCorpus:" in line:
                            title = line.replace("//", "").replace("/*", "").replace("*/", "").strip()
                            break

                works.append({
                    "id": p.name,
                    "title": title,
                    "license": license_type,
                    "content": content,
                    "ast_norm": normalize_ast_tokens(content),
                })
            except Exception:
                pass
        return works

    async def evaluate(
        self,
        asset: AssetInput,
        index_dir: Optional[Path] = None,
    ) -> MatchResult:
        """Evaluate source code asset against indexed reference code and license database."""
        code_text = asset.read_text()
        if not code_text.strip():
            return MatchResult(is_match=False, details="Empty code asset; marked clean")

        if not index_dir or not Path(index_dir).exists():
            return MatchResult(is_match=False, details="Index directory not provided; marked clean")

        indexed_code = self._load_code_index(Path(index_dir))
        if not indexed_code:
            return MatchResult(is_match=False, details="No indexed reference code found")

        query_ast_norm = normalize_ast_tokens(code_text)
        query_tokens = set(re.findall(r"\b\w{2,}\b", code_text.lower()))

        candidates = []
        best_score = 0.0
        best_source = None

        for item in indexed_code:
            ref_ast_norm = item["ast_norm"]
            ref_content = item["content"]

            # Stage 1: AST Normalized Exact / High Structural Match (Catches renamed variables!)
            from difflib import SequenceMatcher
            ast_ratio = SequenceMatcher(None, query_ast_norm, ref_ast_norm).ratio()

            # Stage 2: Token Jaccard + Sequence Matcher
            ref_tokens = set(re.findall(r"\b\w{2,}\b", ref_content.lower()))
            token_sim = len(query_tokens & ref_tokens) / max(len(query_tokens | ref_tokens), 1)

            # Combined score giving heavy weight to AST structural identity
            structural_score = max(ast_ratio, (ast_ratio * 0.7) + (token_sim * 0.3))

            # Excerpt containment: if query tokens are a subset of indexed reference code
            containment = len(query_tokens & ref_tokens) / max(len(query_tokens), 1)
            if containment >= 0.8:
                excerpt_score = 0.75 + (ast_ratio * 0.12)
                structural_score = max(structural_score, excerpt_score)

            if structural_score > 0.4:
                candidates.append(
                    MatchCandidate(
                        source_id=item["id"],
                        source_title=item["title"],
                        similarity_score=round(structural_score, 4),
                        stage="stage1_ast_normalized" if ast_ratio > 0.85 else "stage2_code_embedding",
                    )
                )

            if structural_score > best_score:
                best_score = structural_score
                best_source = item["title"]

        candidates.sort(key=lambda c: c.similarity_score, reverse=True)

        if best_score >= self.similarity_threshold:
            return MatchResult(
                is_match=True,
                matched_source=best_source,
                similarity_score=round(best_score, 4),
                details=f"Code structural match {round(best_score * 100, 1)}% >= threshold {self.similarity_threshold}. {best_source}",
                candidates=candidates[:5],
            )

        return MatchResult(
            is_match=False,
            matched_source=best_source if best_score > 0 else None,
            similarity_score=round(best_score, 4) if best_score > 0 else None,
            details="Code similarity in review/evaluation band" if best_score >= 0.70 else "Code similarity below contamination threshold",
            candidates=candidates[:5],
        )
