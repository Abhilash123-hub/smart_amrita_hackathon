import hashlib
import base64
from datetime import datetime, timezone
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes
from backend.models.schemas import ClearanceCertificate

# Ephemeral key pair for local Gateway execution
PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PUBLIC_KEY = PRIVATE_KEY.public_key()

def get_asset_sha256(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()

def issue_clearance_certificate(scan_id: str, file_bytes: bytes) -> ClearanceCertificate:
    asset_hash = get_asset_sha256(file_bytes)
    now_iso = datetime.now(timezone.utc).isoformat()

    payload = f"{scan_id}:{asset_hash}:{now_iso}".encode('utf-8')
    signature = PRIVATE_KEY.sign(
        payload,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )

    return ClearanceCertificate(
        certificate_id=scan_id,
        asset_hash=f"sha256:{asset_hash}",
        algorithm="RSASSA-PSS-SHA256",
        signature_b64=base64.b64encode(signature).decode('utf-8'),
        key_fingerprint=f"sha256:{hashlib.sha256(str(PUBLIC_KEY).encode()).hexdigest()[:16]}",
        issued_at=now_iso
    )

def generate_prov_o(scan_id: str, asset_hash: str) -> dict:
    now_iso = datetime.now(timezone.utc).isoformat()
    return {
        "@context": "http://www.w3.org/ns/prov#",
        "@id": f"urn:traceai:entity:{asset_hash[:16]}",
        "@type": "prov:Entity",
        "prov:wasGeneratedBy": {
            "@type": "prov:Activity",
            "prov:name": "TraceAI Ingestion Scan",
            "prov:identifier": scan_id
        },
        "prov:wasAssociatedWith": {
            "@type": "prov:Agent",
            "prov:name": "TraceAI Multimodal Gateway v0.1.0"
        },
        "prov:endedAtTime": now_iso
    }