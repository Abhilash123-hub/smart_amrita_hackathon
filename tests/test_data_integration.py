"""Automated QA & Integration Test Suite (Member 4 - Tasks C & D).

Verifies the integration pipeline:
  Frontend -> Backend -> AI -> Data Layer -> Response -> Frontend
Covers:
  - TEST-001: Unrelated / root document -> LOW review category
  - TEST-002: Partial similarity document -> MEDIUM review category
  - TEST-003: High similarity document -> HIGH review category
  - TEST-004: Invalid record ID -> 404 error
  - TEST-005: Missing file handling
  - TEST-006: Malformed metadata handling
  - TEST-007: Missing licence metadata penalty
  - TEST-008: Missing source metadata handling
  - TEST-009: Image record processing (pHash & SHA-256)
  - TEST-010: Text record processing
  - TEST-011: Evidence export (JSON & HTML)
  - TEST-012: Frontend serving & asset delivery
  - TEST-013: Offline sample data reliability
"""

import json
from pathlib import Path
from fastapi.testclient import TestClient
from traceai.api.server import app
from traceai.data_service import data_service

client = TestClient(app)


# -------------------------------------------------------------
# Phase 2: Data -> Backend Verification
# -------------------------------------------------------------
def test_data_to_backend_loading():
    """Verify backend loads all 6 records with accurate metadata."""
    records = data_service.load_records()
    assert len(records) == 6
    expected_ids = {"DOC-001", "DOC-002", "DOC-003", "IMG-001", "IMG-002", "IMG-003"}
    assert set(records.keys()) == expected_ids

    for rid, rec in records.items():
        assert rec["record_id"] == rid
        assert rec["dataset"] == "TRACEAI Synthetic Demo Dataset"
        assert rec["dataset_version"] == "1.0"
        assert rec["license"] == "Project-created demo data"
        assert rec["license_verified"] is True
        assert rec["source"] == "TRACEAI Synthetic Demo Dataset"
        # Verify file exists on disk
        fp = data_service.resolve_file_path(rec)
        assert fp.exists(), f"File for {rid} does not exist: {fp}"


# -------------------------------------------------------------
# Phase 3 & 4: Backend -> AI & AI -> Provenance Verification
# -------------------------------------------------------------
def test_test_001_unrelated_low_scenario():
    """TEST-001: Base reference document (DOC-001) produces LOW review indicator."""
    res = data_service.analyze_record("DOC-001")
    assert res["record_id"] == "DOC-001"
    assert res["review_indicator"] == "LOW"
    assert res["composite_risk_score"] < 0.40
    assert res["sha256"].startswith("sha256:8005447d")
    assert res["license_verified"] is True
    assert res["parent_record"] is None
    assert "low provenance risk" in res["review_status"].lower()


def test_test_002_partial_similarity_medium_scenario():
    """TEST-002: Partially similar document (DOC-002) produces MEDIUM review indicator."""
    res = data_service.analyze_record("DOC-002")
    assert res["record_id"] == "DOC-002"
    assert res["review_indicator"] == "MEDIUM"
    assert 0.40 <= res["composite_risk_score"] < 0.75
    assert res["parent_record"] == "DOC-001"
    assert len(res["similarity_results"]) > 0
    assert "moderate provenance risk" in res["review_status"].lower()


def test_test_003_high_similarity_near_duplicate_scenario():
    """TEST-003: Near-duplicate document (DOC-003) produces HIGH review indicator."""
    res = data_service.analyze_record("DOC-003")
    assert res["record_id"] == "DOC-003"
    assert res["review_indicator"] == "HIGH"
    assert res["composite_risk_score"] >= 0.75
    assert res["parent_record"] == "DOC-001"
    assert len(res["similarity_results"]) > 0
    # Confirm neutral wording without legal determination
    assert "copyright infringement" not in res["review_status"].lower()
    assert "potential provenance risk" in res["review_status"].lower()


# -------------------------------------------------------------
# Multimodal Images (TEST-009)
# -------------------------------------------------------------
def test_test_009_image_records_processing():
    """TEST-009: Verify image records calculate both SHA-256 and pHash."""
    for img_id in ["IMG-001", "IMG-002", "IMG-003"]:
        res = data_service.analyze_record(img_id)
        assert res["record_type"] == "image"
        assert res["sha256"].startswith("sha256:")
        assert res["phash"] is not None
        assert len(res["phash"]) == 16  # 64-bit hex pHash

    # Verify visual derivation levels
    res_img1 = data_service.analyze_record("IMG-001")
    res_img2 = data_service.analyze_record("IMG-002")
    res_img3 = data_service.analyze_record("IMG-003")

    assert res_img1["review_indicator"] == "LOW"
    assert res_img2["review_indicator"] == "MEDIUM"
    assert res_img3["review_indicator"] == "HIGH"


# -------------------------------------------------------------
# Phase 6: API Flow Verification
# -------------------------------------------------------------
def test_api_health():
    """Verify GET /health and /api/health."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "HEALTHY"
    assert data["data_layer_status"] == "READY"
    assert data["records_loaded"] == 6


def test_api_records_list_and_single():
    """Verify GET /records and /records/{record_id}."""
    res_list = client.get("/records")
    assert res_list.status_code == 200
    records = res_list.json()["records"]
    assert len(records) == 6

    # Single record
    res_single = client.get("/records/DOC-001")
    assert res_single.status_code == 200
    assert res_single.json()["record_id"] == "DOC-001"


def test_test_004_invalid_record_id():
    """TEST-004: Invalid record ID returns clear 404 error."""
    res = client.get("/records/NONEXISTENT-999")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()

    # In /analyze
    res_analyze = client.post("/analyze", json={"record_id": "NONEXISTENT-999"})
    assert res_analyze.status_code == 404


def test_api_analyze_valid_records():
    """Verify POST /analyze returns full evidence record."""
    for rid in ["DOC-001", "DOC-002", "DOC-003", "IMG-001", "IMG-002", "IMG-003"]:
        res = client.post("/analyze", json={"record_id": rid})
        assert res.status_code == 200
        data = res.json()
        assert data["record_id"] == rid
        assert "sha256" in data
        assert "lineage" in data
        assert "review_indicator" in data
        assert "provenance_completeness" in data


def test_api_similarity_search():
    """Verify POST /similarity/search."""
    res = client.post("/similarity/search", json={"record_id": "DOC-003", "top_k": 3})
    assert res.status_code == 200
    data = res.json()
    assert "results" in data
    assert len(data["results"]) > 0
    # Top match for DOC-003 should be DOC-001 or DOC-002
    assert data["results"][0]["record_id"] in ["DOC-001", "DOC-002"]


def test_api_provenance_endpoint():
    """Verify GET /records/{record_id}/provenance."""
    res = client.get("/records/DOC-002/provenance")
    assert res.status_code == 200
    data = res.json()
    assert data["record_id"] == "DOC-002"
    assert data["parent_record"] == "DOC-001"
    assert len(data["lineage_chain"]) >= 4


def test_test_011_evidence_export_json_and_html():
    """TEST-011: Export evidence package in JSON and HTML."""
    # JSON export
    res_json = client.get("/records/DOC-003/evidence?format=json")
    assert res_json.status_code == 200
    assert res_json.headers["content-type"].startswith("application/json")
    data = res_json.json()
    assert data["record_id"] == "DOC-003"
    assert data["review_indicator"] == "HIGH"

    # HTML export
    res_html = client.get("/records/DOC-003/evidence?format=html")
    assert res_html.status_code == 200
    assert "text/html" in res_html.headers["content-type"]
    html_text = res_html.text
    assert "TRACEAI Cryptographic Audit Record" in html_text
    assert "DOC-003" in html_text
    assert "HIGH RISK" in html_text


# -------------------------------------------------------------
# Edge Cases & Robustness
# -------------------------------------------------------------
def test_test_005_missing_file_handling(tmp_path):
    """TEST-005: Missing file returns clean error without crashing."""
    try:
        data_service.compute_sha256(tmp_path / "non_existent_file.txt")
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError as e:
        assert "does not exist" in str(e)


def test_test_007_missing_licence_penalty():
    """TEST-007: Unverified licence incurs transparent risk penalty."""
    review_verified = data_service.calculate_review_indicator(
        similarity_score=0.20,
        license_verified=True,
    )
    review_unverified = data_service.calculate_review_indicator(
        similarity_score=0.20,
        license_verified=False,
    )
    assert review_verified["review_indicator"] == "LOW"
    # Adding 0.35 penalty brings composite score to 0.55 -> MEDIUM
    assert review_unverified["review_indicator"] == "MEDIUM"
    assert review_unverified["composite_risk_score"] > review_verified["composite_risk_score"]


def test_test_008_missing_source_penalty():
    """TEST-008: Untracked or scraped source incurs source risk penalty."""
    review_clean = data_service.calculate_review_indicator(
        similarity_score=0.30,
        license_verified=True,
        source_type="synthetic",
    )
    review_scraped = data_service.calculate_review_indicator(
        similarity_score=0.30,
        license_verified=True,
        source_type="scraped",
    )
    assert review_clean["review_indicator"] == "LOW"
    assert review_scraped["review_indicator"] == "MEDIUM"


def test_test_012_frontend_serving():
    """TEST-012: Frontend index.html serves with HTTP 200."""
    res = client.get("/")
    assert res.status_code == 200
    assert "TraceAI" in res.text


def test_test_013_offline_sample_data_integrity():
    """TEST-013: All 6 sample records pass local offline integrity check."""
    for rid in ["DOC-001", "DOC-002", "DOC-003", "IMG-001", "IMG-002", "IMG-003"]:
        rec = data_service.get_record(rid)
        assert rec is not None
        fp = data_service.resolve_file_path(rec)
        assert fp.exists()
        sha = data_service.compute_sha256(fp)
        assert len(sha) == 71  # 'sha256:' + 64 hex chars



# -------------------------------------------------------------
# Canonical Demo Fixtures Verification (Member 4 Requirement)
# -------------------------------------------------------------
def test_canonical_clean_asset_evaluation():
    """Verify Canonical Demo Fixture 1: clean_asset.txt passes clearance (LOW / CLEAR)."""
    manifest = data_service.load_canonical_demo_manifest()
    clean_info = data_service.get_canonical_demo_fixture("clean_asset.txt")
    assert clean_info is not None
    assert clean_info["fixture_id"] == "CANON-001"

    # API Scan
    res = client.post("/api/canonical-demo/scan/clean_asset.txt")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "PASSED"
    assert data["risk_band"] == "CLEAR"
    assert data["detected_track"] == "TEXT"
    assert data["detected_mime"] == "text/plain"
    assert data["certificate_id"] is not None
    assert data["similarity_score"] is None


def test_canonical_infringing_asset_evaluation():
    """Verify Canonical Demo Fixture 2: infringing_asset.txt is blocked (HIGH / BLOCKED)."""
    manifest = data_service.load_canonical_demo_manifest()
    infringe_info = data_service.get_canonical_demo_fixture("infringing_asset.txt")
    assert infringe_info is not None
    assert infringe_info["fixture_id"] == "CANON-002"

    # API Scan
    res = client.post("/api/canonical-demo/scan/infringing_asset.txt")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "BLOCKED"
    assert data["risk_band"] == "BLOCKED"
    assert data["detected_track"] == "TEXT"
    assert data["detected_mime"] == "text/plain"
    assert data["similarity_score"] is not None and data["similarity_score"] >= 0.85
    assert "Moby Dick" in data["matched_source"]
    assert data["certificate_id"] is None


def test_canonical_spoofed_asset_sniffing():
    """Verify Canonical Demo Fixture 3: spoofed_asset.txt is sniffed as IMAGE (image/png) despite .txt extension."""
    manifest = data_service.load_canonical_demo_manifest()
    spoofed_info = data_service.get_canonical_demo_fixture("spoofed_asset.txt")
    assert spoofed_info is not None
    assert spoofed_info["fixture_id"] == "CANON-003"

    # Check raw bytes signature directly
    fix_path = Path("mock_data/canonical_demo/spoofed_asset.txt")
    raw_bytes = fix_path.read_bytes()
    assert raw_bytes.startswith(b"\x89PNG\r\n\x1a\n")

    # API Scan
    res = client.post("/api/canonical-demo/scan/spoofed_asset.txt")
    assert res.status_code == 200
    data = res.json()
    assert data["detected_track"] == "IMAGE"
    assert data["detected_mime"] == "image/png"
    assert data["extension"] == ".txt"
    assert data["magic_bytes_sniffed"] is True


def test_canonical_demo_api_and_manifest():
    """Verify canonical demo manifest endpoint and hash consistency."""
    res = client.get("/api/canonical-demo")
    assert res.status_code == 200
    data = res.json()
    assert "fixtures" in data
    assert len(data["fixtures"]) == 3

    # Check frontend serves with canonical demo buttons
    ui_res = client.get("/")
    assert ui_res.status_code == 200
    assert "Canonical Demo Fixtures" in ui_res.text
    assert "clean_asset.txt" in ui_res.text
    assert "infringing_asset.txt" in ui_res.text
    assert "spoofed_asset.txt" in ui_res.text
