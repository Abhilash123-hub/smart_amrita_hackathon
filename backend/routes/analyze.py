import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks

from backend.models.schemas import AnalyzeResponse, ThreatDiagnosis
from backend.services.sniffer import detect_mime_type
from backend.services.ai_service import run_ai_analysis
from backend.services.crypto_service import issue_clearance_certificate, generate_prov_o
from backend.services.db_service import log_scan_result
from backend.routes.certificate import CERTIFICATE_REGISTRY

router = APIRouter(prefix="/api/v1", tags=["Analysis"])


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_file(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Ingests raw file payload, executes byte-level anti-spoofing verification,
    evaluates threat risks via AI pipeline, generates verifiable provenance/certificates,
    and dispatches database audit persistence asynchronously.
    """
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    scan_id = f"trc_{uuid.uuid4().hex[:8]}"

    # 1. Anti-Spoofing binary magic byte check
    detected_mime = detect_mime_type(content)

    # 2. AI Threat Analysis (Model evaluation or mock adapter)
    ai_result = run_ai_analysis(content, file.filename, detected_mime)

    # 3. Handle Passed vs Blocked pipelines
    if ai_result.get("verdict") == "PASSED":
        certificate = issue_clearance_certificate(scan_id, content)
        prov_o = generate_prov_o()
        threat_diagnosis = None

        # Cache in certificate registry for rapid lookups and third-party verification
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

    # 4. Asynchronous non-blocking Supabase persistence
    threat_dict = threat_diagnosis.model_dump() if threat_diagnosis else None
    cert_id = certificate.certificate_id if certificate else None

    background_tasks.add_task(
        log_scan_result,
        scan_id=scan_id,
        filename=file.filename,
        detected_mime=detected_mime,
        status=ai_result["verdict"],
        risk_level=ai_result["risk_level"],
        similarity_score=ai_result["similarity_score"],
        certificate_id=cert_id,
        threat_diagnosis=threat_dict
    )

    # 5. Immediate response dispatch to client
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