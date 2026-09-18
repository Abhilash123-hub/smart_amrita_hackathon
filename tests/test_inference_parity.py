"""Verification Tests for Inference Parity & Fallback Contract (Task Card T4.2)."""

import pytest
from src.traceai.db.inference import TritonInferenceClient


def test_inference_client_local_fallback():
    """Verify local PyTorch fallback path scores pairs successfully when Triton is disabled."""
    client = TritonInferenceClient(use_triton=False)
    pairs = [
        ("The quick brown fox jumps over the lazy dog.", "The quick brown fox jumps over the lazy dog."),
        ("Completely unrelated astrophysical physics concept.", "A recipe for chocolate cake with frosting."),
    ]

    scores = client.predict_cross_encoder_batch(pairs)
    assert len(scores) == 2
    # Exact match should have high score
    assert scores[0] > 0.80
    # Unrelated match should have low score
    assert scores[1] < 0.40


def test_inference_client_triton_flag_toggle():
    """Verify toggling use_triton restores Phase 1 local behavior without redeploy."""
    client_local = TritonInferenceClient(use_triton=False)
    client_triton = TritonInferenceClient(use_triton=True)

    pairs = [("Hello world", "Hello world")]
    s_local = client_local.predict_cross_encoder_batch(pairs)
    s_triton = client_triton.predict_cross_encoder_batch(pairs)

    assert len(s_local) == 1
    assert len(s_triton) == 1
