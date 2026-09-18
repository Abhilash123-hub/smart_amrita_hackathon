from __future__ import annotations

"""Scheduling Layer (A7): Continuous polling & resumable batch backfills with checkpointing."""

import asyncio
import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from traceai.web_ingestion.fetcher import IngestionFetcher
from traceai.web_ingestion.models import CrawlCheckpoint, SourceRegistryEntry
from traceai.web_ingestion.queue import IngestionQueue
from traceai.web_ingestion.registry import SourceRegistry

logger = logging.getLogger(__name__)


class CrawlScheduler:
    """Orchestrates continuous cron-style polling and checkpointed resumable backfills."""

    def __init__(
        self,
        registry: SourceRegistry,
        fetcher: IngestionFetcher,
        queue: IngestionQueue,
        db_path: Optional[Path | str] = None,
    ):
        self.registry = registry
        self.fetcher = fetcher
        self.queue = queue
        self._running = False
        self._poll_task: Optional[asyncio.Task] = None

        if db_path is None:
            data_dir = Path("./data").resolve()
            data_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = data_dir / "traceai_checkpoints.db"
        else:
            self.db_path = Path(db_path).resolve()
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_db()

    def _init_db(self):
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS checkpoints (
                    job_id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    crawled_urls TEXT NOT NULL,
                    cursor TEXT,
                    status TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def save_checkpoint(self, checkpoint: CrawlCheckpoint):
        """Persist crawl state to SQLite for resumability."""
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO checkpoints
                (job_id, source_id, crawled_urls, cursor, status, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    checkpoint.job_id,
                    checkpoint.source_id,
                    json.dumps(checkpoint.crawled_urls),
                    checkpoint.cursor,
                    checkpoint.status,
                    now,
                ),
            )
            conn.commit()

    def get_checkpoint(self, job_id: str) -> Optional[CrawlCheckpoint]:
        """Load checkpoint to resume interrupted crawl."""
        with sqlite3.connect(str(self.db_path)) as conn:
            cur = conn.execute("SELECT * FROM checkpoints WHERE job_id = ?", (job_id,))
            row = cur.fetchone()
            if not row:
                return None
            return CrawlCheckpoint(
                job_id=row[0],
                source_id=row[1],
                crawled_urls=json.loads(row[2]),
                cursor=row[3],
                status=row[4],
                updated_at=row[5],
            )

    async def execute_backfill(
        self,
        source: SourceRegistryEntry,
        target_urls: list[str],
        job_id: Optional[str] = None,
        delay_seconds: float = 0.2,
    ) -> CrawlCheckpoint:
        """Execute a resumable, throttled batch backfill job (A7 acceptance criteria)."""
        checkpoint = None
        if job_id:
            checkpoint = self.get_checkpoint(job_id)

        if not checkpoint:
            checkpoint = CrawlCheckpoint(
                job_id=job_id or str(len(target_urls)) + "_" + source.source_id,
                source_id=source.source_id,
                crawled_urls=[],
                status="IN_PROGRESS",
            )

        completed_set = set(checkpoint.crawled_urls)
        logger.info("Executing backfill job %s (Already crawled: %d/%d)", checkpoint.job_id, len(completed_set), len(target_urls))

        for url in target_urls:
            # Checkpoint check: skip already crawled URLs on resume
            if url in completed_set:
                continue

            # Fetch respecting rate limits and compliance
            fetch_res = await self.fetcher.fetch_url(url, source=source)
            if fetch_res.asset:
                # Enqueue for fingerprinting
                await self.queue.enqueue(fetch_res.asset)

            checkpoint.crawled_urls.append(url)
            checkpoint.cursor = url
            # Save checkpoint after each URL fetch
            self.save_checkpoint(checkpoint)

            if delay_seconds > 0:
                await asyncio.sleep(delay_seconds)

        checkpoint.status = "COMPLETED"
        self.save_checkpoint(checkpoint)
        self.registry.update_last_crawled(source.source_id, datetime.now(timezone.utc).isoformat())
        return checkpoint

    async def poll_due_sources_once(self) -> int:
        """Continuous mode: check and poll active sources due for crawl."""
        due_sources = self.registry.get_sources_due_for_crawl()
        for src in due_sources:
            logger.info("Polling due source: %s (%s)", src.source_id, src.url_pattern)
            # In a real environment, discover links; here fetch the seed URL
            res = await self.fetcher.fetch_url(src.url_pattern, source=src)
            if res.asset:
                await self.queue.enqueue(res.asset)
            self.registry.update_last_crawled(src.source_id, datetime.now(timezone.utc).isoformat())
        return len(due_sources)
