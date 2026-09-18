"""Verification Tests for Sliding-Window Token Chunker (Task Card T1.1)."""

import math
import pytest
from src.traceai.pipelines.text_track import chunk_text


def test_10000_token_document_window_count():
    """Verify a 10,000-token document yields ceil((10000-50)/(256-50)) windows, all within size."""
    size = 256
    overlap = 50
    total_tokens = 10_000

    # Build a 10,000-token document
    doc_text = " ".join([f"tok_{i}" for i in range(total_tokens)])

    chunks = chunk_text(doc_text, size=size, overlap=overlap, parent_asset_id="doc-10k")

    expected_windows = math.ceil((total_tokens - overlap) / (size - overlap))
    assert len(chunks) == expected_windows

    # Verify no chunk exceeds 256 tokens
    for ch in chunks:
        assert ch.token_count <= size
        assert len(ch.text.split()) <= size
        assert ch.token_count > 0


def test_boundary_sentence_captured_intact():
    """Verify a sentence deliberately straddling a chunk boundary appears fully in at least one chunk."""
    size = 256
    overlap = 50

    # Place a 30-word target sentence starting at token 240 (crosses the 256 boundary into 270)
    target_sentence = "The elusive copyright clause was strategically inserted across the boundary window to test chunking."
    target_words = target_sentence.split()
    assert len(target_words) == 14

    prefix = ["word"] * 245
    suffix = ["word"] * 300
    full_tokens = prefix + target_words + suffix
    full_text = " ".join(full_tokens)

    chunks = chunk_text(full_text, size=size, overlap=overlap, parent_asset_id="test-boundary")

    # In chunk 0: tokens 0 to 256 -> contains partial sentence (245 to 256)
    # In chunk 1: tokens 206 to 462 -> covers tokens 206 to 462, which completely spans 245 to 259!
    sentence_found_intact = any(target_sentence in ch.text for ch in chunks)
    assert sentence_found_intact is True, "Target sentence must appear intact in at least one overlapping chunk"


def test_empty_and_short_documents():
    """Verify edge cases: empty strings and documents shorter than window size."""
    assert chunk_text("", size=256, overlap=50) == []

    short_doc = "A brief document of seven words."
    chunks = chunk_text(short_doc, size=256, overlap=50, parent_asset_id="short")
    assert len(chunks) == 1
    assert chunks[0].token_count == 6
    assert chunks[0].text == short_doc
