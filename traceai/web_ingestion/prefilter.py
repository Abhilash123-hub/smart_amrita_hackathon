"""Compliance Pre-Filter (A2): Pre-fetch legal and robot checks before asset download."""

import logging
import re
from typing import Optional
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

from traceai.web_ingestion.models import PreFilterResult

logger = logging.getLogger(__name__)


class CompliancePreFilter:
    """Pre-fetch compliance validator for robots.txt, ai.txt, and TDMRep reservation."""

    def __init__(self, user_agent: str = "TraceAI-Bot/0.1"):
        self.user_agent = user_agent
        self._robots_cache: dict[str, Optional[RobotFileParser]] = {}
        self._ai_txt_cache: dict[str, Optional[dict]] = {}

    async def evaluate_url(
        self,
        target_url: str,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> PreFilterResult:
        """Run pre-fetch compliance checks before any payload bytes are downloaded."""
        parsed = urlparse(target_url)
        domain = parsed.netloc
        scheme = parsed.scheme or "http"
        base_origin = f"{scheme}://{domain}"

        client = http_client or httpx.AsyncClient(timeout=10.0, follow_redirects=True)
        should_close = http_client is None

        try:
            # 1. Check robots.txt (Disallow & Crawl-delay)
            robot_parser = await self._get_robots_parser(base_origin, client)
            if robot_parser:
                can_fetch = robot_parser.can_fetch(self.user_agent, target_url)
                if not can_fetch:
                    logger.warning("Crawl disallowed by robots.txt: %s", target_url)
                    return PreFilterResult(
                        allowed=False,
                        tdm_opted_out=False,
                        skip_reason="Blocked by robots.txt Disallow rule",
                    )

            # 2. Check ai.txt for AI/ML specific training restrictions
            ai_rules = await self._get_ai_txt(base_origin, client)
            if ai_rules:
                if ai_rules.get("disallow_all") or target_url in ai_rules.get("disallowed_paths", []):
                    logger.warning("Ingestion disallowed by ai.txt: %s", target_url)
                    return PreFilterResult(
                        allowed=False,
                        tdm_opted_out=True,
                        skip_reason="Blocked by domain ai.txt restrictions",
                    )

            # 3. Perform a lightweight HTTP HEAD request to inspect TDMRep headers & licenses
            head_res = None
            try:
                head_res = await client.head(target_url, headers={"User-Agent": self.user_agent})
            except Exception:
                pass

            license_hint = None
            tdm_opted_out = False

            if head_res:
                # Check HTTP tdm-reservation header (TDMRep protocol / EU DSM Art 4)
                tdm_header = head_res.headers.get("tdm-reservation")
                if tdm_header and tdm_header.strip() in {"1", "true", "yes"}:
                    logger.warning("TDM reservation asserted in HTTP header: %s", target_url)
                    return PreFilterResult(
                        allowed=False,
                        tdm_opted_out=True,
                        skip_reason="TDM reservation asserted (HTTP header tdm-reservation: 1)",
                    )

                # Capture license header if present
                license_hint = head_res.headers.get("license") or head_res.headers.get("x-license")

            # 4. If HTML page, peek initial metadata headers without fetching full body
            # Acceptance criteria: capture stated license (<meta name="license">, CC badge)
            if head_res and "text/html" in head_res.headers.get("content-type", ""):
                try:
                    # Stream only first 4KB to inspect HTML head metadata
                    async with client.stream("GET", target_url, headers={"User-Agent": self.user_agent, "Range": "bytes=0-4096"}) as r:
                        content_chunk = (await r.aread()).decode("utf-8", errors="ignore")

                    # Check <meta name="tdm-reservation" content="1">
                    if re.search(r'<meta[^>]+name=["\']tdm-reservation["\'][^>]+content=["\'](1|true)["\']', content_chunk, re.IGNORECASE):
                        logger.warning("TDM reservation asserted in HTML meta: %s", target_url)
                        return PreFilterResult(
                            allowed=False,
                            tdm_opted_out=True,
                            skip_reason="TDM reservation asserted in <meta name='tdm-reservation'>",
                        )

                    # Check <meta name="license" content="...">
                    meta_lic = re.search(r'<meta[^>]+name=["\']license["\'][^>]+content=["\']([^"\']+)["\']', content_chunk, re.IGNORECASE)
                    if meta_lic:
                        license_hint = meta_lic.group(1)
                    elif "creativecommons.org" in content_chunk:
                        license_hint = "Creative Commons"
                except Exception as e:
                    logger.debug("HTML meta inspection error for %s: %s", target_url, e)

            return PreFilterResult(
                allowed=True,
                tdm_opted_out=tdm_opted_out,
                license_hint=license_hint,
                skip_reason=None,
            )

        finally:
            if should_close:
                await client.aclose()

    async def _get_robots_parser(self, base_origin: str, client: httpx.AsyncClient) -> Optional[RobotFileParser]:
        if base_origin in self._robots_cache:
            return self._robots_cache[base_origin]

        robots_url = f"{base_origin}/robots.txt"
        parser = RobotFileParser()
        try:
            res = await client.get(robots_url)
            if res.status_code == 200:
                parser.parse(res.text.splitlines())
                self._robots_cache[base_origin] = parser
                return parser
        except Exception:
            pass

        self._robots_cache[base_origin] = None
        return None

    async def _get_ai_txt(self, base_origin: str, client: httpx.AsyncClient) -> Optional[dict]:
        if base_origin in self._ai_txt_cache:
            return self._ai_txt_cache[base_origin]

        ai_url = f"{base_origin}/ai.txt"
        try:
            res = await client.get(ai_url)
            if res.status_code == 200:
                rules = {"disallow_all": False, "disallowed_paths": []}
                for line in res.text.splitlines():
                    line = line.strip()
                    if line.startswith("User-agent: *") or f"User-agent: {self.user_agent}" in line:
                        pass
                    if line.startswith("Disallow: /"):
                        rules["disallow_all"] = True
                self._ai_txt_cache[base_origin] = rules
                return rules
        except Exception:
            pass

        self._ai_txt_cache[base_origin] = None
        return None
