"""End-to-end and CLI tests for TraceAI Gateway."""

import json
import tempfile
from pathlib import Path
from traceai import cli
from traceai.crypto.signer import CryptoSigner


def test_cli_help():
    assert cli.main([]) == 0


def test_cli_generate_keys_and_scan(tmp_path: Path):
    keys_dir = tmp_path / "keys"
    data_dir = tmp_path / "data"
    output_json = tmp_path / "scan_output.json"

    data_dir.mkdir(parents=True, exist_ok=True)
    keys_dir.mkdir(parents=True, exist_ok=True)

    # Create dummy text and image assets
    (data_dir / "clean_sample_1.txt").write_text("Unique uncopyrighted machine learning data asset.", encoding="utf-8")
    
    # 1x1 dummy PNG bytes
    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    (data_dir / "clean_sample_2.png").write_bytes(png_bytes)

    # 1. Generate keys
    ret_keys = cli.main(["generate-keys", "--output-dir", str(keys_dir)])
    assert ret_keys == 0
    priv_key = keys_dir / "traceai_private.pem"
    pub_key = keys_dir / "traceai_public.pem"
    assert priv_key.exists()
    assert pub_key.exists()

    # 2. Run scan
    ret_scan = cli.main([
        "scan",
        "--input-dir", str(data_dir),
        "--output", str(output_json),
        "--private-key", str(priv_key),
    ])
    assert ret_scan == 0
    assert output_json.exists()

    # 3. Verify JSON output content
    with open(output_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["summary"]["total_assets"] == 2
    assert data["summary"]["passed_count"] == 2
    assert data["summary"]["blocked_count"] == 0

    # Ensure certificates are issued for both clean assets
    first_result = data["results"][0]
    assert first_result["status"] == "PASSED"
    assert first_result["certificate_id"] is not None
    assert first_result["certificate"] is not None

    cert = first_result["certificate"]
    assert cert["signature_b64"] is not None

    # 4. Verify certificate using verify-cert CLI command
    ret_verify = cli.main([
        "verify-cert",
        "--asset-hash", cert["asset_hash"],
        "--signature", cert["signature_b64"],
        "--public-key", str(pub_key),
    ])
    assert ret_verify == 0
