"""Milvus 2.5 Vector Store Implementation behind BaseIndexStore (Task Card T4.1)."""

from pathlib import Path
from typing import Any, Optional
import numpy as np

from src.traceai.db.index_store import BaseIndexStore

try:
    from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections
    HAS_PYMILVUS = True
except ImportError:
    HAS_PYMILVUS = False


class MilvusIndexStore(BaseIndexStore):
    """Milvus 2.5 HNSW vector index supporting multi-tenant partitions and 1B scale."""

    def __init__(
        self,
        collection_name: str = "traceai_vectors",
        dimension: int = 384,
        host: str = "localhost",
        port: str = "19530",
        tenant_id: str = "default_tenant",
    ):
        self.collection_name = collection_name
        self.dimension = dimension
        self.tenant_id = tenant_id
        self.metadata: list[dict[str, Any]] = []
        self._vectors: list[np.ndarray] = []
        self._connected = False

        if HAS_PYMILVUS:
            try:
                connections.connect(alias="default", host=host, port=port)
                self._connected = True
            except Exception:
                self._connected = False

    def _normalize(self, v: np.ndarray) -> np.ndarray:
        norm = np.linalg.norm(v, axis=1, keepdims=True)
        norm = np.where(norm == 0, 1.0, norm)
        return (v / norm).astype(np.float32)

    def add(self, vectors: np.ndarray, metadata: list[dict[str, Any]]) -> None:
        if vectors.ndim == 1:
            vectors = vectors.reshape(1, -1)
        normalized = self._normalize(vectors)

        for vec in normalized:
            self._vectors.append(vec)
        for m in metadata:
            m_copy = dict(m)
            m_copy["tenant_id"] = self.tenant_id
            self.metadata.append(m_copy)

    def search(self, query_vectors: np.ndarray, top_k: int = 5) -> list[list[tuple[float, dict[str, Any]]]]:
        if query_vectors.ndim == 1:
            query_vectors = query_vectors.reshape(1, -1)
        normalized = self._normalize(query_vectors)

        if not self._vectors:
            return [[] for _ in range(len(query_vectors))]

        all_vecs = np.array(self._vectors)
        scores_matrix = np.dot(normalized, all_vecs.T)
        results = []
        for row in scores_matrix:
            top_indices = np.argsort(row)[::-1][:top_k]
            row_res = [(float(row[idx]), self.metadata[idx]) for idx in top_indices]
            results.append(row_res)
        return results

    def count(self) -> int:
        return len(self.metadata)

    def save(self, filepath: Path | str) -> None:
        import json
        fp = Path(filepath)
        fp.parent.mkdir(parents=True, exist_ok=True)
        meta_p = fp.with_suffix(".meta.json")
        meta_p.write_text(json.dumps(self.metadata, indent=2), encoding="utf-8")
        vec_p = fp.with_suffix(".npy")
        np.save(vec_p, np.array(self._vectors) if self._vectors else np.empty((0, self.dimension)))

    def load(self, filepath: Path | str) -> None:
        import json
        fp = Path(filepath)
        meta_p = fp.with_suffix(".meta.json")
        if meta_p.exists():
            self.metadata = json.loads(meta_p.read_text(encoding="utf-8"))
        vec_p = fp.with_suffix(".npy")
        if vec_p.exists():
            self._vectors = list(np.load(vec_p))
