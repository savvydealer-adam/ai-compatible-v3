"""XML/HTML sitemap parsing."""

import logging
import re
from datetime import UTC, datetime, timedelta

from server.data.url_patterns import INVENTORY_LIST_PATTERNS, VDP_URL_PATTERNS
from server.detectors.base import BaseDetector
from server.models.schemas import SitemapInfo

logger = logging.getLogger(__name__)


class SitemapDetector(BaseDetector):
    """Discover and parse XML/HTML sitemaps."""

    async def check(self, domain: str) -> SitemapInfo:
        """Find and analyze sitemap."""
        info = SitemapInfo()

        # Try common sitemap locations
        sitemap_paths = [
            "/sitemap.xml",
            "/sitemap.htm",
            "/sitemap",
            "/sitemap_index.xml",
        ]
        # Also try with www prefix
        domains_to_try = [domain]
        if not domain.startswith("www."):
            domains_to_try.append(f"www.{domain}")

        content = None
        for d in domains_to_try:
            for path in sitemap_paths:
                url = self.make_url(d, path)
                content = await self.fetch_page(url)
                if content and len(content.strip()) > 50:
                    info.found = True
                    info.url = url
                    break
            if info.found:
                break

        # Check robots.txt for Sitemap directive
        if not info.found:
            sitemap_url = await self._get_sitemap_from_robots(domain)
            if sitemap_url:
                content = await self.fetch_page(sitemap_url)
                if content and len(content.strip()) > 50:
                    info.found = True
                    info.url = sitemap_url

        if not info.found or not content:
            return info

        # Parse based on content type
        if (
            "<?xml" in content[:100]
            or "<urlset" in content[:500]
            or "<sitemapindex" in content[:500]
        ):
            self._parse_xml_sitemap(content, info, domain)
        else:
            self._parse_html_sitemap(content, info, domain)

        return info

    async def _get_sitemap_from_robots(self, domain: str) -> str | None:
        """Extract Sitemap URL from robots.txt."""
        content = await self.fetch_page(self.make_url(domain, "/robots.txt"))
        if not content:
            return None

        for line in content.split("\n"):
            line = line.strip()
            if line.lower().startswith("sitemap:"):
                return line.split(":", 1)[1].strip()
        return None

    def _parse_xml_sitemap(self, content: str, info: SitemapInfo, domain: str) -> None:
        """Parse XML sitemap content."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(content, "xml")
        if not soup:
            # Fallback to html.parser
            soup = BeautifulSoup(content, "html.parser")

        # Check if sitemap index
        sitemaps = soup.find_all("sitemap")
        if sitemaps:
            # Sitemap index - look for vehicle/inventory sitemaps
            vehicle_keywords = ["vehicle", "inventory", "vdp", "car", "auto"]
            for sm in sitemaps:
                loc = sm.find("loc")
                if not loc or not loc.string:
                    continue
                sm_url = loc.string.strip()
                lower_url = sm_url.lower()
                if any(kw in lower_url for kw in vehicle_keywords):
                    info.entry_count += 1

            # Also parse main sitemap entries
            self._extract_url_entries(soup, info, domain)
            return

        self._extract_url_entries(soup, info, domain)

    def _extract_url_entries(self, soup, info: SitemapInfo, domain: str) -> None:
        """Extract URL entries from parsed sitemap."""
        urls = soup.find_all("url")
        info.entry_count = len(urls)

        vehicle_count = 0
        now = datetime.now(tz=UTC)
        fresh_threshold = now - timedelta(days=30)

        for url_entry in urls:
            loc = url_entry.find("loc")
            if not loc or not loc.string:
                continue

            url_str = loc.string.strip().lower()

            # Check for vehicle URLs
            if self._is_vehicle_url(url_str):
                vehicle_count += 1

            # Check lastmod
            lastmod = url_entry.find("lastmod")
            if lastmod and lastmod.string:
                try:
                    mod_date = datetime.fromisoformat(lastmod.string.strip().replace("Z", "+00:00"))
                    if mod_date > fresh_threshold:
                        info.has_lastmod = True
                except ValueError:
                    pass

            # Check for images
            if url_entry.find("image:image") or url_entry.find("image"):
                info.has_images = True

        if vehicle_count > 0:
            info.has_lastmod = info.has_lastmod  # Keep existing value

    def _parse_html_sitemap(self, content: str, info: SitemapInfo, domain: str) -> None:
        """Parse HTML sitemap content."""
        soup = self.parse_html(content)
        links = soup.find_all("a", href=True)
        info.entry_count = len(links)

        vehicle_count = 0
        for link in links:
            href = link["href"].lower()
            if self._is_vehicle_url(href):
                vehicle_count += 1

    @staticmethod
    def _is_vehicle_url(url: str) -> bool:
        """Check if URL is a vehicle-related page."""
        url_lower = url.lower()
        vdp_patterns = [p.lower() for p in VDP_URL_PATTERNS]
        inv_patterns = [p.lower() for p in INVENTORY_LIST_PATTERNS]

        if any(p in url_lower for p in vdp_patterns + inv_patterns):
            return True

        # VIN pattern in URL
        vin_pattern = re.compile(r"[A-HJ-NPR-Z0-9]{17}", re.IGNORECASE)
        if vin_pattern.search(url):
            return True

        # Year-make-model pattern
        return bool(re.search(r"/\d{4}-[a-z]+-[a-z]+", url_lower))
