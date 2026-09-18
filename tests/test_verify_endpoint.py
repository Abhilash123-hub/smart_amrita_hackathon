"""Verification Tests for Attorney Verification Endpoint (Task Card T2.5)."""

import base64
import pytest
from fastapi.testclient import TestClient

import src.traceai.api as api_mod
from src.traceai.api import app
from src.traceai.core.crypto import CryptoSigner, hash_asset_bytes


@pytest.fixture
def client():
    # Pin a known signer into api_mod._GLOBAL_SIGNER for reproducible testing
    signer = CryptoSigner.generate(key_size=2048)
    api_mod._GLOBAL_SIGNER = signer
    return TestClient(app), signer


def test_attorney_verify_valid_certificate(client):
    """Verify round-trip verification succeeds for authentic certificate and bytes."""
    test_client, signer = client
    content = "Authentic training data sample for attorney review."
    raw_bytes = content.encode("utf-8")
    asset_hash = hash_asset_bytes(raw_bytes)

    cert = signer.issue_clearance_certificate(
        asset_id="asset-attorney-01",
        asset_hash=asset_hash,
    )

    resp = test_client.post(
        "/v1/verify",
        json={
            "certificate": cert.model_dump(mode="json"),
            "raw_content_text": content,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["verified"] is True
    assert data["reason_code"] == "SIGNATURE_VALID"
    assert data["asset_hash"] == asset_hash


def test_attorney_verify_tampered_bytes_fails_hash_mismatch(client):
    """Verify verification of altered file fails with HASH_MISMATCH reason code."""
    test_client, signer = client
    content = "Original unaltered data."
    raw_bytes = content.encode("utf-8")
    asset_hash = hash_asset_bytes(raw_bytes)

    cert = signer.issue_clearance_certificate(
        asset_id="asset-attorney-02",
        asset_hash=asset_hash,
    )

    # Submit altered content
    resp = test_client.post(
        "/v1/verify",
        json={
            "certificate": cert.model_dump(mode="json"),
            "raw_content_text": "Altered or tampered content with modified bits.",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["verified"] is False
    assert data["reason_code"] == "HASH_MISMATCH"
    assert data["certificate_hash"] == asset_hash


def test_attorney_verify_tampered_signature_fails_signature_invalid(client):
    """Verify tampered certificate signature fails with SIGNATURE_INVALID."""
    test_client, signer = client
    content = "Unaltered content."
    raw_bytes = content.encode("utf-8")
    asset_hash = hash_asset_bytes(raw_bytes)

    cert = signer.issue_clearance_certificate(
        asset_id="asset-attorney-03",
        asset_hash=asset_hash,
    )

    # Flip bits in signature
    sig_raw = base64.b64decode(cert.rsa_signature)
    tampered_sig = base64.b64encode(bytes([sig_raw[0] ^ 0xFF]) + sig_raw[1:]).decode("ascii")
    tampered_cert = cert.model_copy(update={"rsa_signature": tampered_sig})

    resp = test_client.post(
        "/v1/verify",
        json={
            "certificate": tampered_cert.model_dump(mode="json"),
            "raw_content_text": content,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["verified"] is False
    assert data["reason_code"] == "SIGNATURE_INVALID"


def test_public_key_distribution_endpoint(client):
    """Verify /v1/keys/public returns active key PEM and key rotation metadata."""
    test_client, _ = client
    resp = test_client.get("/v1/keys/public")
    assert resp.status_code == 200
    data = resp.json()
    assert "public_key_pem" in data
    assert "-----BEGIN PUBLIC KEY-----" in data["public_key_pem"]
    assert data["key_id"] == "key-2026-v1"
    assert data["status"] == "ACTIVE"
