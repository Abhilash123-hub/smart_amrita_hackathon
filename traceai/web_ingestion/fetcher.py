"""Fetcher Layer (A3): Static async HTTP crawler, dynamic JS renderer, and incremental caching."""

import asyncio
import hashlib
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import httpx

from traceai.schemas.asset import AssetInput, sniff_mime_and_track_from_bytes
from traceai.web_ingestion.models import PreFilterResult, SourceRegistryEntry
from traceai.web_ingestion.prefilter import CompliancePreFilter

logger = logging.getLogger(__name__)


class FetchResult:
    def __init__(
        self,
        url: str,
        asset: Optional[AssetInput] = None,
        is_modified: bool = True,
        status_code: int = 200,
        error: Optional[str] = None,
        prefilter_result: Optional[PreFilterResult] = None,
    ):
        self.url = url
        self.asset = asset
        self.is_modified = is_modified
        self.status_code = status_code
        self.error = error
        self.prefilter_result = prefilter_result


class IngestionFetcher:
    """Fetcher layer with per-domain concurrency limits, incremental ETag cache, and conditional JS rendering."""

    def __init__(
        self,
        prefilter: Optional[CompliancePreFilter] = None,
        db_path: Optional[Path | str] = None,
        max_concurrent_per_domain: int = 3,
        user_agent: str = "TraceAI-Bot/0.1",
    ):
        self.prefilter = prefilter or CompliancePreFilter(user_agent=user_agent)
        self.user_agent = user_agent
        self.max_concurrent_per_domain = max_concurrent_per_domain
        self._domain_semaphores: dict[str, asyncio.Semaphore] = {}

        if db_path is None:
            data_dir = Path("./data").resolve()
            data_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = data_dir / "traceai_cache.db"
        else:
            self.db_path = Path(db_path).resolve()
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_db()

    def _init_db(self):
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS url_cache (
                    url TEXT PRIMARY KEY,
                    etag TEXT,
                    last_modified TEXT,
                    sha256_hash TEXT,
                    crawled_at TEXT
                )
                """
            )
            conn.commit()

    def _get_semaphore(self, domain: str) -> asyncio.Semaphore:
        if domain not in self._domain_semaphores:
            self._domain_semaphores[domain] = asyncio.Semaphore(self.max_concurrent_per_domain)
        return self._domain_semaphores[domain]

    def get_cache_headers(self, url: str) -> tuple[Optional[str], Optional[str]]:
        """Retrieve stored ETag and Last-Modified for incremental fetch."""
        with sqlite3.connect(str(self.db_path)) as conn:
            cur = conn.execute("SELECT etag, last_modified FROM url_cache WHERE url = ?", (url,))
            row = cur.fetchone()
            if row:
                return row[0], row[1]
        return None, None

    def update_cache(self, url: str, etag: Optional[str], last_modified: Optional[str], sha256_hash: str):
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO url_cache (url, etag, last_modified, sha256_hash, crawled_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (url, etag, last_modified, sha256_hash, now),
            )
            conn.commit()

    async def fetch_url(
        self,
        target_url: str,
        source: Optional[SourceRegistryEntry] = None,
        staging_dir: Optional[Path] = None,
    ) -> FetchResult:
        """Fetch asset bytes respecting robots.txt/TDM, incremental cache, and conditional JS rendering."""
        # 1. Run compliance pre-filter BEFORE any bytes are downloaded (A2)
        prefilter_decision = await self.prefilter.evaluate_url(target_url)
        if not prefilter_decision.allowed:
            return FetchResult(
                url=target_url,
                is_modified=False,
                status_code=403,
                error=prefilter_decision.skip_reason,
                prefilter_result=prefilter_decision,
            )

        parsed = urlparse(target_url)
        domain = parsed.netloc
        semaphore = self._get_semaphore(domain)

        async with semaphore:
            js_required = source.js_render_required if source else False
            if js_required:
                return await self._dynamic_fetch(target_url, source, prefilter_decision, staging_dir)
            else:
                return await self._static_fetch(target_url, source, prefilter_decision, staging_dir)

    async def _static_fetch(
        self,
        target_url: str,
        source: Optional[SourceRegistryEntry],
        prefilter_decision: PreFilterResult,
        staging_dir: Optional[Path],
    ) -> FetchResult:
        """Standard async HTTP fetch with ETag / Last-Modified caching."""
        etag, last_mod = self.get_cache_headers(target_url)
        headers = {"User-Agent": self.user_agent}
        if etag:
            headers["If-None-Match"] = etag
        if last_mod:
            headers["If-Modified-Since"] = last_mod

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            try:
                res = await client.get(target_url, headers=headers)
                if res.status_code == 304:
                    # Incremental fetch: Unchanged, skip download & fingerprinting (A3 acceptance criteria)
                    return FetchResult(
                        url=target_url,
                        is_modified=False,
                        status_code=304,
                        prefilter_result=prefilter_decision,
                    )

                if res.status_code != 200:
                    return FetchResult(
                        url=target_url,
                        is_modified=False,
                        status_code=res.status_code,
                        error=f"HTTP {res.status_code}",
                        prefilter_result=prefilter_decision,
                    )

                content_bytes = res.content
                return self._create_asset_from_bytes(
                    target_url=target_url,
                    content_bytes=content_bytes,
                    headers=dict(res.headers),
                    source=source,
                    prefilter_decision=prefilter_decision,
                    staging_dir=staging_dir,
                )

            except Exception as e:
                logger.error("Static fetch error for %s: %s", target_url, e)
                return FetchResult(
                    url=target_url,
                    is_modified=False,
                    status_code=500,
                    error=str(e),
                    prefilter_result=prefilter_decision,
                )

    async def _dynamic_fetch(
        self,
        target_url: str,
        source: Optional[SourceRegistryEntry],
        prefilter_decision: PreFilterResult,
        staging_dir: Optional[Path],
    ) -> FetchResult:
        """Headless rendering (Playwright fallback to static if playwright not installed)."""
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page(user_agent=self.user_agent)
                await page.goto(target_url, wait_until="networkidle", timeout=15000)
                rendered_html = await page.content()
                await browser.close()
                content_bytes = rendered_html.encode("utf-8")
                return self._create_asset_from_bytes(
                    target_url=target_url,
                    content_bytes=content_bytes,
                    headers={"content-type": "text/html"},
                    source=source,
                    prefilter_decision=prefilter_decision,
                    staging_dir=staging_dir,
                )
        except ImportError:
            logger.info("Playwright not installed; falling back gracefully to static fetch for %s", target_url)
            return await self._static_fetch(target_url, source, prefilter_decision, staging_dir)
        except Exception as e:
            logger.warning("Dynamic rendering exception on %s: %s", target_url, e)
            return await self._static_fetch(target_url, source, prefilter_decision, staging_dir)

    def _create_asset_from_bytes(
        self,
        target_url: str,
        content_bytes: bytes,
        headers: dict,
        source: Optional[SourceRegistryEntry],
        prefilter_decision: PreFilterResult,
        staging_dir: Optional[Path],
    ) -> FetchResult:
        """Persist downloaded asset, update incremental cache, and construct AssetInput with web metadata (A4)."""
        target_dir = staging_dir or Path("./data/staging").resolve()
        target_dir.mkdir(parents=True, exist_ok=True)

        # Hash and filename
        sha256_hex = hashlib.sha256(content_bytes).hexdigest()
        asset_hash = f"sha256:{sha256_hex}"

        # Determine extension and filename
        filename = f"{sha256_hex[:12]}_{Path(urlparse(target_url).path).name or 'asset'}"
        file_path = target_dir / filename
        file_path.write_bytes(content_bytes)

        # Sniff bytes
        track, mime_type = sniff_mime_and_track_from_bytes(file_path, content_bytes[:4096])

        # Update incremental cache
        self.update_cache(
            url=target_url,
            etag=headers.get("etag"),
            last_modified=headers.get("last-modified"),
            sha256_hash=asset_hash,
        )

        now_iso = datetime.now(timezone.utc).isoformat()
        asset = AssetInput(
            asset_id=filename,
            file_path=file_path,
            track=track,
            mime_type=mime_type,
            size_bytes=len(content_bytes),
            sha256_hash=asset_hash,
            source_url=target_url,
            http_headers=headers,
            source_id=source.source_id if source else None,
            source_trust_tier=source.trust_tier.value if source else None,
            prefilter_decision=prefilter_decision.model_dump(),
            crawl_timestamp=now_iso,
        )

        return FetchResult(
            url=target_url,
            asset=asset,
            is_modified=True,
            status_code=200,
            prefilter_result=prefilter_decision,
        )
