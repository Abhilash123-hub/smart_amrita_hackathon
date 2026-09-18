"""Verification Tests for Append-Only Audit Log Store (Task Card T2.3)."""

from datetime import datetime, timezone
from uuid import uuid4
import pytest

from src.traceai.core.models import ScanResult, Track, Verdict
from src.traceai.db.audit import AuditLogStore


def test_audit_log_append_and_query(tmp_path):
    """Verify recording scan results and querying by batch and asset hash."""
    db_file = tmp_path / "test_audit.db"
    audit = AuditLogStore(db_path=db_file)
    now = datetime.now(timezone.utc)
    dummy_hash = "sha256:" + "e" * 64

    res = ScanResult(
        asset_id="asset-audit-01",
        track=Track.TEXT,
        verdict=Verdict.PASSED,
        score=0.04,
        matched_source=None,
        asset_hash=dummy_hash,
        evidence_uri=None,
        scanned_at=now,
    )

    cert_id = uuid4()
    event_id = audit.record_scan_result("batch-audit-100", res, certificate_id=cert_id)
    assert event_id is not None

    # Query by batch
    batch_rows = audit.query_by_batch("batch-audit-100")
    assert len(batch_rows) == 1
    assert batch_rows[0]["asset_id"] == "asset-audit-01"
    assert batch_rows[0]["verdict"] == "PASSED"
    assert batch_rows[0]["certificate_id"] == str(cert_id)

    # Query by hash
    hash_rows = audit.query_by_asset_hash(dummy_hash)
    assert len(hash_rows) == 1
    assert hash_rows[0]["batch_id"] == "batch-audit-100"


def test_audit_log_forbids_update_and_delete(tmp_path):
    """Verify that update and delete operations raise PermissionError."""
    db_file = tmp_path / "test_audit_immutable.db"
    audit = AuditLogStore(db_path=db_file)

    with pytest.raises(PermissionError, match="DELETE operations are strictly prohibited"):
        audit.delete()

    with pytest.raises(PermissionError, match="UPDATE operations are strictly prohibited"):
        audit.update()
