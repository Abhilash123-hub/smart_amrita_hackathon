"""Automated Web Ingestion Layer for TraceAI (A1-A7)."""

from traceai.web_ingestion.dedup import ChangeAwareDedup
from traceai.web_ingestion.fetcher import FetchResult, IngestionFetcher
from traceai.web_ingestion.models import CrawlCheckpoint, PreFilterResult, SourceRegistryEntry, SourceType, TrustTier
from traceai.web_ingestion.prefilter import CompliancePreFilter
from traceai.web_ingestion.queue import IngestionQueue, QueueItem, QueueMetrics
from traceai.web_ingestion.registry import SourceRegistry
from traceai.web_ingestion.scheduler import CrawlScheduler

__all__ = [
    "TrustTier",
    "SourceType",
    "SourceRegistryEntry",
    "PreFilterResult",
    "CrawlCheckpoint",
    "SourceRegistry",
    "CompliancePreFilter",
    "IngestionFetcher",
    "FetchResult",
    "ChangeAwareDedup",
    "IngestionQueue",
    "QueueItem",
    "QueueMetrics",
    "CrawlScheduler",
]
