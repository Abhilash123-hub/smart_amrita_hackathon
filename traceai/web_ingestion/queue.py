"""Queue-Based Handoff (A6): Decoupled ingestion queue with backpressure, retries, and DLQ."""

import asyncio
import logging
import time
from typing import Any, Callable, Optional
from uuid import uuid4
from pydantic import BaseModel, Field

from traceai.schemas.asset import AssetInput

logger = logging.getLogger(__name__)


class QueueItem(BaseModel):
    item_id: str = Field(default_factory=lambda: str(uuid4()))
    asset: AssetInput
    priority: int = 10  # Lower number = higher priority
    retry_count: int = 0
    max_retries: int = 3
    enqueued_at: float = Field(default_factory=time.time)
    error_log: list[str] = Field(default_factory=list)


class QueueMetrics(BaseModel):
    queue_depth: int
    dlq_depth: int
    total_enqueued: int
    total_processed: int
    backpressure_active: bool


class IngestionQueue:
    """Async Priority Ingestion Queue with backpressure and dead-letter queue (DLQ)."""

    def __init__(self, max_depth: int = 1000):
        self.max_depth = max_depth
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._dlq: list[QueueItem] = []
        self._total_enqueued = 0
        self._total_processed = 0
        self._counter = 0
        self._running = False
        self._worker_tasks: list[asyncio.Task] = []

    @property
    def depth(self) -> int:
        return self._queue.qsize()

    @property
    def dlq_depth(self) -> int:
        return len(self._dlq)

    @property
    def is_backpressure_active(self) -> bool:
        return self.depth >= self.max_depth

    async def enqueue(self, asset: AssetInput, priority: int = 10) -> bool:
        """Enqueue an asset. Applies backpressure if queue is saturated."""
        if self.is_backpressure_active:
            # Backpressure activated: wait briefly or warn
            logger.warning("Queue backpressure active (depth %d >= %d). Throttling ingestion.", self.depth, self.max_depth)
            await asyncio.sleep(0.01)

        item = QueueItem(asset=asset, priority=priority)
        self._counter += 1
        # PriorityQueue sorts by tuple (priority, counter, item)
        await self._queue.put((priority, self._counter, item))
        self._total_enqueued += 1
        return True

    async def dequeue(self) -> QueueItem:
        """Retrieve highest priority item."""
        _, _, item = await self._queue.get()
        return item

    def mark_completed(self, item: QueueItem):
        """Mark item successfully processed."""
        self._total_processed += 1
        self._queue.task_done()

    async def handle_failure(self, item: QueueItem, error_message: str):
        """Handle execution failure: retry or route to Dead-Letter Queue (DLQ)."""
        item.retry_count += 1
        item.error_log.append(f"Attempt {item.retry_count}: {error_message}")
        logger.warning("Task %s failed: %s (Retry %d/%d)", item.item_id, error_message, item.retry_count, item.max_retries)

        if item.retry_count <= item.max_retries:
            # Re-enqueue with lower priority
            item.priority += 5
            self._counter += 1
            await self._queue.put((item.priority, self._counter, item))
        else:
            logger.error("Item %s exceeded max retries. Routing to DLQ.", item.item_id)
            self._dlq.append(item)

        self._queue.task_done()

    def get_metrics(self) -> QueueMetrics:
        """Expose queue telemetry for dashboard (B10)."""
        return QueueMetrics(
            queue_depth=self.depth,
            dlq_depth=self.dlq_depth,
            total_enqueued=self._total_enqueued,
            total_processed=self._total_processed,
            backpressure_active=self.is_backpressure_active,
        )

    def get_dlq_items(self) -> list[dict]:
        """List dead-letter queue items for diagnostic review."""
        return [
            {
                "item_id": it.item_id,
                "asset_id": it.asset.asset_id,
                "track": it.asset.track.value,
                "retry_count": it.retry_count,
                "errors": it.error_log,
            }
            for it in self._dlq
        ]
