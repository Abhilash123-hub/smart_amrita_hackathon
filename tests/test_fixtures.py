"""Verification Tests for Dirty Dataset Fixtures & Reference Seeds (Task Card T0.5)."""

import json
from pathlib import Path
import pytest
from scripts.generate_dirty_dataset import check_dirty_dataset, generate_dataset


def test_dirty_dataset_fixture_acceptance():
    """Verify 10 dirty text + 10 dirty image files with manifest and 0 exact matches."""
    data_dir = Path("mock_data/dirty_dataset")
    ref_dir = Path("mock_data/copyright_index")

    assert data_dir.exists(), "mock_data/dirty_dataset directory must exist"
    assert ref_dir.exists(), "mock_data/copyright_index directory must exist"

    # Run fixture check
    passed = check_dirty_dataset(data_dir, ref_dir)
    assert passed is True, "Dirty dataset fixture check failed"

    # Assert exact asset counts
    manifest = json.loads((data_dir / "manifest.json").read_text(encoding="utf-8"))
    assets = manifest.get("assets", [])
    assert len(assets) == 20

    text_assets = [a for a in assets if a["track"] == "TEXT"]
    img_assets = [a for a in assets if a["track"] == "IMAGE"]
    assert len(text_assets) == 10
    assert len(img_assets) == 10

    # Ensure naive exact hash catches zero assets
    for asset in assets:
        assert asset["exact_hash_match"] is False
        assert asset["reference_sha256"] != asset["dirty_sha256"]


def test_deterministic_generation_from_seed(tmp_path):
    """Verify generator output is bit-identical for identical seed."""
    ref_dir = Path("mock_data/copyright_index")
    out1 = tmp_path / "run1"
    out2 = tmp_path / "run2"

    m1 = generate_dataset(out1, ref_dir, seed=123)
    m2 = generate_dataset(out2, ref_dir, seed=123)

    # Check identical manifests
    assert len(m1["assets"]) == len(m2["assets"])
    for a1, a2 in zip(m1["assets"], m2["assets"]):
        assert a1["asset_id"] == a2["asset_id"]
        assert a1["dirty_sha256"] == a2["dirty_sha256"]
