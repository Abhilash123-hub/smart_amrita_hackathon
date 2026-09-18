from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
import base64

from backend.models.schemas import ClearanceCertificate, ProvOGraph
from backend.services.crypto_service import PUBLIC_KEY

router = APIRouter(prefix="/api/v1/certificates", tags=["Certificates"])

# In-memory certificate ledger for MVP / local execution
CERTIFICATE_REGISTRY: Dict[str, Dict[str, Any]] = {}

class CertificateDetailResponse(BaseModel):
    certificate_id: str
    certificate: ClearanceCertificate
    prov_o: ProvOGraph
    verification_status: str

class VerifyCertificateRequest(BaseModel):
    certificate_id: str
    asset_hash: str
    signature_b64: str


@router.get("/{certificate_id}", response_model=CertificateDetailResponse)
async def get_certificate(certificate_id: str):
    """Retrieve an issued clearance certificate and its W3C PROV-O graph."""
    record = CERTIFICATE_REGISTRY.get(certificate_id)
    if not record:
        raise HTTPException(
            status_code=404, 
            detail=f"Certificate '{certificate_id}' not found or asset was blocked."
        )

    return CertificateDetailResponse(
        certificate_id=certificate_id,
        certificate=record["certificate"],
        prov_o=record["prov_o"],
        verification_status="VALID"
    )


@router.post("/verify")
async def verify_certificate(payload: VerifyCertificateRequest):
    """Zero-knowledge verification of the RSASSA-PSS signature against TraceAI's public key."""
    record = CERTIFICATE_REGISTRY.get(payload.certificate_id)
    if not record:
        raise HTTPException(status_code=404, detail="Certificate ID not registered.")

    # Match raw signature payload: scan_id:asset_hash:timestamp
    cert: ClearanceCertificate = record["certificate"]
    expected_message = f"{cert.certificate_id}:{payload.asset_hash.replace('sha256:', '')}:{cert.issued_at}".encode("utf-8")

    try:
        raw_signature = base64.b64decode(payload.signature_b64)
        PUBLIC_KEY.verify(
            raw_signature,
            expected_message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return {
            "valid": True,
            "algorithm": cert.algorithm,
            "key_fingerprint": cert.key_fingerprint,
            "message": "Cryptographic signature matches immutable asset hash."
        }
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Signature verification failed. Asset hash or certificate payload has been tampered with."
        )