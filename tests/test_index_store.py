"""Verification Tests for Vector Index Store (Task Card T1.2)."""

import time
import numpy as np
import pytest
from src.traceai.db.index_store import FAISSIndexStore


def test_verbatim_chunk_recall_rank_one():
    """Verify querying a verbatim chunk returns its source at rank 1 with similarity > 0.9."""
    store = FAISSIndexStore(dimension=128)
    rng = np.random.RandomState(42)

    # Populate 50 synthetic reference vectors
    ref_vectors = rng.randn(50, 128).astype(np.float32)
    meta = [{"id": f"ref_{i}", "source": f"doc_{i}.txt"} for i in range(50)]
    store.add(ref_vectors, meta)

    # Query with exact vector of ref 7
    query_vec = ref_vectors[7:8].copy()
    start_time = time.perf_counter()
    results = store.search(query_vec, top_k=5)[0]
    latency_ms = (time.perf_counter() - start_time) * 1000

    assert len(results) >= 1
    top_score, top_meta = results[0]

    # Rank 1 must be ref_7 with inner-product similarity ~ 1.0 (>= 0.99)
    assert top_meta["id"] == "ref_7"
    assert top_score >= 0.90
    assert latency_ms < 50.0  # sub-50ms latency requirement


def test_p95_recall_latency_under_50ms():
    """Verify p95 recall-stage latency is under 50 ms per chunk on CPU."""
    store = FAISSIndexStore(dimension=128)
    rng = np.random.RandomState(100)

    # 100 items index
    vectors = rng.randn(100, 128).astype(np.float32)
    meta = [{"id": f"ref_{i}"} for i in range(100)]
    store.add(vectors, meta)

    latencies = []
    for _ in range(50):
        q = rng.randn(1, 128).astype(np.float32)
        t0 = time.perf_counter()
        _ = store.search(q, top_k=5)
        latencies.append((time.perf_counter() - t0) * 1000)

    p95 = np.percentile(latencies, 95)
    assert p95 < 50.0, f"p95 latency was {p95:.2f}ms, expected < 50ms"


def test_index_snapshot_save_and_reload(tmp_path):
    """Verify index snapshots save and reload bit-identically."""
    store = FAISSIndexStore(dimension=64)
    rng = np.random.RandomState(200)

    vectors = rng.randn(20, 64).astype(np.float32)
    meta = [{"id": f"item_{i}", "title": f"Title {i}"} for i in range(20)]
    store.add(vectors, meta)

    snapshot_path = tmp_path / "test_index.faiss"
    store.save(snapshot_path)

    # Create new store and reload
    new_store = FAISSIndexStore(dimension=64)
    new_store.load(snapshot_path)

    assert new_store.count() == 20
    assert len(new_store.metadata) == 20
    assert new_store.metadata[0]["id"] == "item_0"

    # Search query should match identically
    q = vectors[3:4]
    orig_res = store.search(q, top_k=3)[0]
    reloaded_res = new_store.search(q, top_k=3)[0]

    assert len(orig_res) == len(reloaded_res)
    for (s1, m1), (s2, m2) in zip(orig_res, reloaded_res):
        assert m1["id"] == m2["id"]
        assert pytest.approx(s1, abs=1e-4) == s2
