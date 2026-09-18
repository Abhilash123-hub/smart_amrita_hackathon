import os
from datetime import datetime, timezone
from fastapi import APIRouter

router = APIRouter(tags=["Health"])

@router.get("/health")
async def health_check():
    mock_mode = os.getenv("TRACEAI_MOCK_AI", "true").lower() == "true"
    return {
        "status": "healthy",
        "service": "TraceAI Multimodal Ingestion Gateway",
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "subsystems": {
            "mock_ai": mock_mode,
            "supported_tracks": ["TEXT", "IMAGE"],
            "anti_spoofing": "active",
            "crypto_signing": "active"
        }
    }