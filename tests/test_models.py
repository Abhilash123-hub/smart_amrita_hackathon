"""Contract Tests for Frozen Pydantic Models (Task Card T0.2)."""

import json
from datetime import datetime, timezone
from uuid import uuid4
import pytest
from pydantic import ValidationError
from fastapi import FastAPI

from src.traceai.core.models import (
    Track,
    Verdict,
    AssetInput,
    IngestRequest,
    ScanResult,
    ClearanceCertificate,
    EvidenceRecord,
)


def test_models_import_and_serialize_round_trip():
    """Verify all 5 models round-trip through JSON without loss."""
    now = datetime.now(timezone.utc)
    dummy_hash = "sha256:" + "a" * 64

    # 1. AssetInput
    asset = AssetInput(
        asset_id="asset-001",
        source_uri="https://example.com/dataset/sample.txt",
        declared_license="MIT",
        mime_type="text/plain",
    )
    asset_json = asset.model_dump_json()
    assert AssetInput.model_validate_json(asset_json) == asset

    # 2. IngestRequest
    req = IngestRequest(batch_id="batch-alpha-1", assets=[asset])
    req_json = req.model_dump_json()
    assert IngestRequest.model_validate_json(req_json) == req

    # 3. ScanResult
    res = ScanResult(
        asset_id="asset-001",
        track=Track.TEXT,
        verdict=Verdict.PASSED,
        score=0.12,
        matched_source=None,
        asset_hash=dummy_hash,
        evidence_uri=None,
        scanned_at=now,
    )
    res_json = res.model_dump_json()
    assert ScanResult.model_validate_json(res_json) == res

    # 4. ClearanceCertificate
    cert = ClearanceCertificate(
        certificate_id=uuid4(),
        asset_id="asset-001",
        asset_hash=dummy_hash,
        verdict=Verdict.PASSED,
        issued_at=now,
        rsa_signature="deadbeefcafebabe",
    )
    cert_json = cert.model_dump_json()
    assert ClearanceCertificate.model_validate_json(cert_json) == cert

    # 5. EvidenceRecord
    evidence = EvidenceRecord(
        asset_id="asset-002",
        asset_hash=dummy_hash,
        matched_source="nyt_article_2023.txt",
        score=0.94,
        text_span="Paraphrased text sequence here",
        locked_at=now,
    )
    evidence_json = evidence.model_dump_json()
    assert EvidenceRecord.model_validate_json(evidence_json) == evidence


def test_hash_validator_rejects_malformed_hashes():
    """Verify sha256:<64 hex> format enforcement."""
    now = datetime.now(timezone.utc)

    # Missing sha256: prefix
    with pytest.raises(ValidationError):
        ScanResult(
            asset_id="test",
            track=Track.TEXT,
            verdict=Verdict.PASSED,
            score=0.0,
            asset_hash="a" * 64,
            scanned_at=now,
        )

    # Uppercase hex or invalid chars
    with pytest.raises(ValidationError):
        ScanResult(
            asset_id="test",
            track=Track.TEXT,
            verdict=Verdict.PASSED,
            score=0.0,
            asset_hash="sha256:" + "A" * 64,
            scanned_at=now,
        )

    # Too short
    with pytest.raises(ValidationError):
        ScanResult(
            asset_id="test",
            track=Track.TEXT,
            verdict=Verdict.PASSED,
            score=0.0,
            asset_hash="sha256:12345",
            scanned_at=now,
        )


def test_score_range_validation():
    """Verify score is bounded in [0.0, 1.0]."""
    now = datetime.now(timezone.utc)
    dummy_hash = "sha256:" + "b" * 64

    with pytest.raises(ValidationError):
        ScanResult(
            asset_id="test",
            track=Track.TEXT,
            verdict=Verdict.BLOCKED,
            score=1.05,  # out of range
            asset_hash=dummy_hash,
            scanned_at=now,
        )

    with pytest.raises(ValidationError):
        ScanResult(
            asset_id="test",
            track=Track.TEXT,
            verdict=Verdict.BLOCKED,
            score=-0.01,  # out of range
            asset_hash=dummy_hash,
            scanned_at=now,
        )


def test_mime_type_allowlist_enforcement():
    """Verify unsupported mime types are rejected."""
    with pytest.raises(ValidationError):
        AssetInput(
            asset_id="asset-bad-mime",
            source_uri="https://example.com/file.exe",
            mime_type="application/x-msdownload",  # not in allowlist
        )


def test_openapi_schema_export():
    """Verify models export into OpenAPI schema cleanly."""
    app = FastAPI(title="TraceAI Schema Test")

    @app.post("/v1/ingest", response_model=ScanResult)
    def dummy_endpoint(payload: IngestRequest):
        pass

    openapi = app.openapi()
    assert "IngestRequest" in openapi["components"]["schemas"]
    assert "ScanResult" in openapi["components"]["schemas"]
    assert "AssetInput" in openapi["components"]["schemas"]
