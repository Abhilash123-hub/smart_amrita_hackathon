"""FastAPI Application for TraceAI Ingestion Gateway (Task Cards T1.7, T2.5)."""

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel

from src.traceai.config import DEFAULT_CONFIG
from src.traceai.core.models import AssetInput, ClearanceCertificate, IngestRequest, ScanResult, Track, Verdict
from src.traceai.worker import BatchWorker

app = FastAPI(
    title="TraceAI Ingestion Gateway",
    version="0.1.0",
    description="Content-Level IP Defense & Provenance Infrastructure for Enterprise AI",
)

# In-memory batch store for idempotency & queryability
_BATCH_STORE: dict[str, dict] = {}
_WORKER = BatchWorker(config=DEFAULT_CONFIG)


class IngestResponse(BaseModel):
    batch_id: str
    status: str
    total_assets: int
    passed_count: int
    blocked_count: int
    review_count: int
    results: list[ScanResult]
    idempotent_cached: bool = False


@app.get("/api/info")
def get_info():
    """Service health and engine info."""
    return {
        "status": "healthy",
        "service": "traceai-gateway",
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/v1/ingest", response_model=IngestResponse)
def ingest_batch(
    payload: IngestRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """Submit an ingestion batch for multimodal scanning with idempotency."""
    key = idempotency_key or payload.batch_id

    # Check idempotency
    if key in _BATCH_STORE:
        cached = _BATCH_STORE[key]
        return IngestResponse(
            batch_id=payload.batch_id,
            status="completed",
            total_assets=len(cached["results"]),
            passed_count=sum(1 for r in cached["results"] if r.verdict == Verdict.PASSED),
            blocked_count=sum(1 for r in cached["results"] if r.verdict == Verdict.BLOCKED),
            review_count=sum(1 for r in cached["results"] if r.verdict == Verdict.REVIEW),
            results=cached["results"],
            idempotent_cached=True,
        )

    results: list[ScanResult] = []
    for asset in payload.assets:
        # Resolve bytes: check if source_uri is a local file or download
        p = Path(asset.source_uri)
        if p.exists() and p.is_file():
            raw_bytes = p.read_bytes()
        else:
            raw_bytes = asset.source_uri.encode("utf-8")

        res = _WORKER.process_asset(asset, raw_bytes)
        results.append(res)

    _BATCH_STORE[key] = {
        "batch_id": payload.batch_id,
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
    }

    return IngestResponse(
        batch_id=payload.batch_id,
        status="completed",
        total_assets=len(results),
        passed_count=sum(1 for r in results if r.verdict == Verdict.PASSED),
        blocked_count=sum(1 for r in results if r.verdict == Verdict.BLOCKED),
        review_count=sum(1 for r in results if r.verdict == Verdict.REVIEW),
        results=results,
        idempotent_cached=False,
    )


@app.get("/v1/batches/{batch_id}")
def get_batch(batch_id: str):
    """Retrieve per-asset results and progress for an existing batch."""
    if batch_id not in _BATCH_STORE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch {batch_id} not found",
        )
    cached = _BATCH_STORE[batch_id]
    return cached


@app.get("/v1/metrics/summary")
def get_metrics_summary():
    """Live telemetry KPI metrics for operations console."""
    all_results = []
    for b in _BATCH_STORE.values():
        all_results.extend(b.get("results", []))

    total = len(all_results)
    blocked = sum(1 for r in all_results if r.verdict == Verdict.BLOCKED)
    passed = sum(1 for r in all_results if r.verdict == Verdict.PASSED)
    review = sum(1 for r in all_results if r.verdict == Verdict.REVIEW)

    block_rate = (blocked / total * 100) if total > 0 else 0.0
@app.get("/v1/keys/public")
def get_public_key():
    """Public key distribution endpoint with key rotation metadata (T2.5)."""
    from src.traceai.core.crypto import CryptoSigner
    global _GLOBAL_SIGNER
    if "_GLOBAL_SIGNER" not in globals() or _GLOBAL_SIGNER is None:
        _GLOBAL_SIGNER = CryptoSigner.generate(key_size=DEFAULT_CONFIG.rsa_key_bits)

    return {
        "key_id": "key-2026-v1",
        "algorithm": "RSASSA-PSS-SHA256",
        "public_key_pem": _GLOBAL_SIGNER.export_public_key_pem(),
        "status": "ACTIVE",
    }


class VerifyRequest(BaseModel):
    certificate: ClearanceCertificate
    raw_content_b64: Optional[str] = None
    raw_content_text: Optional[str] = None


@app.post("/v1/verify")
def verify_clearance_certificate(payload: VerifyRequest):
    """Attorney verification endpoint: cryptographically verifies certificate and asset hash."""
    from src.traceai.core.crypto import CryptoSigner, hash_asset_bytes
    global _GLOBAL_SIGNER
    if "_GLOBAL_SIGNER" not in globals() or _GLOBAL_SIGNER is None:
        _GLOBAL_SIGNER = CryptoSigner.generate(key_size=DEFAULT_CONFIG.rsa_key_bits)

    cert = payload.certificate

    # 1. Compute hash of submitted asset bytes
    if payload.raw_content_b64:
        import base64
        raw_bytes = base64.b64decode(payload.raw_content_b64)
    elif payload.raw_content_text:
        raw_bytes = payload.raw_content_text.encode("utf-8")
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either raw_content_b64 or raw_content_text must be provided",
        )

    computed_hash = hash_asset_bytes(raw_bytes)

    # 2. Check hash match
    if computed_hash != cert.asset_hash:
        return {
            "verified": False,
            "reason_code": "HASH_MISMATCH",
            "computed_hash": computed_hash,
            "certificate_hash": cert.asset_hash,
            "message": "Computed asset hash does not match hash bound in certificate",
        }

    # 3. Verify RSA-PSS signature
    is_valid_sig = _GLOBAL_SIGNER.verify_certificate(cert)
    if not is_valid_sig:
        return {
            "verified": False,
            "reason_code": "SIGNATURE_INVALID",
            "message": "Cryptographic RSA-PSS signature is invalid or tampered",
        }

    return {
        "verified": True,
        "reason_code": "SIGNATURE_VALID",
        "asset_id": cert.asset_id,
        "asset_hash": cert.asset_hash,
        "certificate_id": str(cert.certificate_id),
        "issued_at": cert.issued_at.isoformat(),
        "message": "Certificate signature and asset hash are mathematically verified",
    }
