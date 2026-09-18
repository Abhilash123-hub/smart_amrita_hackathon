import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException

from backend.models.schemas import AnalyzeResponse, ThreatDiagnosis
from backend.services.sniffer import detect_mime_type
from backend.services.ai_service import run_ai_analysis
from backend.services.crypto_service import issue_clearance_certificate, generate_prov_o
from backend.services.db_service import log_scan_result
from backend.routes.certificate import CERTIFICATE_REGISTRY

router = APIRouter(prefix="/api/v1", tags=["Analysis"])


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_file(file: UploadFile = File(...)):
    """
    Core Ingestion Gateway Endpoint:
    1. Reads raw asset bytes and executes anti-spoofing byte sniffing.
    2. Runs AI multimodal threat detection (Text or Image track).
    3. Issues RSASSA-PSS clearance cert & W3C PROV-O graph (if PASSED)
       or returns threat diagnosis diagnostics (if BLOCKED).
    4. Persists the transaction audit record to Supabase.
    """
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Unique gateway scan identifier
    scan_id = f"trc_{uuid.uuid4().hex[:8]}"

    # 1. Anti-Spoofing binary inspection
    detected_mime = detect_mime_type(content)

    # 2. Invoke AI engine contract (or mock fallback)
    ai_result = run_ai_analysis(content, file.filename, detected_mime)

    # 3. Process outcome
    if ai_result["verdict"] == "PASSED":
        certificate = issue_clearance_certificate(scan_id, content)
        prov_o = generate_prov_o()
        threat_diagnosis = None

        # Cache in certificate registry for retrieval / verify endpoints
        CERTIFICATE_REGISTRY[scan_id] = {
            "certificate": certificate,
            "prov_o": prov_o
        }
    else:
        certificate = None
        prov_o = None
        threat_diagnosis = ThreatDiagnosis(
            matched_source=ai_result.get("matched_source"),
            similarity_score=ai_result.get("similarity_score", 0.0),
            trigger_stage=ai_result.get("stage_triggered"),
            matched_excerpt=ai_result.get("matched_excerpt"),
            reasons=ai_result.get("reasons", [])
        )

    # 4. Asynchronously log scan result to Supabase
    log_scan_result(
        scan_id=scan_id,
        filename=file.filename,
        detected_mime=detected_mime,
        status=ai_result["verdict"],
        risk_level=ai_result["risk_level"],
        similarity_score=ai_result["similarity_score"],
        certificate_id=certificate.certificate_id if certificate else None,
        threat_diagnosis=threat_diagnosis.model_dump() if threat_diagnosis else None
    )

    # 5. Return standardized payload to Frontend
    return AnalyzeResponse(
        scan_id=scan_id,
        filename=file.filename,
        detected_mime=detected_mime,
        status=ai_result["verdict"],
        risk_level=ai_result["risk_level"],
        similarity_score=ai_result["similarity_score"],
        certificate=certificate,
        prov_o=prov_o,
        threat_diagnosis=threat_diagnosis
    )