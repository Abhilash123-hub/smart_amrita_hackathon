"""End-to-End Integration Tests for Ingestion Gateway & Batch Scanning (Task Card T1.7)."""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.traceai.api import app, _BATCH_STORE
from src.traceai.core.models import AssetInput, IngestRequest, Verdict
from traceai import cli


@pytest.fixture
def client():
    _BATCH_STORE.clear()
    return TestClient(app)


def test_dirty_dataset_flagged_100_percent_via_http(client):
    """Verify 100% of dirty dataset assets are flagged (BLOCKED or REVIEW) through POST /v1/ingest."""
    dirty_dir = Path("mock_data/dirty_dataset")
    dirty_texts = sorted(list(dirty_dir.glob("dirty_text_*.public_domain")))[:5]
    dirty_imgs = sorted(list(dirty_dir.glob("dirty_image_*.public_domain")))[:5]

    assets = []
    for t in dirty_texts:
        assets.append(
            AssetInput(
                asset_id=t.name,
                source_uri=str(t),
                declared_license="Public Domain (Claimed)",
                mime_type="text/plain",
            )
        )
    for img in dirty_imgs:
        assets.append(
            AssetInput(
                asset_id=img.name,
                source_uri=str(img),
                declared_license="Public Domain (Claimed)",
                mime_type="image/png",
            )
        )

    req = IngestRequest(batch_id="batch-dirty-integration-01", assets=assets)

    resp = client.post("/v1/ingest", json=req.model_dump())
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_assets"] == len(assets)
    # Every dirty asset must be intercepted
    flagged = data["blocked_count"] + data["review_count"]
    assert flagged == len(assets)


def test_idempotency_prevents_double_scan(client):
    """Verify resubmitting the same batch returns cached response without double-scanning."""
    dirty_dir = Path("mock_data/dirty_dataset")
    text_file = next(dirty_dir.glob("dirty_text_*.public_domain"))

    asset = AssetInput(
        asset_id="asset-idempotent-test",
        source_uri=str(text_file),
        mime_type="text/plain",
    )
    req = IngestRequest(batch_id="batch-idempotent-check", assets=[asset])

    # First request
    resp1 = client.post(
        "/v1/ingest",
        json=req.model_dump(),
        headers={"Idempotency-Key": "test-idem-key-123"},
    )
    assert resp1.status_code == 200
    d1 = resp1.json()
    assert d1["idempotent_cached"] is False

    # Second request with same idempotency key
    resp2 = client.post(
        "/v1/ingest",
        json=req.model_dump(),
        headers={"Idempotency-Key": "test-idem-key-123"},
    )
    assert resp2.status_code == 200
    d2 = resp2.json()
    assert d2["idempotent_cached"] is True
    assert d1["results"] == d2["results"]


def test_cli_and_api_produce_identical_verdicts(tmp_path, client):
    """Verify CLI scan and HTTP API produce matching verdicts for identical input directory."""
    input_dir = tmp_path / "cli_test_dir"
    input_dir.mkdir(parents=True, exist_ok=True)

    clean_file = input_dir / "clean_sample.txt"
    clean_file.write_text("Unique uncopyrighted scientific data.", encoding="utf-8")

    out_json = tmp_path / "cli_scan_report.json"

    # Run CLI scan
    ret = cli.main([
        "scan",
        "--input-dir", str(input_dir),
        "--output", str(out_json),
    ])
    assert ret in (0, 2)
    assert out_json.exists()

    with open(out_json, "r", encoding="utf-8") as f:
        cli_data = json.load(f)

    # Run HTTP API on same file
    asset = AssetInput(
        asset_id="clean_sample.txt",
        source_uri=str(clean_file),
        mime_type="text/plain",
    )
    req = IngestRequest(batch_id="batch-parity-check", assets=[asset])
    resp = client.post("/v1/ingest", json=req.model_dump())
    api_data = resp.json()

    # Compare verdicts
    cli_verdict = cli_data["results"][0].get("verdict") or cli_data["results"][0].get("status")
    api_verdict = api_data["results"][0]["verdict"]
    assert cli_verdict == api_verdict == "PASSED"
