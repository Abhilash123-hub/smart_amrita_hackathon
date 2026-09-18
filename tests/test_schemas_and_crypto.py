"""Unit tests for schemas, byte sniffing, and cryptographic layer."""

import tempfile
from pathlib import Path

from traceai.config import DEFAULT_CONFIG
from traceai.crypto.hasher import compute_sha256_bytes, compute_sha256_file
from traceai.crypto.lineage import build_prov_lineage
from traceai.crypto.signer import CryptoSigner
from traceai.gateway import IngestionGateway
from traceai.schemas.asset import AssetInput, TrackType, sniff_mime_and_track_from_bytes
from traceai.schemas.certificate import ClearanceCertificate
from traceai.schemas.report import AssetEvaluation, AssetStatus


def test_sha256_hasher():
    data = b"Hello TraceAI Ingestion Gateway"
    digest = compute_sha256_bytes(data)
    assert digest.startswith("sha256:")
    assert len(digest) == 7 + 64

    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(data)
        f_path = Path(f.name)

    try:
        file_digest = compute_sha256_file(f_path)
        assert file_digest == digest
    finally:
        f_path.unlink()


def test_byte_sniffing_ignores_misleading_extension():
    """Directive: Ignore dataset metadata labels entirely. Inspect actual bytes."""
    # PNG signature bytes
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    
    # File disguised with .txt or .public_domain extension
    with tempfile.NamedTemporaryFile(suffix=".public_domain", delete=False) as f:
        f.write(png_bytes)
        f_path = Path(f.name)

    try:
        asset = AssetInput.from_file(f_path)
        # Even though extension is .public_domain, track MUST be detected as IMAGE
        assert asset.track == TrackType.IMAGE
        assert asset.mime_type == "image/png"
        assert asset.sha256_hash.startswith("sha256:")
    finally:
        f_path.unlink()


def test_text_asset_detection():
    sample_text = "This is a clean excerpt from a training corpus."
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w", encoding="utf-8") as f:
        f.write(sample_text)
        f_path = Path(f.name)

    try:
        asset = AssetInput.from_file(f_path)
        assert asset.track == TrackType.TEXT
        assert asset.mime_type == "text/plain"
        assert asset.read_text().strip() == sample_text
    finally:
        f_path.unlink()


def test_crypto_signer_and_certificate_verification():
    signer = CryptoSigner.generate(key_size=2048)
    asset_hash = "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    cert = signer.issue_certificate("sample_asset_001.txt", asset_hash)
    assert isinstance(cert, ClearanceCertificate)
    assert cert.asset_id == "sample_asset_001.txt"
    assert cert.asset_hash == asset_hash
    assert cert.signature_algorithm == "RSASSA-PSS-SHA256"

    # Verify signature passes
    assert signer.verify_signature(asset_hash, cert.signature_b64) is True

    # Verify tampered hash fails
    tampered_hash = "sha256:0000000000000000000000000000000000000000000000000000000000000000"
    assert signer.verify_signature(tampered_hash, cert.signature_b64) is False


def test_crypto_key_persistence(tmp_path: Path):
    signer = CryptoSigner.generate(key_size=2048)
    priv_p, pub_p = signer.save_keys(tmp_path)

    assert priv_p.exists()
    assert pub_p.exists()

    loaded = CryptoSigner.load_from_files(private_key_path=priv_p, public_key_path=pub_p)
    assert loaded.key_fingerprint == signer.key_fingerprint

    asset_hash = "sha256:abcd1234ef"
    sig = loaded.sign_hash(asset_hash)
    assert loaded.verify_signature(asset_hash, sig) is True


def test_prov_lineage_schema():
    asset = AssetInput(
        asset_id="test_file.txt",
        file_path=Path("test_file.txt"),
        track=TrackType.TEXT,
        mime_type="text/plain",
        size_bytes=100,
        sha256_hash="sha256:abcdef",
    )
    lineage = build_prov_lineage(
        asset=asset,
        status="PASSED",
        certificate_id="123e4567-e89b-12d3-a456-426614174000",
    )

    assert lineage["@type"] == "prov:Entity"
    assert lineage["prov:wasGeneratedBy"]["@type"] == "prov:Activity"
    assert lineage["prov:wasGeneratedBy"]["traceai:resolutionStatus"] == "PASSED"
    assert lineage["prov:wasGeneratedBy"]["traceai:certificateId"] == "123e4567-e89b-12d3-a456-426614174000"


def test_asset_evaluation_minimal_json_format():
    """Verify output schema matches exact prompt requirement."""
    evaluation = AssetEvaluation(
        asset_id="book_excerpt_0421.txt",
        status=AssetStatus.BLOCKED,
        track=TrackType.TEXT,
        matched_source="© O'Reilly Media",
        similarity_score=0.94,
        asset_hash="sha256:9f3c0000e7a1",
        certificate_id=None,
    )

    minimal = evaluation.to_minimal_dict()
    expected = {
        "asset_id": "book_excerpt_0421.txt",
        "status": "BLOCKED",
        "track": "TEXT",
        "matched_source": "© O'Reilly Media",
        "similarity_score": 0.94,
        "asset_hash": "sha256:9f3c0000e7a1",
        "certificate_id": None,
    }
    assert minimal == expected
