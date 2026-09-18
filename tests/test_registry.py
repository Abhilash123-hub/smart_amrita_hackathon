"""Verification Tests for Public Fingerprint Registry & Revocation (Task Card T4.7)."""

import pytest
from src.traceai.registry.api import FingerprintRegistry, RightsholderSubmission


def test_registry_submission_and_revocation():
    """Verify rightsholder submission, active registration check, and revocation."""
    reg = FingerprintRegistry()
    dummy_hash = "sha256:" + "4" * 64

    sub = RightsholderSubmission(
        submission_id="sub-001",
        rightsholder_name="Global Media Corp",
        contact_email="legal@globalmedia.com",
        work_title="Original Novel Excerpt",
        fingerprint_hash=dummy_hash,
        track="TEXT",
        attestation_statement="I attest under penalty of perjury that I hold copyright to this work.",
    )

    reg.submit_work(sub)
    assert reg.is_fingerprint_registered(dummy_hash) is True

    # Revoke work
    revoked = reg.revoke_work("sub-001")
    assert revoked is True
    # Once revoked, fingerprint is no longer considered active
    assert reg.is_fingerprint_registered(dummy_hash) is False
