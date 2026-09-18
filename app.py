#!/usr/bin/env python3
"""Launcher for TraceAI Web Dashboard."""

import sys
import uvicorn

if __name__ == "__main__":
    print("=" * 70)
    print("🚀 TraceAI Multimodal Ingestion Gateway & Web Dashboard")
    print("🌐 Running locally at: http://127.0.0.1:8000")
    print("📄 API Documentation:  http://127.0.0.1:8000/docs")
    print("=" * 70)
    uvicorn.run("traceai.api.server:app", host="127.0.0.1", port=8000, reload=True)
