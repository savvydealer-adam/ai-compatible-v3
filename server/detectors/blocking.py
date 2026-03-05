"""CloudFlare, 403, JS challenge, CAPTCHA, rate limiting detection."""

import asyncio
import logging
import re

import httpx

from server.config import settings
from server.detectors.base import BaseDetector
from server.models.schemas import BlockingInfo

logger = logging.getLogger(__name__)

CLOUDFLARE_CONTENT_PATTERNS = [
    "checking your browser before accessing",
    "cloudflare ray id",
    "cf-browser-verification",
    "please enable cookies and refresh",
    "ddos protection by cloudflare",
    "__cf_challenge_submission",
    "cf-challenge-running",
    "enable javascript and cookies to continue",
    "cloudflare protection",
    "protected by cloudflare",
    "cloudflare security check",
    "cloudflare firewall",
]

JS_CHALLENGE_PATTERNS = [
    "checking your browser",
    "please wait while we check your browser",
    "javascript is required",
    "enable javascript to continue",
    "just a moment",
    "_cf_chl_opt",
    "cf-browser-verification",
    "challenge-platform",
    "cf_chl_opt",
    "jschl-answer",
    "data-cf-settings",
    "challenge-running",
]

SITE_BLOCKING_CAPTCHA_PATTERNS = [
    "verify you are human to access",
    "prove you are human to continue",
    "complete the captcha to proceed",
    "solve the captcha to access",
    "verify to access this site",
    "human verification required to continue",
    "captcha verification required to proceed",
    "verify you're not a robot to continue",
]

CAPTCHA_INDICATORS = [
    "captcha",
    "recaptcha",
    "hcaptcha",
    "i'm not a robot",
    "verify you are human",
    "prove you are human",
    "solve the puzzle",
    "human verification",
    "are you a robot",
]

FORM_CONTEXT_PATTERNS = [
    "submit",
    "contact form",
    "lead form",
    "inquiry form",
    "message form",
    "quote form",
    "registration form",
    "sign up",
    "newsletter",
    "comment form",
    "feedback form",
    "apply form",
]

SITE_BLOCKING_CONTEXT = [
    "to access this site",
    "to continue browsing",
    "to view this page",
    "to proceed",
    "access denied",
    "verify to continue",
    "before accessing",
    "security check required",
]

CAPTCHA_ELEMENTS = [
    "google.com/recaptcha",
    "hcaptcha.com",
    "captcha-delivery",
    "data-sitekey",
    "g-recaptcha",
]

RATE_LIMIT_PATTERNS = [
    "rate limit exceeded",
    "you have been rate limited",
    "request rate too high",
    "rate limiting in effect",
    "exceeded the rate limit",
]


class BlockingDetector(BaseDetector):
    """Detect blocking mechanisms: CloudFlare, CAPTCHA, rate limiting, 403s."""

    async def check_access(self, domain: str) -> tuple[BlockingInfo, httpx.Response | None]:
        """Check basic site accessibility and detect blocking."""
        url = self.make_url(domain)
        info = BlockingInfo()

        resp = await self._try_access(url)
        if resp is None:
            info.is_blocked = True
            info.details.append("Site unreachable (connection error or timeout)")
            return info, None

        info.status_code = resp.status_code

        if resp.status_code == 403:
            info.is_blocked = True
            info.details.append("HTTP 403 Forbidden")
            info.blocking_provider = self._identify_blocking_provider(resp)

        # CloudFlare detection
        cf = self._detect_cloudflare(resp)
        info.cloudflare_detected = cf

        # JS challenge detection
        content_lower = resp.text[:10000].lower() if resp.text else ""
        if self._detect_js_challenge(resp, content_lower):
            info.js_challenge = True
            info.is_blocked = True
            info.details.append("JavaScript challenge detected")

        # CAPTCHA detection
        if self._detect_captcha(content_lower):
            info.captcha_detected = True
            info.is_blocked = True
            info.details.append("Site-blocking CAPTCHA detected")

        # Classify Cloudflare tier from initial response when blocked
        if cf and info.is_blocked:
            body = (resp.text or "")[:15000]
            has_cf_mitigated = bool(resp.headers.get("cf-mitigated"))
            has_challenge_platform = "/cdn-cgi/challenge-platform/" in body

            if has_cf_mitigated:
                info.cloudflare_blocking_tier = "super_bot_fight_mode"
                info.cloudflare_tier_signals.append("cf-mitigated header")
            elif has_challenge_platform:
                info.cloudflare_blocking_tier = "bot_fight_mode"
                info.cloudflare_tier_signals.append("/cdn-cgi/challenge-platform/ in response")
            elif info.js_challenge:
                info.cloudflare_blocking_tier = "bot_fight_mode"
                info.cloudflare_tier_signals.append("JS challenge on browser request")
            elif resp.status_code == 403:
                info.cloudflare_blocking_tier = "ai_scrapers_toggle"
                info.cloudflare_tier_signals.append("Cloudflare 403 on browser request")
            else:
                info.cloudflare_blocking_tier = "enterprise"
                info.cloudflare_tier_signals.append("Cloudflare blocking, tier unclear")

        return info, resp

    async def check_rate_limiting(self, domain: str) -> bool:
        """Detect aggressive rate limiting by making rapid requests."""
        url = self.make_url(domain)
        error_count = 0

        for _ in range(3):
            try:
                resp = await self.client.get(
                    url,
                    headers=self._browser_headers(),
                    timeout=5.0,
                    follow_redirects=True,
                )
                if resp.status_code == 429:
                    return True
                if resp.status_code in (503, 509):
                    error_count += 1
                    if error_count >= 2:
                        return True

                # Check content for rate limit messages (only short pages)
                if resp.text and len(resp.text) < 5000:
                    text_lower = resp.text.lower()
                    if any(p in text_lower for p in RATE_LIMIT_PATTERNS):
                        return True

            except (httpx.HTTPError, httpx.TimeoutException):
                error_count += 1

            await asyncio.sleep(0.5)

        return False

    def is_cloudflare_challenge(self, content: str) -> bool:
        """Check if content is a CloudFlare challenge page."""
        lower = content[:10000].lower()
        indicators = [
            "just a moment",
            "_cf_chl_opt",
            "cf-browser-verification",
            "challenge-platform",
            "enable javascript and cookies to continue",
            "checking your browser",
            "cf_chl_opt",
            "jschl-answer",
            "data-cf-settings",
            "challenge-running",
        ]
        return sum(1 for i in indicators if i in lower) >= 2

    async def _try_access(self, url: str) -> httpx.Response | None:
        """Try HTTPS then HTTP with retries."""
        for scheme in ("https://", "http://"):
            target = re.sub(r"^https?://", scheme, url)
            for attempt in range(2):
                try:
                    resp = await self.client.get(
                        target,
                        headers=self._browser_headers(),
                        timeout=settings.request_timeout,
                        follow_redirects=True,
                    )
                    return resp
                except (httpx.HTTPError, httpx.TimeoutException):
                    if attempt == 0:
                        await asyncio.sleep(0.5)
        return None

    def _detect_cloudflare(self, resp: httpx.Response) -> bool:
        """Detect CloudFlare from headers, cookies, and content."""
        # Headers
        server = resp.headers.get("server", "").lower()
        if "cloudflare" in server:
            return True
        if "cf-ray" in resp.headers:
            return True
        if "cf-cache-status" in resp.headers:
            return True

        # Cookies
        cookie_header = resp.headers.get("set-cookie", "")
        if "__cf" in cookie_header or "cf_" in cookie_header:
            return True

        # Content
        content_lower = resp.text[:10000].lower() if resp.text else ""
        return any(p in content_lower for p in CLOUDFLARE_CONTENT_PATTERNS)

    def _detect_js_challenge(self, resp: httpx.Response, content_lower: str) -> bool:
        """Detect JavaScript challenge pages."""
        matches = sum(1 for p in JS_CHALLENGE_PATTERNS if p in content_lower)
        if matches >= 2:
            return True
        return resp.status_code in (403, 503) and self._detect_cloudflare(resp)

    def _detect_captcha(self, content_lower: str) -> bool:
        """Detect site-blocking CAPTCHAs (not form CAPTCHAs)."""
        # Direct site-blocking patterns
        if any(p in content_lower for p in SITE_BLOCKING_CAPTCHA_PATTERNS):
            return True

        # General indicators need context analysis
        has_indicator = any(p in content_lower for p in CAPTCHA_INDICATORS)
        if not has_indicator:
            return False

        # Check if it's in a form context (benign)
        if any(p in content_lower for p in FORM_CONTEXT_PATTERNS) and not any(
            p in content_lower for p in SITE_BLOCKING_CONTEXT
        ):
            return False

        # Check for site-blocking context
        if any(p in content_lower for p in SITE_BLOCKING_CONTEXT):
            return True

        # Fallback: check for technical CAPTCHA elements
        return any(p in content_lower for p in CAPTCHA_ELEMENTS)

    @staticmethod
    def classify_cloudflare_tier(
        cloudflare_detected: bool,
        bot_results: list,
    ) -> tuple[str, list[str]]:
        """Classify Cloudflare blocking tier from bot response signals.

        Tiers (from lightest to heaviest):
        - none: No Cloudflare detected
        - passive: Cloudflare present but not blocking AI bots
        - ai_scrapers_toggle: Straight 403 for bot UAs, no challenge page
        - bot_fight_mode: JS challenge with /cdn-cgi/challenge-platform/
        - super_bot_fight_mode: cf-mitigated header present
        - enterprise: Cloudflare blocking but no identifiable tier signals
        """
        if not cloudflare_detected:
            return "none", []

        blocked_bots = [b for b in bot_results if b.http_accessible is False]

        if not blocked_bots:
            return "passive", ["Cloudflare present, no AI bots blocked"]

        signals: list[str] = []
        has_challenge_platform = any(b.challenge_platform_detected for b in blocked_bots)
        has_cf_mitigated = any(b.cf_mitigated_header for b in blocked_bots)
        has_403 = any(b.http_status == 403 for b in blocked_bots)
        has_503 = any(b.http_status in (503, 429) for b in blocked_bots)

        # Super Bot Fight Mode: cf-mitigated header is the strongest signal
        if has_cf_mitigated:
            signals.append("cf-mitigated header on bot response")
            if has_challenge_platform:
                signals.append("/cdn-cgi/challenge-platform/ in response body")
            return "super_bot_fight_mode", signals

        # Bot Fight Mode: challenge-platform in body without cf-mitigated
        if has_challenge_platform:
            signals.append("/cdn-cgi/challenge-platform/ in response body")
            if has_503:
                signals.append("503 JS challenge responses")
            return "bot_fight_mode", signals

        # AI Scrapers Toggle: clean 403 with no challenge infrastructure
        if has_403 and not has_503:
            signals.append("Direct 403 for bot UAs, no challenge page")
            return "ai_scrapers_toggle", signals

        # Cloudflare is blocking but tier is unclear
        if has_503:
            signals.append("503 responses without challenge-platform")
        if has_403:
            signals.append("403 responses")
        signals.append("Cloudflare blocking detected, specific tier unclear")
        return "enterprise", signals

    @staticmethod
    def _identify_blocking_provider(resp: httpx.Response) -> str:
        """Identify which service is blocking access on a 403."""
        # Header-based detection
        server = resp.headers.get("server", "").lower()
        if "cloudflare" in server or "cf-ray" in resp.headers:
            return "CloudFlare"
        if "akamai" in server or "akamai-origin-hop" in resp.headers:
            return "Akamai"
        if "awselb" in server or "aws" in server:
            return "AWS WAF"
        if "incap" in server or "x-iinfo" in resp.headers:
            return "Incapsula"
        if "sucuri" in server:
            return "Sucuri"

        # Content-based detection
        from server.data.provider_patterns import BLOCKING_PROVIDER_PATTERNS

        content_lower = resp.text[:10000].lower() if resp.text else ""
        for pattern, provider in BLOCKING_PROVIDER_PATTERNS:
            if pattern in content_lower:
                return provider

        return "Unknown Security Service"
