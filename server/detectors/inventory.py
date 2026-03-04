"""Inventory page discovery and schema analysis."""

import logging
import re

from server.data.url_patterns import (
    INVENTORY_LIST_PATTERNS,
    INVENTORY_URL_PATTERNS,
    NON_VDP_EXCLUSION_PATTERNS,
    PROVIDER_INVENTORY_PATTERNS,
    VDP_URL_PATTERNS,
)
from server.detectors.base import BaseDetector
from server.detectors.schema_parser import SchemaParser
from server.models.schemas import InventoryInfo

logger = logging.getLogger(__name__)

VIN_PATTERN = re.compile(r"[A-HJ-NPR-Z0-9]{17}", re.IGNORECASE)
DEALER_COM_T3_VDP = re.compile(
    r"/(?:new|used)/[A-Za-z-]+/\d{4}-[A-Za-z]+-.*-[a-f0-9]{20,}\.htm", re.IGNORECASE
)


class InventoryDetector(BaseDetector):
    """Find inventory pages and analyze their structured data."""

    async def check(self, domain: str, website_provider: str | None = None) -> InventoryInfo:
        """Find and analyze inventory page."""
        info = InventoryInfo()

        # Find inventory page
        inv_url = await self._find_inventory_page(domain, website_provider)
        if not inv_url:
            return info

        info.found = True
        info.url = inv_url

        # Fetch and analyze
        content = await self.fetch_page(inv_url)
        if not content:
            info.issues.append("Inventory page found but could not be fetched")
            return info

        # Check for CloudFlare challenge
        from server.detectors.blocking import BlockingDetector

        bd = BlockingDetector(self.client, self.page_cache)
        if bd.is_cloudflare_challenge(content):
            info.issues.append("Inventory page behind CloudFlare challenge")
            return info

        # Parse schemas
        parser = SchemaParser(self.client, self.page_cache)
        schema_result = parser.parse_content(content)
        if schema_result.get("schema_details"):
            for detail in schema_result["schema_details"]:
                from server.models.schemas import SchemaItem

                info.schemas.append(
                    SchemaItem(
                        schema_type=detail["type"],
                        properties_found=detail["properties_found"],
                        properties_missing=detail["properties_missing"],
                        completeness=detail["completeness_score"],
                    )
                )

        # Count vehicles
        info.vehicle_count = self._count_vehicles(content, inv_url, schema_result)

        return info

    async def _find_inventory_page(
        self, domain: str, website_provider: str | None = None
    ) -> str | None:
        """Discover inventory page URL."""
        # Build pattern list (provider-specific first)
        patterns = []
        if website_provider and website_provider in PROVIDER_INVENTORY_PATTERNS:
            patterns.extend(PROVIDER_INVENTORY_PATTERNS[website_provider])

        patterns.extend(INVENTORY_URL_PATTERNS)
        # Deduplicate while preserving order
        seen = set()
        unique_patterns = []
        for p in patterns:
            if p not in seen:
                seen.add(p)
                unique_patterns.append(p)

        # Try each pattern
        base_url = self.make_url(domain)
        for pattern in unique_patterns:
            if self._check_timeout():
                break

            url = f"{base_url}{pattern}"
            resp = await self.fetch_response(url, timeout=8.0)
            if resp and resp.status_code == 200:
                # Make sure it didn't redirect back to homepage
                final_url = str(resp.url)
                if final_url.rstrip("/") != base_url.rstrip("/"):
                    return final_url

        # Fallback: check nav links on homepage
        homepage = await self.fetch_page(base_url)
        if homepage:
            inv_url = self._find_inventory_in_nav(homepage, base_url)
            if inv_url:
                return inv_url

        return None

    def _find_inventory_in_nav(self, html: str, base_url: str) -> str | None:
        """Search homepage navigation for inventory links."""
        soup = self.parse_html(html)

        # Check nav and header areas
        nav_areas = soup.find_all(["nav", "header"])
        for area in nav_areas:
            links = area.find_all("a", href=True)
            for link in links:
                href = link["href"].lower()
                text = link.get_text(strip=True).lower()

                # Check URL patterns
                if any(p.lower() in href for p in INVENTORY_LIST_PATTERNS):
                    return self.normalize_url(base_url, link["href"])

                # Check link text
                inv_words = ["inventory", "new vehicles", "used vehicles", "browse", "shop"]
                if any(w in text for w in inv_words):
                    return self.normalize_url(base_url, link["href"])

        return None

    def _count_vehicles(self, html: str, base_url: str, schema_result: dict) -> int:
        """Count vehicles on inventory page."""
        from server.data.bot_user_agents import VEHICLE_SCHEMA_TYPES

        # Try JSON-LD count first
        jsonld_count = 0
        for detail in schema_result.get("schema_details", []):
            schema_type = detail.get("type", "")
            if schema_type in VEHICLE_SCHEMA_TYPES or schema_type == "Offer":
                jsonld_count += 1
            elif schema_type == "ItemList":
                raw = detail.get("raw_data", {})
                items = raw.get("itemListElement", [])
                jsonld_count += len(items)

        if jsonld_count > 0:
            return jsonld_count

        # Fallback: count VDP-like links
        return self._count_vehicle_links(html, base_url)

    def _count_vehicle_links(self, html: str, base_url: str) -> int:
        """Count unique vehicle detail page links."""
        soup = self.parse_html(html)
        links = soup.find_all("a", href=True)
        vehicle_urls: set[str] = set()

        for link in links:
            href = link["href"].lower()
            full_url = self.normalize_url(base_url, href)

            # Skip non-VDP URLs
            if any(exc in href for exc in NON_VDP_EXCLUSION_PATTERNS):
                continue

            # Check VDP patterns
            is_vdp = (
                any(p.lower() in href for p in VDP_URL_PATTERNS)
                or VIN_PATTERN.search(href)
                or DEALER_COM_T3_VDP.search(href)
                or re.search(r"/\d{4}-[a-z]+-[a-z]+", href)
            )
            if is_vdp:
                vehicle_urls.add(full_url)

        return len(vehicle_urls)
