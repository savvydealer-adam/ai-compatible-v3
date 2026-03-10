"""Vehicle detail page discovery and schema analysis."""

import logging
import re

from server.data.url_patterns import (
    GENERIC_VDP_PATTERNS,
    NON_VDP_EXCLUSION_PATTERNS,
    PROVIDER_VDP_PATTERNS,
    VDP_URL_PATTERNS,
)
from server.detectors.base import BaseDetector
from server.detectors.schema_parser import SchemaParser
from server.models.schemas import VdpInfo

logger = logging.getLogger(__name__)

VIN_PATTERN = re.compile(r"[A-HJ-NPR-Z0-9]{17}", re.IGNORECASE)
DEALER_COM_T3_PATTERN = re.compile(
    r"/(?:new|used)/[A-Za-z-]+/\d{4}-[A-Za-z]+-.*-[a-f0-9]{20,}\.htm", re.IGNORECASE
)
PRICE_PATTERN = re.compile(
    r"\$[\d,]+(?:\.\d{2})?|\bprice[:\s]*\$[\d,]+|\bmsrp[:\s]*\$[\d,]+", re.IGNORECASE
)


class VdpDetector(BaseDetector):
    """Find vehicle detail pages and analyze their structured data."""

    async def check(
        self,
        domain: str,
        inventory_url: str | None = None,
        sitemap_vdps: list[str] | None = None,
        website_provider: str | None = None,
    ) -> VdpInfo:
        """Find and analyze vehicle detail page."""
        info = VdpInfo()

        vdp_url = await self._find_vdp(domain, inventory_url, sitemap_vdps, website_provider)
        if not vdp_url:
            return info

        info.found = True
        info.url = vdp_url

        # Fetch and analyze
        content = await self.fetch_page(vdp_url)
        if not content:
            info.issues.append("VDP found but could not be fetched")
            return info

        # Check for CloudFlare
        from server.detectors.blocking import BlockingDetector

        bd = BlockingDetector(self.client, self.page_cache)
        if bd.is_cloudflare_challenge(content):
            info.issues.append("VDP behind CloudFlare challenge")
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

        # If no vehicle schema, try alternative VDPs
        has_vehicle = schema_result.get("has_vehicle_schema", False)
        if not has_vehicle and inventory_url:
            alt = await self._try_alt_vdps(inventory_url, vdp_url, website_provider)
            if alt:
                info.url = alt["url"]
                info.schemas = alt.get("schemas", [])

        return info

    async def _find_vdp(
        self,
        domain: str,
        inventory_url: str | None,
        sitemap_vdps: list[str] | None,
        website_provider: str | None,
    ) -> str | None:
        """Multi-pass VDP discovery."""
        # Try sitemap VDPs first
        if sitemap_vdps:
            for url in sitemap_vdps[:3]:
                resp = await self.fetch_response(url, timeout=8.0)
                if resp and resp.status_code == 200:
                    return str(resp.url)

        # Get VDP patterns for provider
        if website_provider and website_provider in PROVIDER_VDP_PATTERNS:
            patterns = PROVIDER_VDP_PATTERNS[website_provider]
        else:
            patterns = GENERIC_VDP_PATTERNS

        # Search inventory page links
        if inventory_url:
            vdp = await self._search_inventory_links(inventory_url, patterns, website_provider)
            if vdp:
                return vdp

        # Try direct URL patterns
        base_url = self.make_url(domain)
        for pattern in VDP_URL_PATTERNS[:6]:
            if self._check_timeout():
                break
            url = f"{base_url}{pattern}"
            resp = await self.fetch_response(url, timeout=8.0)
            if resp and resp.status_code == 200:
                return str(resp.url)

        return None

    async def _search_inventory_links(
        self, inventory_url: str, patterns: list[str], website_provider: str | None
    ) -> str | None:
        """Search inventory page links for VDP candidates."""
        content = await self.fetch_page(inventory_url)
        if not content:
            return None

        soup = self.parse_html(content)
        links = soup.find_all("a", href=True)
        candidates: list[str] = []

        for link in links:
            href = link["href"]
            href_lower = href.lower()

            # Skip non-VDP URLs
            if any(exc in href_lower for exc in NON_VDP_EXCLUSION_PATTERNS):
                continue

            full_url = self.normalize_url(inventory_url, href)

            # Pass 1: vehicle-info links with VIN (Savvy Dealer)
            if "/vehicle-info/" in href_lower and VIN_PATTERN.search(href):
                return full_url

            # Pass 2: Links with VIN
            if VIN_PATTERN.search(href):
                candidates.append(full_url)
                continue

            # Pass 3: Provider VDP patterns
            if any(p.lower() in href_lower for p in patterns):
                candidates.append(full_url)
                continue

            # Pass 4: -detail.htm links
            if "-detail.htm" in href_lower:
                candidates.append(full_url)
                continue

            # Pass 5: Dealer.com T3 pattern
            if DEALER_COM_T3_PATTERN.search(href):
                candidates.append(full_url)
                continue

            # Pass 6: Year-make-model pattern
            if re.search(r"/\d{4}-[a-z]+-[a-z]+", href_lower):
                candidates.append(full_url)

        # Validate first candidate
        for url in candidates[:5]:
            if self._check_timeout():
                break
            resp = await self.fetch_response(url, timeout=8.0)
            if resp and resp.status_code == 200:
                return str(resp.url)

        return None

    async def _try_alt_vdps(
        self, inventory_url: str, exclude_url: str, website_provider: str | None, max_tries: int = 3
    ) -> dict | None:
        """Try alternative VDP URLs looking for one with vehicle schema."""
        content = await self.fetch_page(inventory_url)
        if not content:
            return None

        soup = self.parse_html(content)
        links = soup.find_all("a", href=True)
        tried = 0

        for link in links:
            if tried >= max_tries or self._check_timeout():
                break

            href = link["href"]
            full_url = self.normalize_url(inventory_url, href)
            if full_url == exclude_url:
                continue

            # Only try links that look like VDPs (have VIN + year-make-model)
            if not (VIN_PATTERN.search(href) and re.search(r"/\d{4}-[a-z]+", href.lower())):
                continue

            tried += 1
            vdp_content = await self.fetch_page(full_url)
            if not vdp_content:
                continue

            parser = SchemaParser(self.client, self.page_cache)
            result = parser.parse_content(vdp_content)
            if result.get("has_vehicle_schema"):
                schemas = []
                for detail in result.get("schema_details", []):
                    from server.models.schemas import SchemaItem

                    schemas.append(
                        SchemaItem(
                            schema_type=detail["type"],
                            properties_found=detail["properties_found"],
                            properties_missing=detail["properties_missing"],
                            completeness=detail["completeness_score"],
                        )
                    )
                return {"url": full_url, "schemas": schemas}

        return None

    def check_vdp_content(self, html: str) -> dict:
        """Check VDP HTML for visible price, VIN, mileage, images."""
        result = {
            "price_visible": False,
            "vin_visible": False,
            "mileage_visible": False,
            "images_found": 0,
            "price_text": "",
            "vin_text": "",
            "vehicle_title": "",
        }

        price_match = PRICE_PATTERN.search(html)
        if price_match:
            result["price_visible"] = True
            result["price_text"] = price_match.group(0)

        vin_match = VIN_PATTERN.search(html)
        if vin_match:
            result["vin_visible"] = True
            result["vin_text"] = vin_match.group(0)

        if re.search(r"\d[\d,]*\s*miles|\bmileage[:\s]*\d|\bodometer[:\s]*\d", html, re.IGNORECASE):
            result["mileage_visible"] = True

        soup = self.parse_html(html)
        result["images_found"] = len(soup.find_all("img"))

        # Extract vehicle title from <h1> or <title>
        h1 = soup.find("h1")
        if h1 and h1.get_text(strip=True):
            result["vehicle_title"] = h1.get_text(strip=True)
        else:
            title_tag = soup.find("title")
            if title_tag and title_tag.get_text(strip=True):
                result["vehicle_title"] = title_tag.get_text(strip=True)

        return result
