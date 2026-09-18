"""Data models for the Automated Web Ingestion Layer (A1-A7)."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4
from pydantic import BaseModel, Field


class TrustTier(str, Enum):
    """Source trust tier determining risk threshold and human review sensitivity."""
    LICENSED_PARTNER = "licensed-partner"
    PUBLIC_WEB_UNKNOWN = "public-web-unknown"
    HIGH_RISK_DOMAIN = "high-risk-domain"


class SourceType(str, Enum):
    """Type of web ingestion target."""
    SITEMAP = "sitemap"
    RSS = "rss"
    API = "api"
    CRAWL = "crawl"


class SourceRegistryEntry(BaseModel):
    """Registered web ingestion source (A1)."""
    source_id: str = Field(default_factory=lambda: str(uuid4())[:8], description="Unique source identifier")
    url_pattern: str = Field(description="Seed URL or URL pattern / domain")
    source_type: SourceType = Field(default=SourceType.CRAWL, description="Ingestion mechanism")
    trust_tier: TrustTier = Field(default=TrustTier.PUBLIC_WEB_UNKNOWN, description="Domain trust classification")
    crawl_frequency: str = Field(default="daily", description="Crawl frequency: hourly, daily, weekly, or cron")
    js_render_required: bool = Field(default=False, description="True if source requires headless browser (Playwright)")
    active: bool = Field(default=True, description="Whether this source is currently scheduled")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_crawled_at: Optional[str] = Field(default=None, description="Timestamp of the most recent crawl")


class PreFilterResult(BaseModel):
    """Compliance pre-fetch check result (A2)."""
    allowed: bool = Field(description="True if crawl is permitted by robots.txt and TDMRep")
    tdm_opted_out: bool = Field(default=False, description="True if TDM reservation is asserted (EU DSM Art 4 / TDMRep)")
    license_hint: Optional[str] = Field(default=None, description="Stated license (e.g. CC-BY, MIT, Proprietary)")
    skip_reason: Optional[str] = Field(default=None, description="Reason if fetch was blocked (e.g. robots.txt Disallow)")
    checked_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CrawlCheckpoint(BaseModel):
    """Resumable crawl job checkpoint state (A7)."""
    job_id: str = Field(default_factory=lambda: str(uuid4()))
    source_id: str
    crawled_urls: list[str] = Field(default_factory=list)
    cursor: Optional[str] = None
    status: str = "IN_PROGRESS"  # IN_PROGRESS, PAUSED, COMPLETED, FAILED
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
