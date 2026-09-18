"""Unit and integration tests for FastAPI Web Platform endpoints."""

import io
from fastapi.testclient import TestClient
from traceai.api.server import app, signer

client = TestClient(app)


def test_api_info():
    response = client.get("/api/info")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ACTIVE"
    assert data["public_key_fingerprint"].startswith("sha256:")
    assert "TEXT" in data["supported_modalities"]
    assert "IMAGE" in data["supported_modalities"]


def test_api_scan_upload_clean():
    # Test uploading clean text asset
    file_content = b"Novel instruction dataset for open-weights transformer fine-tuning."
    files = [
        ("files", ("dataset_clean.txt", io.BytesIO(file_content), "text/plain"))
    ]
    response = client.post("/api/scan", files=files)
    assert response.status_code == 200
    report = response.json()
    assert report["summary"]["total_assets"] == 1
    assert report["summary"]["passed_count"] == 1
    assert report["results"][0]["status"] == "PASSED"
    assert report["results"][0]["certificate_id"] is not None


def test_api_verify_signature():
    # Generate valid signature
    test_hash = "sha256:4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a"
    valid_sig = signer.sign_hash(test_hash)

    # Test valid verification
    res_valid = client.post("/api/verify", json={
        "asset_hash": test_hash,
        "signature": valid_sig
    })
    assert res_valid.status_code == 200
    assert res_valid.json()["valid"] is True

    # Test invalid / tampered verification
    res_invalid = client.post("/api/verify", json={
        "asset_hash": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
        "signature": valid_sig
    })
    assert res_invalid.status_code == 200
    assert res_invalid.json()["valid"] is False


def test_api_mock_init_and_list():
    res_init = client.post("/api/mock/init")
    assert res_init.status_code == 200
    assert res_init.json()["stats"]["total_index_works"] == 100

    res_list = client.get("/api/mock/dirty-files")
    assert res_list.status_code == 200
    files = res_list.json()["files"]
    assert len(files) == 10
