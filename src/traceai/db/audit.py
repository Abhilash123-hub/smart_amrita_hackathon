"""Append-Only Audit Log Persistence Repository (Task Card T2.3)."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import UUID, uuid4

from src.traceai.core.models import ScanResult, Verdict


class AuditLogStore:
    """Append-only audit log persistence layer (PostgreSQL / SQLite fallback).
    
    Strictly forbids UPDATE, DELETE, and TRUNCATE actions; corrections must be compensating events.
    """

    def __init__(self, db_path: Optional[Path | str] = None):
        self.db_path = str(db_path or "./data/audit_log.db")
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL,
                    batch_id TEXT NOT NULL,
                    asset_id TEXT NOT NULL,
                    asset_hash TEXT NOT NULL,
                    track TEXT NOT NULL,
                    verdict TEXT NOT NULL,
                    score REAL NOT NULL,
                    certificate_id TEXT,
                    evidence_uri TEXT,
                    raw_payload TEXT NOT NULL,
                    recorded_at TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_batch ON audit_events (batch_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_hash ON audit_events (asset_hash)")
            conn.commit()

    def record_scan_result(
        self,
        batch_id: str,
        result: ScanResult,
        certificate_id: Optional[UUID] = None,
    ) -> str:
        """Insert an immutable scan event into the audit log."""
        event_id = str(uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()
        payload_json = result.model_dump_json()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO audit_events (
                    event_id, batch_id, asset_id, asset_hash, track, verdict, score,
                    certificate_id, evidence_uri, raw_payload, recorded_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    batch_id,
                    result.asset_id,
                    result.asset_hash,
                    result.track.value if hasattr(result.track, "value") else str(result.track),
                    result.verdict.value if hasattr(result.verdict, "value") else str(result.verdict),
                    result.score,
                    str(certificate_id) if certificate_id else None,
                    result.evidence_uri,
                    payload_json,
                    now_iso,
                ),
            )
            conn.commit()
        return event_id

    def query_by_batch(self, batch_id: str) -> list[dict[str, Any]]:
        """Query audit log by batch ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM audit_events WHERE batch_id = ? ORDER BY id ASC",
                (batch_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def query_by_asset_hash(self, asset_hash: str) -> list[dict[str, Any]]:
        """Query audit log by asset SHA-256 hash."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM audit_events WHERE asset_hash = ? ORDER BY id DESC",
                (asset_hash,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def delete(self, *args, **kwargs):
        """Disallowed: Audit log is strictly append-only."""
        raise PermissionError("Audit log is append-only: DELETE operations are strictly prohibited.")

    def update(self, *args, **kwargs):
        """Disallowed: Audit log is strictly append-only."""
        raise PermissionError("Audit log is append-only: UPDATE operations are strictly prohibited.")
