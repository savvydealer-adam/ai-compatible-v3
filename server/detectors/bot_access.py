"""HTTP user-agent testing per AI bot."""

import asyncio
import logging

import httpx

from server.config import settings
from server.data.bot_user_agents import ALL_AI_BOTS
from server.detectors.base import BaseDetector
from server.models.schemas import BotPermission

logger = logging.getLogger(__name__)


class BotAccessDetector(BaseDetector):
    """Test HTTP accessibility for each AI bot user agent."""

    async def test(self, domain: str, robots_permissions: dict[str, str]) -> list[BotPermission]:
        """Test each AI bot's HTTP access to the site."""
        url = self.make_url(domain)

        # Get browser baseline
        browser_status, browser_length = await self._get_browser_baseline(url)

        results: list[BotPermission] = []
        for bot_name, ua_string in ALL_AI_BOTS.items():
            if self._check_timeout():
                break

            perm = await self._test_bot(
                url,
                bot_name,
                ua_string,
                browser_status,
                browser_length,
                robots_permissions.get(bot_name, "unknown"),
            )
            results.append(perm)
            await asyncio.sleep(0.5)  # Rate limiting between tests

        return results

    async def _get_browser_baseline(self, url: str) -> tuple[int, int]:
        """Get browser response as baseline for comparison."""
        try:
            resp = await self.client.get(
                url,
                headers=self._browser_headers(),
                timeout=settings.request_timeout,
                follow_redirects=True,
            )
            return resp.status_code, len(resp.text) if resp.text else 0
        except (httpx.HTTPError, httpx.TimeoutException):
            return 0, 0

    async def _test_bot(
        self,
        url: str,
        bot_name: str,
        ua_string: str,
        browser_status: int,
        browser_length: int,
        robots_status: str,
    ) -> BotPermission:
        """Test a single bot's access."""
        perm = BotPermission(
            bot_name=bot_name,
            user_agent=ua_string,
            robots_status=robots_status,
        )

        try:
            import time

            start = time.time()
            resp = await self.client.get(
                url,
                headers={
                    "User-Agent": ua_string,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                },
                timeout=settings.bot_test_timeout,
                follow_redirects=True,
            )
            perm.response_time = round(time.time() - start, 2)
            perm.http_status = resp.status_code

            if resp.status_code == 403:
                perm.http_accessible = False
                perm.details = "HTTP 403 Forbidden"
            elif resp.status_code in (503, 429):
                # Check if CloudFlare challenge
                from server.detectors.blocking import BlockingDetector

                bd = BlockingDetector(self.client, self.page_cache)
                if bd.is_cloudflare_challenge(resp.text or ""):
                    perm.http_accessible = False
                    perm.details = "CloudFlare challenge"
                else:
                    perm.http_accessible = False
                    perm.details = f"HTTP {resp.status_code}"
            elif resp.status_code == 200:
                content_length = len(resp.text) if resp.text else 0
                if browser_length > 0:
                    ratio = content_length / browser_length if browser_length else 0
                    if 0.5 <= ratio <= 1.5:
                        perm.http_accessible = True
                        perm.details = "Full access"
                    elif ratio < 0.5:
                        perm.http_accessible = False
                        perm.details = "Significantly reduced content"
                    else:
                        perm.http_accessible = True
                        perm.details = "Access with different content size"
                else:
                    perm.http_accessible = True
                    perm.details = "HTTP 200 OK"
            else:
                perm.http_accessible = None
                perm.details = f"HTTP {resp.status_code}"

        except httpx.TimeoutException:
            perm.http_accessible = False
            perm.details = "Request timed out"
        except httpx.HTTPError as e:
            perm.http_accessible = False
            perm.details = f"Connection error: {type(e).__name__}"

        return perm
