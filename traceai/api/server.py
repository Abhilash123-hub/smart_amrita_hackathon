"""FastAPI REST API Application for TraceAI Gateway."""

import shutil
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from traceai.config import DEFAULT_CONFIG
from traceai.crypto.signer import CryptoSigner
from traceai.gateway import IngestionGateway
from traceai.mock.generator import generate_mock_corpus

app = FastAPI(
    title="TraceAI Ingestion Gateway",
    description="Multimodal Ingestion Gateway for ML Data Governance & Cryptographic Clearance",
    version="0.1.0",
)

# Enable CORS for local web interactions
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global in-memory signer and gateway
signer = CryptoSigner.generate(key_size=DEFAULT_CONFIG.rsa_key_bits)
gateway = IngestionGateway(config=DEFAULT_CONFIG, signer=signer)

# Path to static frontend files
STATIC_DIR = Path(__file__).parent.parent / "web" / "static"


class VerificationRequest(BaseModel):
    asset_hash: str
    signature: str
    public_key_pem: Optional[str] = None


@app.get("/api/info")
async def get_gateway_info():
    """Retrieve operational metadata and cryptographic public key fingerprint."""
    return {
        "gateway_version": "0.1.0",
        "status": "ACTIVE",
        "public_key_fingerprint": signer.key_fingerprint,
        "public_key_pem": signer.public_key_pem,
        "thresholds": {
            "text_cross_encoder": DEFAULT_CONFIG.text_cross_encoder_threshold,
            "image_clip_cosine": DEFAULT_CONFIG.image_clip_cosine_threshold,
            "image_phash_hamming": DEFAULT_CONFIG.image_phash_hamming_threshold,
        },
        "supported_modalities": ["TEXT", "IMAGE"],
    }


@app.post("/api/scan")
async def scan_assets(
    files: list[UploadFile] = File(...),
    use_mock_index: bool = Form(default=True),
    custom_index_dir: Optional[str] = Form(default=None),
):
    """Scan and clear uploaded multimodal assets."""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided for scan.")

    # Determine index directory
    index_path = None
    if custom_index_dir and Path(custom_index_dir).exists():
        index_path = Path(custom_index_dir)
    elif use_mock_index:
        mock_dir = Path("./mock_data").resolve()
        if not (mock_dir / "copyright_index").exists():
            generate_mock_corpus(mock_dir)
        index_path = mock_dir / "copyright_index"

    # Save uploaded files to a temporary staging folder
    with tempfile.TemporaryDirectory() as temp_dir:
        staging_dir = Path(temp_dir)
        for upload in files:
            file_path = staging_dir / upload.filename
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(upload.file, buffer)

        # Run gateway scan
        report = await gateway.scan(input_path=staging_dir, index_dir=index_path)
        return report.to_output_payload(minimal=False)


@app.post("/api/verify")
async def verify_certificate(payload: VerificationRequest):
    """Verify an RSA-PSS cryptographic signature against the public key."""
    if payload.public_key_pem:
        try:
            verifier_signer = CryptoSigner.load_from_files()
            # If custom key string is provided, could load here
            is_valid = signer.verify_signature(payload.asset_hash, payload.signature)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid public key: {e}")
    else:
        is_valid = signer.verify_signature(payload.asset_hash, payload.signature)

    return {
        "valid": is_valid,
        "asset_hash": payload.asset_hash,
        "key_fingerprint": signer.key_fingerprint,
        "message": "Signature verified successfully" if is_valid else "Signature verification failed: tampered or invalid signature",
    }


@app.post("/api/mock/init")
async def init_mock_data():
    """Ensure mock copyright corpus and dirty datasets are generated."""
    mock_dir = Path("./mock_data").resolve()
    stats = generate_mock_corpus(mock_dir)
    return {
        "message": "Mock dataset generated successfully",
        "stats": stats,
    }


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


# Serve frontend static files
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def serve_index():
    """Serve the interactive web platform UI."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return JSONResponse({
        "message": "TraceAI API is active. Web frontend is being initialized.",
        "api_docs": "/docs",
    })
