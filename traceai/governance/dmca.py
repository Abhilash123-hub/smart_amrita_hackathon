from __future__ import annotations

"""DMCA & Takedown Intake with Delta Index Re-evaluation (B6)."""

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from traceai.schemas.asset import AssetInput, TrackType
from traceai.schemas.report import AssetStatus

logger = logging.getLogger(__name__)


class DmcaIndexManager:
    """Manages takedown notices, index versioning, and delta re-evaluations."""

    def __init__(self, db_path: Optional[Path | str] = None, base_index_dir: Optional[Path | str] = None):
        if db_path is None:
            data_dir = Path("./data").resolve()
            data_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = data_dir / "traceai_dmca.db"
        else:
            self.db_path = Path(db_path).resolve()
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.index_dir = Path(base_index_dir or "./mock_data/copyright_index").resolve()
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS takedowns (
                    notice_id TEXT PRIMARY KEY,
                    rightsholder TEXT NOT NULL,
                    work_title TEXT NOT NULL,
                    track TEXT NOT NULL,
                    sample_content TEXT,
                    index_version INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cleared_asset_log (
                    asset_id TEXT PRIMARY KEY,
                    asset_hash TEXT NOT NULL,
                    track TEXT NOT NULL,
                    text_content TEXT,
                    checked_index_version INTEGER NOT NULL,
                    status TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def get_current_index_version(self) -> int:
        """Fetch latest index version."""
        with sqlite3.connect(str(self.db_path)) as conn:
            cur = conn.execute("SELECT MAX(index_version) FROM takedowns")
            row = cur.fetchone()
            return (row[0] or 1)

    def register_cleared_asset(self, asset: AssetInput, status: str = "PASSED"):
        """Log asset cleared under current index version for future delta audits."""
        current_v = self.get_current_index_version()
        text_content = asset.read_text() if asset.track in {TrackType.TEXT, TrackType.CODE} else ""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cleared_asset_log
                (asset_id, asset_hash, track, text_content, checked_index_version, status)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (asset.asset_id, asset.sha256_hash, asset.track.value, text_content, current_v, status),
            )
            conn.commit()

    def submit_takedown(
        self,
        notice_id: str,
        rightsholder: str,
        work_title: str,
        track: str,
        sample_content: str,
    ) -> dict[str, Any]:
        """Intake new copyrighted work from a rightsholder and increment index_version."""
        new_version = self.get_current_index_version() + 1
        now = datetime.now(timezone.utc).isoformat()

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                INSERT INTO takedowns (notice_id, rightsholder, work_title, track, sample_content, index_version, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (notice_id, rightsholder, work_title, track, sample_content, new_version, now),
            )
            conn.commit()

        # Update disk index if directory exists
        if track == "TEXT" and self.index_dir.exists():
            texts_dir = self.index_dir / "texts"
            texts_dir.mkdir(parents=True, exist_ok=True)
            (texts_dir / f"dmca_{notice_id}.txt").write_text(
                f"[{work_title}]\n{sample_content}\nCopyright (c) {rightsholder}", encoding="utf-8"
            )

        return {
            "notice_id": notice_id,
            "rightsholder": rightsholder,
            "work_title": work_title,
            "new_index_version": f"v{new_version}",
            "status": "INDEXED",
        }

    def reevaluate_delta(self, from_version: int, to_version: Optional[int] = None) -> list[dict[str, Any]]:
        """Re-run previously CLEAR assets against ONLY the delta additions (B6 acceptance criteria)."""
        target_v = to_version or self.get_current_index_version()

        # Fetch only delta takedown items between versions
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                "SELECT * FROM takedowns WHERE index_version > ? AND index_version <= ?",
                (from_version, target_v),
            )
            delta_items = [dict(r) for r in cur.fetchall()]

            # Fetch previously cleared assets checked under older index versions
            cur_assets = conn.execute(
                "SELECT * FROM cleared_asset_log WHERE checked_index_version <= ?",
                (from_version,),
            )
            cleared_assets = [dict(r) for r in cur_assets.fetchall()]

        flagged_delta = []
        from difflib import SequenceMatcher

        # Re-evaluate against delta only
        for asset in cleared_assets:
            for delta in delta_items:
                if asset["track"] == delta["track"] and asset["text_content"] and delta["sample_content"]:
                    ratio = SequenceMatcher(
                        None, asset["text_content"].lower(), delta["sample_content"].lower()
                    ).ratio()

                    if ratio >= 0.75:
                        flagged_delta.append({
                            "asset_id": asset["asset_id"],
                            "asset_hash": asset["asset_hash"],
                            "previously_cleared_at_version": f"v{asset['checked_index_version']}",
                            "flagged_at_version": f"v{delta['index_version']}",
                            "matched_delta_source": f"© {delta['work_title']} ({delta['rightsholder']})",
                            "similarity_score": round(ratio, 4),
                            "action_required": "REVOKE_AND_BLOCK",
                        })

        return flagged_delta
