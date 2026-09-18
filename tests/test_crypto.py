"""Verification Tests for Crypto Signer & Clearance Certificates (Task Card T2.1)."""

import base64
from uuid import uuid4
import pytest
from src.traceai.core.crypto import CryptoSigner, canonicalize_json, hash_asset_bytes
from src.traceai.core.models import ClearanceCertificate, Verdict


def test_hash_asset_bytes():
    """Verify SHA-256 asset hash format and correctness."""
    data = b"Clean multimodal asset data"
    h = hash_asset_bytes(data)
    assert h.startswith("sha256:")
    assert len(h) == 71  # "sha256:" (7) + 64 hex characters


def test_sign_and_verify_certificate_round_trip():
    """Verify certificate sign-and-verify cycle passes."""
    signer = CryptoSigner.generate(key_size=2048)
    cert = signer.issue_clearance_certificate(
        asset_id="asset-test-42",
        asset_hash="sha256:" + "0" * 64,
    )

    assert cert.verdict == Verdict.PASSED
    assert len(cert.rsa_signature) > 100
    assert signer.verify_certificate(cert) is True


def test_tampered_payload_fails_verification():
    """Verify flipped bits or altered metadata immediately fail verification."""
    signer = CryptoSigner.generate(key_size=2048)
    cert = signer.issue_clearance_certificate(
        asset_id="asset-original",
        asset_hash="sha256:" + "1" * 64,
    )

    # 1. Tamper with asset hash
    tampered_hash_cert = cert.model_copy(update={"asset_hash": "sha256:" + "2" * 64})
    assert signer.verify_certificate(tampered_hash_cert) is False

    # 2. Tamper with asset ID
    tampered_id_cert = cert.model_copy(update={"asset_id": "asset-tampered"})
    assert signer.verify_certificate(tampered_id_cert) is False

    # 3. Tamper with signature bits
    sig_raw = base64.b64decode(cert.rsa_signature)
    tampered_sig_raw = bytes([sig_raw[0] ^ 0xFF]) + sig_raw[1:]
    tampered_sig_b64 = base64.b64encode(tampered_sig_raw).decode("ascii")

    tampered_sig_cert = cert.model_copy(update={"rsa_signature": tampered_sig_b64})
    assert signer.verify_certificate(tampered_sig_cert) is False


def test_public_key_verifier_instance():
    """Verify that a public-key-only verifier instance can verify certificates without private key."""
    signer = CryptoSigner.generate(key_size=2048)
    cert = signer.issue_clearance_certificate(
        asset_id="asset-external",
        asset_hash="sha256:" + "f" * 64,
    )

    pub_pem = signer.export_public_key_pem()
    verifier = CryptoSigner.load_from_pem(public_pem=pub_pem)

    # Cannot sign without private key
    with pytest.raises(ValueError, match="Cannot sign without private key"):
        verifier.issue_clearance_certificate("asset-fail", "sha256:" + "0" * 64)

    # Can verify successfully
    assert verifier.verify_certificate(cert) is True
