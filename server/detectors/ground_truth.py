"""Ground truth crawler — uses Playwright to establish what a site actually contains."""

import logging
import re
import time

from server.config import settings
from server.models.schemas import GroundTruthPage, GroundTruthResult

logger = logging.getLogger(__name__)

VIN_PATTERN = re.compile(r"[A-HJ-NPR-Z0-9]{17}", re.IGNORECASE)
PRICE_PATTERN = re.compile(
    r"\$[\d,]+(?:\.\d{2})?|\bprice[:\s]*\$[\d,]+|\bmsrp[:\s]*\$[\d,]+", re.IGNORECASE
)

# AI bots to check in robots.txt
ROBOTS_AI_BOTS = ["GPTBot", "Claude-Web", "PerplexityBot", "Google-Extended", "CCBot"]


class GroundTruthCrawler:
    """Crawls a site with Playwright to establish ground truth for AI verification."""

    def __init__(
        self,
        domain: str,
        inventory_url: str = "",
        vdp_urls: list[str] | None = None,
        robots_data: dict | None = None,
        sitemap_data: dict | None = None,
        vdp_content_info: dict | None = None,
    ) -> None:
        self.domain = domain
        self.inventory_url = inventory_url
        self.vdp_urls = vdp_urls or []
        # Existing detector data for httpx fallback
        self._robots_data = robots_data
        self._sitemap_data = sitemap_data
        self._vdp_content_info = vdp_content_info

    async def crawl(self) -> GroundTruthResult:
        """Run the ground truth crawl. Falls back to httpx data if Playwright unavailable."""
        start = time.time()
        try:
            result = await self._crawl_playwright()
            result.crawl_time = round(time.time() - start, 1)
            return result
        except Exception as e:
            logger.warning("Playwright crawl failed, using httpx fallback: %s", e)
            result = self._build_httpx_fallback()
            result.crawl_time = round(time.time() - start, 1)
            return result

    async def _crawl_playwright(self) -> GroundTruthResult:
        """Crawl with Playwright headless Chromium."""
        from playwright.async_api import async_playwright

        pages: list[GroundTruthPage] = []
        timeout_ms = int(settings.playwright_timeout * 1000)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=settings.browser_ua,
                viewport={"width": 1280, "height": 720},
            )
            context.set_default_timeout(timeout_ms)

            try:
                # 1. robots.txt (~2s)
                robots_page = await self._crawl_robots(context)
                pages.append(robots_page)

                # 2. sitemap.xml (~2s)
                sitemap_page = await self._crawl_sitemap(context)
                pages.append(sitemap_page)

                # 3. SRP/Inventory (~5s)
                if self.inventory_url:
                    srp_page = await self._crawl_srp(context)
                    pages.append(srp_page)

                # 4. VDP pages (~8s for up to 2)
                for vdp_url in self.vdp_urls[:2]:
                    vdp_page = await self._crawl_vdp(context, vdp_url)
                    pages.append(vdp_page)

            finally:
                await context.close()
                await browser.close()

        return GroundTruthResult(
            pages=pages,
            source="playwright",
            domain=self.domain,
        )

    async def _crawl_robots(self, context) -> GroundTruthPage:
        """Crawl robots.txt and parse AI bot rules."""
        url = f"https://{self.domain}/robots.txt"
        page_result = GroundTruthPage(url=url, page_type="robots")

        try:
            page = await context.new_page()
            resp = await page.goto(url, wait_until="domcontentloaded", timeout=5000)
            # resp.status is the initial response; after 301 redirects
            # Playwright follows them, so check the final page content
            body = await page.inner_text("body")
            final_ok = resp and (resp.status == 200 or (resp.status in (301, 302) and body.strip()))
            if final_ok and body.strip():
                page_result.accessible = True
                page_result.robots_rules = self._parse_robots_rules(body)
                page_result.raw_content = body[:500]
            await page.close()
        except Exception as e:
            logger.debug("robots.txt crawl failed: %s", e)

        return page_result

    async def _crawl_sitemap(self, context) -> GroundTruthPage:
        """Crawl sitemap.xml and count URLs."""
        url = f"https://{self.domain}/sitemap.xml"
        page_result = GroundTruthPage(url=url, page_type="sitemap")

        try:
            page = await context.new_page()
            resp = await page.goto(url, wait_until="domcontentloaded", timeout=5000)
            text = await page.content()
            has_locs = "<loc>" in text.lower()
            final_ok = resp and (resp.status == 200 or (resp.status in (301, 302) and has_locs))
            if final_ok and has_locs:
                page_result.accessible = True
                loc_count = text.lower().count("<loc>")
                page_result.sitemap_url_count = loc_count
                loc_matches = re.findall(r"<loc>\s*(.*?)\s*</loc>", text, re.IGNORECASE)
                page_result.raw_content = "\n".join(loc_matches[:3])
            await page.close()
        except Exception as e:
            logger.debug("sitemap.xml crawl failed: %s", e)

        return page_result

    async def _crawl_srp(self, context) -> GroundTruthPage:
        """Crawl inventory/SRP page — count vehicles, extract samples."""
        page_result = GroundTruthPage(url=self.inventory_url, page_type="srp")

        try:
            page = await context.new_page()
            await page.goto(self.inventory_url, wait_until="domcontentloaded", timeout=10000)
            await page.wait_for_timeout(2000)  # JS rendering delay

            page_result.accessible = True

            # Count vehicle-like links (VIN pattern or year-make-model)
            links = await page.query_selector_all("a[href]")
            vehicle_count = 0
            for link in links[:200]:
                href = await link.get_attribute("href") or ""
                if VIN_PATTERN.search(href) or re.search(r"/\d{4}-[a-z]+-[a-z]+", href.lower()):
                    vehicle_count += 1

            page_result.vehicle_count = vehicle_count

            # Extract first 3 vehicle names for verification
            vehicle_names: list[str] = []
            h_tags = await page.query_selector_all("h2, h3")
            for h in h_tags[:20]:
                text = (await h.inner_text()).strip()
                if re.search(r"\d{4}\s+\w+", text):
                    if not page_result.vehicle_title:
                        page_result.vehicle_title = text
                    vehicle_names.append(text)
                    if len(vehicle_names) >= 3:
                        break

            page_result.raw_content = "; ".join(vehicle_names)

            await page.close()
        except Exception as e:
            logger.debug("SRP crawl failed: %s", e)

        return page_result

    async def _crawl_vdp(self, context, url: str) -> GroundTruthPage:
        """Crawl a VDP — extract price, VIN, title."""
        page_result = GroundTruthPage(url=url, page_type="vdp")

        try:
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=10000)
            await page.wait_for_timeout(2000)

            page_result.accessible = True
            content = await page.content()

            # Extract price
            price_match = PRICE_PATTERN.search(content)
            if price_match:
                page_result.price = price_match.group(0)

            # Extract VIN
            vin_match = VIN_PATTERN.search(content)
            if vin_match:
                page_result.vin = vin_match.group(0)

            # Extract title from <h1>
            h1 = await page.query_selector("h1")
            if h1:
                page_result.vehicle_title = (await h1.inner_text()).strip()
            else:
                title = await page.title()
                page_result.vehicle_title = title

            # Build raw_content snippet for verification
            parts = []
            if page_result.vehicle_title:
                parts.append(page_result.vehicle_title)
            if page_result.price:
                parts.append(page_result.price)
            if page_result.vin:
                parts.append(page_result.vin)
            page_result.raw_content = " | ".join(parts)

            await page.close()
        except Exception as e:
            logger.debug("VDP crawl failed: %s", e)

        return page_result

    def _build_httpx_fallback(self) -> GroundTruthResult:
        """Build ground truth from existing httpx detector data when Playwright unavailable."""
        pages: list[GroundTruthPage] = []

        # robots.txt from existing data
        if self._robots_data:
            rules = {}
            bot_permissions = self._robots_data.get("bot_permissions", {})
            for bot in ROBOTS_AI_BOTS:
                perm = bot_permissions.get(bot, "not_specified")
                rules[bot] = "blocked" if perm == "blocked" else "allowed"
            raw_robots = self._robots_data.get("raw_robots_txt", "")
            pages.append(
                GroundTruthPage(
                    url=f"https://{self.domain}/robots.txt",
                    page_type="robots",
                    accessible=self._robots_data.get("robots_txt_exists", False),
                    robots_rules=rules,
                    raw_content=raw_robots[:500] if raw_robots else "",
                )
            )

        # sitemap from existing data
        if self._sitemap_data:
            sample_urls = self._sitemap_data.get("sample_urls", [])
            pages.append(
                GroundTruthPage(
                    url=self._sitemap_data.get("sitemap_url", f"https://{self.domain}/sitemap.xml"),
                    page_type="sitemap",
                    accessible=self._sitemap_data.get("sitemap_found", False),
                    sitemap_url_count=self._sitemap_data.get("total_urls", 0),
                    raw_content="\n".join(sample_urls[:3]),
                )
            )

        # VDP from existing content info
        if self._vdp_content_info and self.vdp_urls:
            vdp_parts = []
            vdp_title = self._vdp_content_info.get("vehicle_title", "")
            vdp_price = self._vdp_content_info.get("price_text", "")
            vdp_vin = self._vdp_content_info.get("vin_text", "")
            if vdp_title:
                vdp_parts.append(vdp_title)
            if vdp_price:
                vdp_parts.append(vdp_price)
            if vdp_vin:
                vdp_parts.append(vdp_vin)
            pages.append(
                GroundTruthPage(
                    url=self.vdp_urls[0],
                    page_type="vdp",
                    accessible=True,
                    price=vdp_price,
                    vin=vdp_vin,
                    vehicle_title=vdp_title,
                    raw_content=" | ".join(vdp_parts),
                )
            )

        return GroundTruthResult(
            pages=pages,
            source="httpx_fallback",
            domain=self.domain,
        )

    @staticmethod
    def _parse_robots_rules(robots_text: str) -> dict[str, str]:
        """Parse robots.txt content for AI bot rules."""
        rules: dict[str, str] = {}
        current_agent = ""

        for line in robots_text.splitlines():
            line = line.strip()
            if line.startswith("#") or not line:
                continue

            if line.lower().startswith("user-agent:"):
                current_agent = line.split(":", 1)[1].strip()
                continue

            if line.lower().startswith("disallow:"):
                path = line.split(":", 1)[1].strip()
                if path in ("/", "/*"):
                    for bot in ROBOTS_AI_BOTS:
                        agent_matches = current_agent == "*" or current_agent.lower() == bot.lower()
                        if agent_matches and (bot not in rules or rules[bot] != "allowed"):
                            rules[bot] = "blocked"

            if line.lower().startswith("allow:"):
                path = line.split(":", 1)[1].strip()
                if path == "/" or path == "/*":
                    for bot in ROBOTS_AI_BOTS:
                        if current_agent == "*" or current_agent.lower() == bot.lower():
                            rules[bot] = "allowed"

        # Default to allowed for bots not mentioned
        for bot in ROBOTS_AI_BOTS:
            if bot not in rules:
                rules[bot] = "allowed"

        return rules
