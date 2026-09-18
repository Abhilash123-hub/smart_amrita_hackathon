"""Verification Tests for Evidence Crops & Visual Proof Artifacts (Task Card T1.6)."""

import hashlib
from pathlib import Path
import pytest
from PIL import Image, ImageDraw

from src.traceai.pipelines.evidence import locate_best_match_bbox, render_evidence_composite


def test_bounding_box_localization():
    """Verify template matching returns valid bounding box coordinates overlapping true region."""
    # Create base source image with distinctive pattern
    source = Image.new("RGB", (600, 600), color=(30, 30, 30))
    draw = ImageDraw.Draw(source)
    draw.ellipse([200, 200, 350, 350], fill=(240, 120, 40))

    # Query is a crop around the patch
    query = source.crop((200, 200, 350, 350))

    bx, by, bw, bh = locate_best_match_bbox(query, source)
    assert bw > 0 and bh > 0
    # Center of bbox should overlap (200, 200) within tolerance
    assert abs(bx - 200) < 5
    assert abs(by - 200) < 5


def test_evidence_composite_deterministic_output(tmp_path):
    """Verify artifact bytes are deterministic for identical inputs (no timestamps in pixels)."""
    source = Image.new("RGB", (400, 400), color=(30, 40, 50))
    query = Image.new("RGB", (300, 300), color=(30, 40, 50))

    p1 = tmp_path / "evidence_1.png"
    p2 = tmp_path / "evidence_2.png"

    render_evidence_composite(
        query_img=query,
        source_img=source,
        score=0.9412,
        asset_hash="sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        matched_source_name="reference_artwork_01.png",
        output_path=p1,
    )

    render_evidence_composite(
        query_img=query,
        source_img=source,
        score=0.9412,
        asset_hash="sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        matched_source_name="reference_artwork_01.png",
        output_path=p2,
    )

    h1 = hashlib.sha256(p1.read_bytes()).hexdigest()
    h2 = hashlib.sha256(p2.read_bytes()).hexdigest()

    assert h1 == h2, "Evidence composite bytes must be strictly deterministic"
