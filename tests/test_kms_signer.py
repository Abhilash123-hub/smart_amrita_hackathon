"""Verification Tests for KMS Asymmetric Key Management (Task Card T4.4)."""

import pytest
from src.traceai.core.kms_signer import KMSSigner


def test_kms_signer_issuance_and_verification():
    """Verify KMS-backed certificate signing and verification."""
    signer = KMSSigner(key_id="kms-key-2026-v1")
    dummy_hash = "sha256:" + "7" * 64

    cert = signer.issue_clearance_certificate("asset-kms-1", dummy_hash)
    assert signer.verify_certificate(cert) is True


def test_kms_key_rotation_historical_verification():
    """Verify rotating key retains ability to verify historical certificates."""
    signer = KMSSigner(key_id="kms-key-2026-v1")
    dummy_hash = "sha256:" + "8" * 64

    # Issue under v1
    cert_v1 = signer.issue_clearance_certificate("asset-v1", dummy_hash)
    assert signer.verify_certificate(cert_v1) is True

    # Rotate to v2
    signer.rotate_key(new_key_id="kms-key-2026-v2")

    # Issue new cert under v2
    cert_v2 = signer.issue_clearance_certificate("asset-v2", dummy_hash)
    assert signer.verify_certificate(cert_v2) is True

    # Historical cert under v1 still verifies!
    assert signer.verify_certificate(cert_v1, key_id="kms-key-2026-v1") is True
