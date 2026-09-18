"""Verification Tests for Immutable Evidence Locker (Task Card T2.2)."""

from datetime import datetime, timezone
from pathlib import Path
from PIL import Image
import pytest

from src.traceai.core.models import EvidenceRecord
from src.traceai.db.evidence_locker import EvidenceLocker


def test_evidence_locker_worm_immutability(tmp_path):
    """Verify that re-writing an existing evidence key raises FileExistsError."""
    locker = EvidenceLocker(root_dir=tmp_path / "evidence_vault")
    dummy_hash = "sha256:" + "c" * 64

    rec = EvidenceRecord(
        asset_id="asset-blocked-001",
        asset_hash=dummy_hash,
        matched_source="reference_artwork_01.png",
        score=0.965,
        crop_uri=None,
        text_span=None,
        locked_at=datetime.now(timezone.utc),
    )

    crop = Image.new("RGB", (100, 100), color=(200, 50, 50))

    # First write: succeeds
    uri = locker.store_evidence(rec, composite_crop=crop)
    assert Path(uri).exists()

    # Second write with same asset_hash: MUST raise FileExistsError (WORM violation)
    with pytest.raises(FileExistsError, match="WORM Violation"):
        locker.store_evidence(rec, composite_crop=crop)


def test_evidence_retrieval_bundle(tmp_path):
    """Verify stored evidence bundles can be retrieved intact with crops and spans."""
    locker = EvidenceLocker(root_dir=tmp_path / "evidence_vault", retention_days=730)
    dummy_hash = "sha256:" + "d" * 64

    rec = EvidenceRecord(
        asset_id="asset-blocked-002",
        asset_hash=dummy_hash,
        matched_source="copyright_book_01.txt",
        score=0.912,
        text_span="The quick brown fox jumps over the lazy dog.",
        locked_at=datetime.now(timezone.utc),
    )

    crop = Image.new("RGB", (50, 50), color=(10, 20, 30))
    locker.store_evidence(rec, composite_crop=crop)

    # Retrieve bundle
    bundle = locker.retrieve_evidence(dummy_hash)
    assert bundle is not None
    assert bundle["record"].asset_id == "asset-blocked-002"
    assert bundle["record"].score == 0.912
    assert bundle["crop_path"] is not None
    assert Path(bundle["crop_path"]).exists()
    assert bundle["text_span_path"] is not None
    assert Path(bundle["text_span_path"]).read_text(encoding="utf-8") == rec.text_span
    assert bundle["retention_days"] == 730
