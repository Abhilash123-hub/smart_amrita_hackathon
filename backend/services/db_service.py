from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from backend.database.supabase_client import get_supabase_client

TABLE_NAME = "ingestion_scans"

def log_scan_result(
    scan_id: str,
    filename: str,
    detected_mime: str,
    status: str,
    risk_level: str,
    similarity_score: float,
    certificate_id: Optional[str] = None,
    threat_diagnosis: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    Persists an ingestion scan outcome to Supabase.
    Fails gracefully so API requests succeed even if DB is offline.
    """
    client = get_supabase_client()
    if not client:
        return None

    record = {
        "scan_id": scan_id,
        "filename": filename,
        "detected_mime": detected_mime,
        "status": status,
        "risk_level": risk_level,
        "similarity_score": similarity_score,
        "certificate_id": certificate_id,
        "threat_diagnosis": threat_diagnosis,
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    try:
        response = client.table(TABLE_NAME).insert(record).execute()
        if response.data:
            return response.data[0]
        return record
    except Exception as e:
        print(f"[TraceAI DB Warning] Failed to log scan to Supabase: {e}")
        return None

def get_scan_by_id(scan_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a specific scan by its scan_id."""
    client = get_supabase_client()
    if not client:
        return None

    try:
        response = client.table(TABLE_NAME).select("*").eq("scan_id", scan_id).execute()
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        print(f"[TraceAI DB Warning] Failed to fetch scan {scan_id}: {e}")
        return None

def get_recent_scans(limit: int = 10) -> List[Dict[str, Any]]:
    """Retrieve recent scans for dashboard activity feeds."""
    client = get_supabase_client()
    if not client:
        return []

    try:
        response = (
            client.table(TABLE_NAME)
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data or []
    except Exception as e:
        print(f"[TraceAI DB Warning] Failed to fetch recent scans: {e}")
        return []