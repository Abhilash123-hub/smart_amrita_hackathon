"""Vector Index Store with FAISS HNSW and Inner-Product Normalization (Task Card T1.2, T4.1)."""

import json
import os
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional
import numpy as np

try:
    import faiss
    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False


class BaseIndexStore(ABC):
    """Abstract 5-method interface for vector index backends (FAISS in Phase 1, Milvus in Phase 4)."""

    @abstractmethod
    def add(self, vectors: np.ndarray, metadata: list[dict[str, Any]]) -> None:
        """Add dense embedding vectors with associated metadata."""
        pass

    @abstractmethod
    def search(self, query_vectors: np.ndarray, top_k: int = 5) -> list[list[tuple[float, dict[str, Any]]]]:
        """Search top-K most similar vectors (cosine / inner-product)."""
        pass

    @abstractmethod
    def save(self, filepath: Path | str) -> None:
        """Persist index state and metadata to disk."""
        pass

    @abstractmethod
    def load(self, filepath: Path | str) -> None:
        """Load index state and metadata from disk."""
        pass

    @abstractmethod
    def count(self) -> int:
        """Return total number of vectors in index."""
        pass


class FAISSIndexStore(BaseIndexStore):
    """FAISS HNSW vector index implementation with L2 inner-product normalization."""

    def __init__(self, dimension: int = 384, m: int = 32, ef_search: int = 64):
        self.dimension = dimension
        self.m = m
        self.ef_search = ef_search
        self.metadata: list[dict[str, Any]] = []

        if HAS_FAISS:
            self.index = faiss.IndexHNSWFlat(dimension, m, faiss.METRIC_INNER_PRODUCT)
            self.index.hnsw.efSearch = ef_search
        else:
            self.index = None
            self._vectors: list[np.ndarray] = []

    def _normalize(self, v: np.ndarray) -> np.ndarray:
        """L2 normalize vectors for cosine / inner-product equivalence."""
        norm = np.linalg.norm(v, axis=1, keepdims=True)
        norm = np.where(norm == 0, 1.0, norm)
        return (v / norm).astype(np.float32)

    def add(self, vectors: np.ndarray, metadata: list[dict[str, Any]]) -> None:
        if vectors.ndim == 1:
            vectors = vectors.reshape(1, -1)
        normalized = self._normalize(vectors)

        if HAS_FAISS and self.index is not None:
            self.index.add(normalized)
        else:
            self._vectors.extend(list(normalized))

        self.metadata.extend(metadata)

    def search(self, query_vectors: np.ndarray, top_k: int = 5) -> list[list[tuple[float, dict[str, Any]]]]:
        if query_vectors.ndim == 1:
            query_vectors = query_vectors.reshape(1, -1)
        normalized = self._normalize(query_vectors)

        results: list[list[tuple[float, dict[str, Any]]]] = []

        if HAS_FAISS and self.index is not None and self.index.ntotal > 0:
            k = min(top_k, self.index.ntotal)
            distances, indices = self.index.search(normalized, k)
            for dist_row, idx_row in zip(distances, indices):
                row_res = []
                for score, idx in zip(dist_row, idx_row):
                    if idx >= 0 and idx < len(self.metadata):
                        row_res.append((float(score), self.metadata[idx]))
                results.append(row_res)
        else:
            # Fallback numpy inner product
            if not self._vectors:
                return [[] for _ in range(len(query_vectors))]
            all_vecs = np.array(self._vectors)
            scores_matrix = np.dot(normalized, all_vecs.T)
            for row in scores_matrix:
                top_indices = np.argsort(row)[::-1][:top_k]
                row_res = [(float(row[idx]), self.metadata[idx]) for idx in top_indices]
                results.append(row_res)

        return results

    def count(self) -> int:
        if HAS_FAISS and self.index is not None:
            return self.index.ntotal
        return len(self.metadata)

    def save(self, filepath: Path | str) -> None:
        fp = Path(filepath)
        fp.parent.mkdir(parents=True, exist_ok=True)

        meta_path = fp.with_suffix(".meta.json")
        meta_path.write_text(json.dumps(self.metadata, indent=2), encoding="utf-8")

        if HAS_FAISS and self.index is not None:
            faiss.write_index(self.index, str(fp))
        else:
            vec_path = fp.with_suffix(".npy")
            np.save(vec_path, np.array(self._vectors) if self._vectors else np.empty((0, self.dimension)))

    def load(self, filepath: Path | str) -> None:
        fp = Path(filepath)
        meta_path = fp.with_suffix(".meta.json")
        if meta_path.exists():
            self.metadata = json.loads(meta_path.read_text(encoding="utf-8"))

        if HAS_FAISS and fp.exists():
            self.index = faiss.read_index(str(fp))
        else:
            vec_path = fp.with_suffix(".npy")
            if vec_path.exists():
                self._vectors = list(np.load(vec_path))
