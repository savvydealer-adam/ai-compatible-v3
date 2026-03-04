"""Base detector with shared async httpx client and page caching."""

import hashlib
import logging
import re
import time
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from server.config import settings

logger = logging.getLogger(__name__)

MAX_CONTENT_SIZE = 500_000
MAX_ANALYSIS_TIME = 90


class BaseDetector:
    """Base class for all detection modules. Shares httpx client and page cache."""

    def __init__(self, client: httpx.AsyncClient, page_cache: dict[str, str]) -> None:
        self.client = client
        self.page_cache = page_cache
        self._analysis_start_time: float | None = None

    def set_start_time(self, t: float) -> None:
        self._analysis_start_time = t

    def _check_timeout(self) -> bool:
        if self._analysis_start_time is None:
            return False
        return (time.time() - self._analysis_start_time) > MAX_ANALYSIS_TIME

    async def fetch_page(self, url: str, *, timeout: float | None = None) -> str | None:
        """Fetch page content with caching."""
        cache_key = hashlib.md5(url.encode()).hexdigest()
        if cache_key in self.page_cache:
            return self.page_cache[cache_key]

        content = await self._fetch_url(url, timeout=timeout)
        if content:
            self.page_cache[cache_key] = content[:MAX_CONTENT_SIZE]
        return content

    async def _fetch_url(
        self, url: str, *, timeout: float | None = None, headers: dict | None = None
    ) -> str | None:
        """Fetch URL content with HTTPS fallback to HTTP."""
        t = timeout or settings.request_timeout
        merged_headers = dict(self._browser_headers())
        if headers:
            merged_headers.update(headers)

        for scheme in ("https", "http"):
            parsed = urlparse(url)
            if parsed.scheme and parsed.scheme != scheme:
                target = url.replace(f"{parsed.scheme}://", f"{scheme}://")
            elif not parsed.scheme:
                target = f"{scheme}://{url}"
            else:
                target = url

            try:
                resp = await self.client.get(
                    target,
                    headers=merged_headers,
                    timeout=t,
                    follow_redirects=True,
                )
                return resp.text
            except (httpx.HTTPError, httpx.TimeoutException):
                continue
        return None

    async def head_request(
        self, url: str, *, timeout: float | None = None, headers: dict | None = None
    ) -> httpx.Response | None:
        """Make a HEAD request (or GET fallback)."""
        t = timeout or settings.request_timeout
        merged_headers = dict(self._browser_headers())
        if headers:
            merged_headers.update(headers)
        try:
            return await self.client.get(
                url, headers=merged_headers, timeout=t, follow_redirects=True
            )
        except (httpx.HTTPError, httpx.TimeoutException):
            return None

    async def fetch_response(
        self, url: str, *, timeout: float | None = None, headers: dict | None = None
    ) -> httpx.Response | None:
        """Fetch full response object."""
        t = timeout or settings.request_timeout
        merged_headers = dict(self._browser_headers())
        if headers:
            merged_headers.update(headers)
        try:
            return await self.client.get(
                url, headers=merged_headers, timeout=t, follow_redirects=True
            )
        except (httpx.HTTPError, httpx.TimeoutException):
            return None

    def parse_html(self, html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "html.parser")

    @staticmethod
    def clean_domain(domain: str) -> str:
        """Clean and normalize domain input."""
        domain = domain.strip().lower()
        domain = re.sub(r"^https?://", "", domain)
        domain = domain.rstrip("/")
        domain = domain.split("?")[0]
        domain = domain.split("#")[0]
        # Remove path if present
        if "/" in domain:
            domain = domain.split("/")[0]
        return domain

    @staticmethod
    def make_url(domain: str, path: str = "") -> str:
        return f"https://{domain}{path}"

    @staticmethod
    def _browser_headers() -> dict[str, str]:
        return {
            "User-Agent": settings.browser_ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
        }

    @staticmethod
    def normalize_url(base: str, path: str) -> str:
        return urljoin(base, path)
