"""Source Registry (A1): Persistent registry of ingestion sources with CRUD operations."""

import sqlite3
from pathlib import Path
from typing import Optional

from traceai.web_ingestion.models import SourceRegistryEntry, SourceType, TrustTier


class SourceRegistry:
    """Persistent SQLite-backed registry for ingestion targets and trust tiers."""

    def __init__(self, db_path: Optional[Path | str] = None):
        if db_path is None:
            data_dir = Path("./data").resolve()
            data_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = data_dir / "traceai_registry.db"
        else:
            self.db_path = Path(db_path).resolve()
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sources (
                    source_id TEXT PRIMARY KEY,
                    url_pattern TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    trust_tier TEXT NOT NULL,
                    crawl_frequency TEXT NOT NULL,
                    js_render_required INTEGER NOT NULL,
                    active INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    last_crawled_at TEXT
                )
                """
            )
            conn.commit()

    def create_source(self, entry: SourceRegistryEntry) -> SourceRegistryEntry:
        """Register a new ingestion source."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO sources (
                    source_id, url_pattern, source_type, trust_tier,
                    crawl_frequency, js_render_required, active,
                    created_at, last_crawled_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.source_id,
                    entry.url_pattern,
                    entry.source_type.value,
                    entry.trust_tier.value,
                    entry.crawl_frequency,
                    1 if entry.js_render_required else 0,
                    1 if entry.active else 0,
                    entry.created_at,
                    entry.last_crawled_at,
                ),
            )
            conn.commit()
        return entry

    def get_source(self, source_id: str) -> Optional[SourceRegistryEntry]:
        """Fetch a source by its ID."""
        with self._get_connection() as conn:
            cur = conn.execute("SELECT * FROM sources WHERE source_id = ?", (source_id,))
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_entry(row)

    def list_sources(self, active_only: bool = False) -> list[SourceRegistryEntry]:
        """List registered sources."""
        query = "SELECT * FROM sources"
        params = ()
        if active_only:
            query += " WHERE active = 1"
        query += " ORDER BY created_at DESC"

        with self._get_connection() as conn:
            cur = conn.execute(query, params)
            return [self._row_to_entry(r) for r in cur.fetchall()]

    def get_sources_due_for_crawl(self) -> list[SourceRegistryEntry]:
        """List active sources due for a crawl (acceptance criteria for A1)."""
        # Active sources that either have not been crawled or were crawled earlier
        with self._get_connection() as conn:
            cur = conn.execute(
                """
                SELECT * FROM sources 
                WHERE active = 1 
                ORDER BY (last_crawled_at IS NOT NULL), last_crawled_at ASC
                """
            )
            return [self._row_to_entry(r) for r in cur.fetchall()]

    def update_last_crawled(self, source_id: str, timestamp: str):
        """Update last crawl timestamp for a source."""
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE sources SET last_crawled_at = ? WHERE source_id = ?",
                (timestamp, source_id),
            )
            conn.commit()

    def delete_source(self, source_id: str) -> bool:
        """Delete a source by ID."""
        with self._get_connection() as conn:
            cur = conn.execute("DELETE FROM sources WHERE source_id = ?", (source_id,))
            conn.commit()
            return cur.rowcount > 0

    def _row_to_entry(self, row: sqlite3.Row) -> SourceRegistryEntry:
        return SourceRegistryEntry(
            source_id=row["source_id"],
            url_pattern=row["url_pattern"],
            source_type=SourceType(row["source_type"]),
            trust_tier=TrustTier(row["trust_tier"]),
            crawl_frequency=row["crawl_frequency"],
            js_render_required=bool(row["js_render_required"]),
            active=bool(row["active"]),
            created_at=row["created_at"],
            last_crawled_at=row["last_crawled_at"],
        )
