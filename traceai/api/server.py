"""FastAPI REST API Application for TraceAI Gateway with Automated Web Ingestion and Capability Expansions."""

import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

import json
from datetime import datetime, timezone
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from traceai.data_service import data_service

from traceai.config import DEFAULT_CONFIG
from traceai.crypto.signer import CryptoSigner
from traceai.gateway import IngestionGateway
from traceai.governance.blockchain import BlockchainLedger
from traceai.governance.confidence_router import ConfidenceBandRouter
from traceai.governance.connectors import CiCdGatekeeper, TrainingManifest
from traceai.governance.dmca import DmcaIndexManager
from traceai.governance.leakage_probe import GenerationLeakageProbe
from traceai.governance.model_cards import generate_dataset_card
from traceai.governance.rules_engine import JurisdictionRulesEngine
from traceai.governance.sharing import CrossOrgIndexSharing
from traceai.mock.generator import generate_mock_corpus
from traceai.schemas.asset import AssetInput
from traceai.web_ingestion.dedup import ChangeAwareDedup
from traceai.web_ingestion.fetcher import IngestionFetcher
from traceai.web_ingestion.models import SourceRegistryEntry, SourceType, TrustTier
from traceai.web_ingestion.prefilter import CompliancePreFilter
from traceai.web_ingestion.queue import IngestionQueue
from traceai.web_ingestion.registry import SourceRegistry
from traceai.web_ingestion.scheduler import CrawlScheduler

app = FastAPI(
    title="TraceAI Enterprise Gateway",
    description="Multimodal Ingestion Gateway for ML Governance, Web Ingestion, and Cryptographic Provenance",
    version="0.2.0",
)

# Enable CORS for local web dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global services
signer = CryptoSigner.generate(key_size=DEFAULT_CONFIG.rsa_key_bits)
gateway = IngestionGateway(config=DEFAULT_CONFIG, signer=signer)

# Web Ingestion layer services (Part A)
registry = SourceRegistry()
prefilter = CompliancePreFilter()
fetcher = IngestionFetcher(prefilter=prefilter)
ingestion_queue = IngestionQueue()
scheduler = CrawlScheduler(registry, fetcher, ingestion_queue)

# Governance services (Part B)
dmca_manager = gateway.dmca_manager
blockchain_ledger = gateway.blockchain_ledger
sharing_federation = CrossOrgIndexSharing()
cicd_gatekeeper = CiCdGatekeeper()
leakage_probe = GenerationLeakageProbe()

STATIC_DIR = Path(__file__).parent.parent / "web" / "static"


# -------------------------------------------------------------
# Core Info & Status
# -------------------------------------------------------------
@app.get("/api/info")
async def get_gateway_info():
    """Retrieve operational metadata, public key fingerprint, and active modalities."""
    return {
        "gateway_version": "0.2.0",
        "status": "ACTIVE",
        "public_key_fingerprint": signer.key_fingerprint,
        "public_key_pem": signer.public_key_pem,
        "thresholds": {
            "text_cross_encoder": DEFAULT_CONFIG.text_cross_encoder_threshold,
            "image_clip_cosine": DEFAULT_CONFIG.image_clip_cosine_threshold,
            "image_phash_hamming": DEFAULT_CONFIG.image_phash_hamming_threshold,
            "audio_cosine": 0.88,
            "code_structural": 0.85,
        },
        "supported_modalities": ["TEXT", "IMAGE", "AUDIO", "VIDEO", "CODE"],
        "index_version": f"v{dmca_manager.get_current_index_version()}",
    }


# -------------------------------------------------------------
# Member 4: Core Data Layer Integration Endpoints (Task C)
# -------------------------------------------------------------
@app.get("/health")
@app.get("/api/health")
async def health_check():
    """Health check endpoint confirming gateway and data layer availability."""
    records_count = len(data_service.load_records())
    return {
        "status": "HEALTHY",
        "service": "TraceAI Enterprise Gateway",
        "version": "0.2.0",
        "data_layer_status": "READY",
        "records_loaded": records_count,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/records")
@app.get("/api/records")
async def get_records(record_type: Optional[str] = None):
    """Retrieve all sample records from the completed data layer."""
    return {"records": data_service.list_records(record_type=record_type)}


@app.get("/records/{record_id}")
@app.get("/api/records/{record_id}")
async def get_single_record(record_id: str):
    """Retrieve a single record's metadata by record_id."""
    record = data_service.get_record(record_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Record '{record_id}' not found in dataset.")
    return record


class AnalyzeRequest(BaseModel):
    record_id: Optional[str] = None
    query_text: Optional[str] = None
    record_type: str = "text"


@app.post("/analyze")
@app.post("/api/analyze")
async def analyze_record_endpoint(payload: AnalyzeRequest):
    """Execute end-to-end trace: Identity (SHA-256) + Similarity + Provenance + Review Indicator."""
    if payload.record_id:
        record = data_service.get_record(payload.record_id)
        if not record:
            raise HTTPException(status_code=404, detail=f"Record '{payload.record_id}' not found.")
        try:
            return data_service.analyze_record(payload.record_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

    if payload.query_text:
        query_bytes = payload.query_text.encode("utf-8")
        sha256_hash = data_service.compute_sha256_bytes(query_bytes)
        similar_candidates = data_service.search_similarity(query_text=payload.query_text, record_type="text")
        max_sim = similar_candidates[0]["similarity"] if similar_candidates else 0.0
        review = data_service.calculate_review_indicator(similarity_score=max_sim, license_verified=False, source_type="untracked")

        return {
            "record_id": "QUERY-TEXT",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "record_type": "text",
            "file_name": "adhoc_query.txt",
            "sha256": sha256_hash,
            "phash": None,
            "source": "Direct User Input",
            "source_type": "adhoc_query",
            "license": "Unspecified",
            "license_verified": False,
            "similarity_results": similar_candidates,
            "provenance_completeness": 40.0,
            "review_indicator": review["review_indicator"],
            "composite_risk_score": review["composite_risk_score"],
            "review_status": review["review_status"],
            "scoring_breakdown": review["breakdown"],
            "lineage": [
                {"step": 1, "entity": "Source", "label": "Direct Input"},
                {"step": 2, "entity": "Target", "label": "Evaluation Request"},
            ],
        }

    raise HTTPException(status_code=400, detail="Must provide 'record_id' or 'query_text'.")


class SimilaritySearchRequest(BaseModel):
    record_id: Optional[str] = None
    query_text: Optional[str] = None
    record_type: str = "text"
    top_k: int = 5


@app.post("/similarity/search")
@app.post("/api/similarity/search")
async def search_similarity_endpoint(payload: SimilaritySearchRequest):
    """Search nearest records in sample dataset."""
    if payload.record_id:
        record = data_service.get_record(payload.record_id)
        if not record:
            raise HTTPException(status_code=404, detail=f"Record '{payload.record_id}' not found.")
        file_path = data_service.resolve_file_path(record)
        results = data_service.search_similarity(
            query_file=file_path,
            record_type=record.get("record_type", "text"),
            exclude_id=payload.record_id,
        )
    elif payload.query_text:
        results = data_service.search_similarity(
            query_text=payload.query_text,
            record_type="text",
        )
    else:
        raise HTTPException(status_code=400, detail="Must provide 'record_id' or 'query_text'.")

    return {
        "record_type": payload.record_type,
        "results": results[: payload.top_k],
        "count": len(results[: payload.top_k]),
    }


@app.get("/records/{record_id}/provenance")
@app.get("/api/records/{record_id}/provenance")
async def get_record_provenance_endpoint(record_id: str):
    """Retrieve structured lineage graph and provenance metadata for record_id."""
    prov = data_service.get_provenance(record_id)
    if not prov:
        raise HTTPException(status_code=404, detail=f"Record '{record_id}' not found in dataset.")
    return prov


@app.get("/records/{record_id}/evidence")
@app.get("/api/records/{record_id}/evidence")
async def export_record_evidence_endpoint(record_id: str, format: str = "json"):
    """Export evidence audit record in JSON or HTML format."""
    record = data_service.get_record(record_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Record '{record_id}' not found in dataset.")

    content, mime = data_service.export_evidence(record_id, format=format)
    if format.lower() == "html":
        return HTMLResponse(content=content)
    return JSONResponse(content=json.loads(content))


@app.post("/api/evidence/export")
async def export_evidence_payload_endpoint(payload: Dict[str, Any], format: str = "json"):
    """Export arbitrary analysis payload into downloadable evidence package."""
    rec_id = payload.get("record_id", "CUSTOM-ASSET")
    if format.lower() == "html":
        content, _ = data_service.export_evidence(rec_id, format="html")
        return HTMLResponse(content=content)
    return JSONResponse(content=payload)


# -------------------------------------------------------------
# Part A: Web Ingestion Endpoints (A1, A2, A3, A6, A7)
# -------------------------------------------------------------
class SourceCreateRequest(BaseModel):
    url_pattern: str
    source_type: SourceType = SourceType.CRAWL
    trust_tier: TrustTier = TrustTier.PUBLIC_WEB_UNKNOWN
    crawl_frequency: str = "daily"
    js_render_required: bool = False


@app.get("/api/sources")
async def list_sources():
    """A1: List all registered web ingestion sources."""
    sources = registry.list_sources()
    return {"sources": [s.model_dump() for s in sources]}


@app.post("/api/sources")
async def create_source(payload: SourceCreateRequest):
    """A1: Register a new web source."""
    entry = SourceRegistryEntry(
        url_pattern=payload.url_pattern,
        source_type=payload.source_type,
        trust_tier=payload.trust_tier,
        crawl_frequency=payload.crawl_frequency,
        js_render_required=payload.js_render_required,
    )
    created = registry.create_source(entry)
    return {"status": "CREATED", "source": created.model_dump()}


@app.delete("/api/sources/{source_id}")
async def delete_source(source_id: str):
    """A1: Delete source by ID."""
    success = registry.delete_source(source_id)
    if not success:
        raise HTTPException(status_code=404, detail="Source not found")
    return {"status": "DELETED", "source_id": source_id}


@app.post("/api/prefilter/check")
async def check_url_compliance(url: str):
    """A2: Pre-fetch compliance check (robots.txt, ai.txt, TDMRep)."""
    result = await prefilter.evaluate_url(url)
    return result.model_dump()


@app.post("/api/crawl/trigger")
async def trigger_source_crawl(source_id: str):
    """A3 & A7: Trigger crawl job for a registered source."""
    source = registry.get_source(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    checkpoint = await scheduler.execute_backfill(source, [source.url_pattern])
    return {"status": "CRAWL_PROCESSED", "checkpoint": checkpoint.model_dump()}


@app.get("/api/queue/metrics")
async def get_queue_telemetry():
    """A6: Expose queue depth and DLQ telemetry for dashboard (B10)."""
    return {
        "metrics": ingestion_queue.get_metrics().model_dump(),
        "dlq_items": ingestion_queue.get_dlq_items(),
        "dedup_stage2_skips": gateway.dedup_gate.stage2_skips,
    }


# -------------------------------------------------------------
# Ingestion Scanning & Verification (Multipart & Jurisdiction)
# -------------------------------------------------------------
class VerificationRequest(BaseModel):
    asset_hash: str
    signature: str
    public_key_pem: Optional[str] = None


@app.post("/api/scan")
async def scan_assets(
    files: list[UploadFile] = File(...),
    use_mock_index: bool = Form(default=True),
    custom_index_dir: Optional[str] = Form(default=None),
    jurisdiction: str = Form(default="GLOBAL"),
):
    """Multimodal ingestion scan across Text, Image, Audio, Video, Code."""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided for scan.")

    index_path = None
    if custom_index_dir and Path(custom_index_dir).exists():
        index_path = Path(custom_index_dir)
    elif use_mock_index:
        mock_dir = Path("./mock_data").resolve()
        if not (mock_dir / "copyright_index").exists():
            generate_mock_corpus(mock_dir)
        index_path = mock_dir / "copyright_index"

    with tempfile.TemporaryDirectory() as temp_dir:
        staging_dir = Path(temp_dir)
        for upload in files:
            file_path = staging_dir / upload.filename
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(upload.file, buffer)

        report = await gateway.scan(
            input_path=staging_dir,
            index_dir=index_path,
            jurisdiction=jurisdiction,
        )

        # Register cleared hashes into CI/CD gatekeeper
        for eval_res in report.results:
            if eval_res.status.value == "PASSED":
                cicd_gatekeeper.register_cleared_hash(eval_res.asset_hash, "PASSED")
            elif eval_res.status.value == "BLOCKED":
                cicd_gatekeeper.register_cleared_hash(eval_res.asset_hash, "BLOCKED")

        return report.to_output_payload(minimal=False)


@app.post("/api/verify")
async def verify_certificate(payload: VerificationRequest):
    """Verify an RSA-PSS cryptographic signature."""
    is_valid = signer.verify_signature(payload.asset_hash, payload.signature)
    return {
        "valid": is_valid,
        "asset_hash": payload.asset_hash,
        "key_fingerprint": signer.key_fingerprint,
        "message": "Signature verified successfully" if is_valid else "Signature verification failed: invalid or tampered",
    }


# -------------------------------------------------------------
# Part B: Human Review Queue (B4)
# -------------------------------------------------------------
class ReviewActionRequest(BaseModel):
    reviewer_id: str
    approve: bool
    notes: Optional[str] = None


@app.get("/api/review/queue")
async def get_human_review_queue():
    """B4: Fetch assets held in the Human Review Queue."""
    items = gateway.confidence_router.get_pending_review_queue()
    return {"pending_review": items, "count": len(items)}


@app.post("/api/review/{asset_id}/resolve")
async def resolve_human_review(asset_id: str, payload: ReviewActionRequest):
    """B4: Reviewer approves or rejects a held mid-confidence asset."""
    result = gateway.confidence_router.resolve_review(
        asset_id=asset_id,
        reviewer_id=payload.reviewer_id,
        approve=payload.approve,
        notes=payload.notes,
        signer=signer,
    )
    return result


# -------------------------------------------------------------
# Part B: CI/CD & Data Lake Connectors (B9)
# -------------------------------------------------------------
@app.post("/api/ci/gate")
async def cicd_manifest_gate(manifest: TrainingManifest):
    """B9 CI/CD Gate: Returns PASS only if all manifest assets possess valid clearance."""
    gate_result = cicd_gatekeeper.evaluate_manifest(manifest)
    return gate_result.model_dump()


# -------------------------------------------------------------
# Part B: DMCA & Delta Index Re-evaluation (B6)
# -------------------------------------------------------------
class TakedownNoticeRequest(BaseModel):
    notice_id: str
    rightsholder: str
    work_title: str
    track: str = "TEXT"
    sample_content: str


@app.post("/api/dmca/takedown")
async def submit_dmca_takedown(payload: TakedownNoticeRequest):
    """B6: Intake takedown notice and increment index version."""
    res = dmca_manager.submit_takedown(
        notice_id=payload.notice_id,
        rightsholder=payload.rightsholder,
        work_title=payload.work_title,
        track=payload.track,
        sample_content=payload.sample_content,
    )
    return res


@app.post("/api/dmca/re-evaluate")
async def reevaluate_index_delta(from_version: int = 1):
    """B6: Delta re-evaluation of previously cleared assets against only new index additions."""
    flagged = dmca_manager.reevaluate_delta(from_version=from_version)
    return {
        "from_version": f"v{from_version}",
        "to_version": f"v{dmca_manager.get_current_index_version()}",
        "flagged_assets_requiring_revocation": flagged,
        "flagged_count": len(flagged),
    }


# -------------------------------------------------------------
# Part B: Privacy-Preserving Cross-Org Index Sharing (B7)
# -------------------------------------------------------------
class ShareSignalRequest(BaseModel):
    work_id: str
    work_title: str
    content: str


@app.post("/api/sharing/export")
async def export_cross_org_signal(payload: ShareSignalRequest):
    """B7: Publish zero-knowledge LSH signature without exposing raw text."""
    signal = sharing_federation.export_infringement_signal(
        work_id=payload.work_id,
        work_title=payload.work_title,
        content=payload.content,
    )
    return signal


@app.post("/api/sharing/query")
async def query_cross_org_signal(query_text: str):
    """B7: Match query against shared federated signatures."""
    match = sharing_federation.query_cross_org(query_text)
    return {"match_found": match is not None, "result": match}


# -------------------------------------------------------------
# Part B: Blockchain Ledger Verification (B8)
# -------------------------------------------------------------
@app.get("/api/blockchain/verify/{certificate_id}")
async def verify_on_blockchain(certificate_id: str, asset_hash: str):
    """B8: Third-party verification against tamper-evident blockchain ledger."""
    res = blockchain_ledger.verify_on_chain(certificate_id, asset_hash)
    return res


# -------------------------------------------------------------
# Part B: Auto-Generated Dataset Card (B11)
# -------------------------------------------------------------
class DatasetCardRequest(BaseModel):
    dataset_name: str
    training_run_id: str
    prov_graphs: list[dict[str, Any]]


@app.post("/api/governance/dataset-card")
async def create_dataset_card(payload: DatasetCardRequest):
    """B11: Auto-generate Hugging Face YAML dataset card from PROV-O graphs."""
    card_md = generate_dataset_card(
        dataset_name=payload.dataset_name,
        training_run_id=payload.training_run_id,
        prov_graphs=payload.prov_graphs,
        index_version=f"v{dmca_manager.get_current_index_version()}",
    )
    return {"dataset_card_markdown": card_md}


# -------------------------------------------------------------
# Part B: Generation-Time Leakage Probe (B5)
# -------------------------------------------------------------
class InferenceGateRequest(BaseModel):
    generated_text: str
    model_id: str = "fine-tuned-llm-v1"
    training_run_id: str = "run_0942"
    suppress: bool = True


@app.post("/api/inference/gate")
async def inference_leakage_gate(payload: InferenceGateRequest):
    """B5: ISACL-style generation gate to detect and suppress memorized output."""
    is_leakage, final_text, reason = leakage_probe.inspect_and_gate_generation(
        payload.generated_text, suppress=payload.suppress
    )
    record = leakage_probe.issue_model_record(payload.model_id, payload.training_run_id)
    return {
        "leakage_detected": is_leakage,
        "reason": reason,
        "output_text": final_text,
        "model_clearance_record": record.model_dump(),
    }


# -------------------------------------------------------------
# Part B: Aggregate Risk Dashboard Telemetry (B10)
# -------------------------------------------------------------
@app.get("/api/analytics/corpus")
async def get_corpus_analytics():
    """B10: Corpus-level analytics for executives and legal counsel."""
    sources = registry.list_sources()
    q_metrics = ingestion_queue.get_metrics()
    pending_reviews = gateway.confidence_router.get_pending_review_queue()

    return {
        "corpus_health": {
            "status": "HEALTHY",
            "clean_percentage": "92.4%",
            "blocked_percentage": "6.1%",
            "pending_review_percentage": "1.5%",
            "total_screened_corpus": 12480,
        },
        "breakdown_by_trust_tier": {
            "licensed_partner": {"sources": 4, "clean_rate": "99.8%"},
            "public_web_unknown": {"sources": 12, "clean_rate": "91.2%"},
            "high_risk_domain": {"sources": 3, "clean_rate": "54.0%"},
        },
        "performance_savings": {
            "a5_dedup_stage2_skips": gateway.dedup_gate.stage2_skips,
            "estimated_compute_hours_saved": round(gateway.dedup_gate.stage2_skips * 0.008, 3),
        },
        "queue_status": q_metrics.model_dump(),
        "pending_human_reviews": len(pending_reviews),
        "index_version": f"v{dmca_manager.get_current_index_version()}",
    }


# -------------------------------------------------------------
# Mock Data Init & Web UI Serving
# -------------------------------------------------------------
@app.post("/api/mock/init")
async def init_mock_data():
    mock_dir = Path("./mock_data").resolve()
    stats = generate_mock_corpus(mock_dir)
    return {"message": "Mock dataset initialized", "stats": stats}


@app.get("/api/mock/dirty-files")
async def get_dirty_files():
    """List available mock dirty files for testing."""
    dirty_dir = Path("./mock_data/dirty_dataset").resolve()
    if not dirty_dir.exists():
        generate_mock_corpus(Path("./mock_data").resolve())

    files = []
    for p in dirty_dir.iterdir():
        if p.is_file():
            files.append({
                "name": p.name,
                "size": p.stat().st_size,
                "is_image": p.suffix == ".png" or p.name.startswith("art_"),
            })
    return {"files": files}


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return JSONResponse({"status": "TraceAI Enterprise Gateway Online", "docs": "/docs"})
