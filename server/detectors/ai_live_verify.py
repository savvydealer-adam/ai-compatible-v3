"""Live AI verification — asks real AI APIs to fetch a VDP and checks results.

V1: AILiveVerifyDetector — single URL, informational only.
V2: AILiveVerifyDetectorV2 — multi-page comparison against ground truth, scored.
"""

import asyncio
import logging
import re

from server.config import settings
from server.models.schemas import (
    AILiveVerifyResult,
    AILiveVerifyResultV2,
    AIProviderVerification,
    AIProviderVerificationV2,
    AIVerifyCheck,
    GroundTruth,
    GroundTruthResult,
)

logger = logging.getLogger(__name__)

_ACCESS_DENIED_PATTERNS = [
    "unable to access",
    "cannot access",
    "can't access",
    "couldn't access",
    "could not access",
    "access denied",
    "access was denied",
    "blocked from accessing",
    "unable to retrieve",
    "unable to reach",
    "unable to visit",
    "cannot browse",
    "not able to access",
]


def _is_access_denied(text: str) -> bool:
    """Check if AI response indicates access was denied."""
    text_lower = text.lower()
    return any(p in text_lower for p in _ACCESS_DENIED_PATTERNS)


VERIFY_PROMPT_VDP = """Visit this URL: {vdp_url}

This is a vehicle detail page on a car dealership website.
What is the listed price of this vehicle? Answer with just the price like $XX,XXX.
What is the VIN? Answer with just the 17-character VIN.

If you cannot access the page, say "UNABLE TO ACCESS" and explain why."""

VERIFY_PROMPT_HOMEPAGE = """Visit this URL: {vdp_url}

This is a car dealership website. Can you access it?
If yes, tell me the dealership name and what brands they sell.
If you cannot access the page, say "UNABLE TO ACCESS" and explain why."""


def _get_prompt(ground_truth: "GroundTruth") -> str:
    """Pick the right prompt based on available ground truth."""
    if ground_truth.expected_price or ground_truth.expected_vin:
        return VERIFY_PROMPT_VDP.format(vdp_url=ground_truth.vdp_url)
    return VERIFY_PROMPT_HOMEPAGE.format(vdp_url=ground_truth.vdp_url)


def _normalize_price(price: str) -> str:
    """Strip price to digits only for comparison."""
    return re.sub(r"[^\d]", "", price)


def _match_vin(expected: str, returned: str) -> bool:
    """Case-insensitive exact 17-char VIN match."""
    if not expected or not returned:
        return False
    # Extract 17-char VIN from response text
    match = re.search(r"[A-HJ-NPR-Z0-9]{17}", returned, re.IGNORECASE)
    if match:
        return match.group(0).upper() == expected.upper()
    return False


def _extract_price(text: str) -> str:
    """Extract first price-like string from response."""
    match = re.search(r"\$[\d,]+(?:\.\d{2})?", text)
    return match.group(0) if match else ""


def _extract_vin(text: str) -> str:
    """Extract first 17-char VIN from response."""
    match = re.search(r"[A-HJ-NPR-Z0-9]{17}", text, re.IGNORECASE)
    return match.group(0) if match else ""


def _evaluate_response(
    text: str, ground_truth: GroundTruth
) -> tuple[bool | None, str, bool, str, bool]:
    """Evaluate AI response against ground truth.

    Returns: (could_access, returned_price, price_matches, returned_vin, vin_matches)
    """
    if _is_access_denied(text):
        return False, "", False, "", False

    returned_price = _extract_price(text)
    returned_vin = _extract_vin(text)

    # Homepage-only test (no ground truth) — any substantive response means access
    if not ground_truth.expected_price and not ground_truth.expected_vin:
        has_content = len(text.strip()) > 50
        return (True if has_content else None), returned_price, False, returned_vin, False

    price_matches = False
    if returned_price and ground_truth.expected_price:
        price_matches = _normalize_price(returned_price) == _normalize_price(
            ground_truth.expected_price
        )

    vin_matches = (
        _match_vin(ground_truth.expected_vin, text) if ground_truth.expected_vin else False
    )

    if price_matches or vin_matches:
        could_access = True
    elif not returned_price and not returned_vin:
        could_access = None  # inconclusive
    else:
        # Got data but doesn't match — could be wrong vehicle or partial access
        could_access = None

    return could_access, returned_price, price_matches, returned_vin, vin_matches


async def _verify_openai(ground_truth: GroundTruth) -> AIProviderVerification:
    """Verify using OpenAI Responses API with web_search tool."""
    result = AIProviderVerification(provider_name="openai")
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        prompt = _get_prompt(ground_truth)

        response = await asyncio.wait_for(
            client.responses.create(
                model="gpt-4o-mini",
                tools=[{"type": "web_search"}],
                input=prompt,
            ),
            timeout=settings.ai_verify_timeout,
        )

        text = response.output_text
        result.response_text = text[:500]

        could_access, ret_price, price_match, ret_vin, vin_match = _evaluate_response(
            text, ground_truth
        )
        result.could_access = could_access
        result.returned_price = ret_price
        result.price_matches = price_match
        result.returned_vin = ret_vin
        result.vin_matches = vin_match

    except Exception as e:
        result.error = str(e)[:200]
        logger.warning("OpenAI verification failed: %s", e)

    return result


async def _verify_kimi(ground_truth: GroundTruth) -> AIProviderVerification:
    """Verify using Kimi K2.5 API with built-in web_search tool."""
    result = AIProviderVerification(provider_name="kimi")
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=settings.kimi_api_key,
            base_url="https://api.moonshot.ai/v1",
        )
        prompt = _get_prompt(ground_truth)

        response = await asyncio.wait_for(
            client.chat.completions.create(
                model="kimi-k2.5",
                messages=[{"role": "user", "content": prompt}],
                tools=[
                    {
                        "type": "builtin_function",
                        "function": {"name": "$web_search"},
                    }
                ],
                extra_body={"chat_template_kwargs": {"thinking": False}},
            ),
            timeout=settings.ai_verify_timeout,
        )

        text = response.choices[0].message.content or ""
        result.response_text = text[:500]

        could_access, ret_price, price_match, ret_vin, vin_match = _evaluate_response(
            text, ground_truth
        )
        result.could_access = could_access
        result.returned_price = ret_price
        result.price_matches = price_match
        result.returned_vin = ret_vin
        result.vin_matches = vin_match

    except Exception as e:
        result.error = str(e)[:200]
        logger.warning("Kimi verification failed: %s", e)

    return result


async def _verify_gemini(ground_truth: GroundTruth) -> AIProviderVerification:
    """Verify using Gemini API with Google Search grounding."""
    result = AIProviderVerification(provider_name="gemini")
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.gemini_api_key)
        prompt = _get_prompt(ground_truth)

        response = await asyncio.wait_for(
            client.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                ),
            ),
            timeout=settings.ai_verify_timeout,
        )

        text = response.text or ""
        result.response_text = text[:500]

        could_access, ret_price, price_match, ret_vin, vin_match = _evaluate_response(
            text, ground_truth
        )
        result.could_access = could_access
        result.returned_price = ret_price
        result.price_matches = price_match
        result.returned_vin = ret_vin
        result.vin_matches = vin_match

    except Exception as e:
        result.error = str(e)[:200]
        logger.warning("Gemini verification failed: %s", e)

    return result


class AILiveVerifyDetector:
    """Orchestrates live AI verification across configured providers."""

    def __init__(self, ground_truth: GroundTruth) -> None:
        self.ground_truth = ground_truth

    async def verify(self) -> AILiveVerifyResult:
        """Run verification against all configured providers concurrently."""
        tasks: list[asyncio.Task] = []

        if settings.openai_api_key:
            tasks.append(asyncio.create_task(_verify_openai(self.ground_truth)))
        if settings.kimi_api_key:
            tasks.append(asyncio.create_task(_verify_kimi(self.ground_truth)))
        if settings.gemini_api_key:
            tasks.append(asyncio.create_task(_verify_gemini(self.ground_truth)))

        if not tasks:
            return AILiveVerifyResult(details="No AI API keys configured")

        providers = await asyncio.gather(*tasks, return_exceptions=True)

        results: list[AIProviderVerification] = []
        for p in providers:
            if isinstance(p, AIProviderVerification):
                results.append(p)
            elif isinstance(p, Exception):
                logger.warning("AI verification task exception: %s", p)

        details_parts = []
        for p in results:
            if p.could_access is True:
                details_parts.append(f"{p.provider_name}: CAN access")
            elif p.could_access is False:
                details_parts.append(f"{p.provider_name}: BLOCKED")
            elif p.error:
                details_parts.append(f"{p.provider_name}: error")
            else:
                details_parts.append(f"{p.provider_name}: inconclusive")

        has_result = any(p.could_access is not None for p in results)
        return AILiveVerifyResult(
            verified=has_result,
            providers=results,
            ground_truth_used=self.ground_truth,
            details="; ".join(details_parts) if details_parts else "No results",
        )


# ── V2: Ground-truth comparison system ──

_V2_PROMPT_TEMPLATE = (
    "Check these pages on {domain}:\n\n"
    "1. ROBOTS: Visit https://{domain}/robots.txt - Does it block AI bots "
    "like GPTBot, Claude-Web, PerplexityBot? List which are blocked.\n"
    "2. INVENTORY: Visit {srp_url} - How many vehicles are listed? "
    "Give the names and prices of the first 3 vehicles you see.\n"
    "3. VDP: Visit {vdp_url} - What is the vehicle title, listed price, "
    "and VIN (17-character alphanumeric code)?\n"
    "4. SITEMAP: Visit https://{domain}/sitemap.xml - Does it exist? "
    "Roughly how many URLs are listed?\n\n"
    'If you cannot access any page, say "BLOCKED" for that section '
    "and explain why.\n\n"
    "Format your response exactly like this:\n"
    "ROBOTS: [your findings]\n"
    "INVENTORY: [your findings]\n"
    "VDP: [your findings]\n"
    "SITEMAP: [your findings]"
)

_V2_PROMPT_NO_VDP = (
    "Check these pages on {domain}:\n\n"
    "1. ROBOTS: Visit https://{domain}/robots.txt - Does it block AI bots "
    "like GPTBot, Claude-Web, PerplexityBot? List which are blocked.\n"
    "2. SITEMAP: Visit https://{domain}/sitemap.xml - Does it exist? "
    "Roughly how many URLs are listed?\n"
    "3. HOMEPAGE: Visit https://{domain} - Can you access it? "
    "What is the dealership name?\n\n"
    'If you cannot access any page, say "BLOCKED" for that section '
    "and explain why.\n\n"
    "Format your response exactly like this:\n"
    "ROBOTS: [your findings]\n"
    "SITEMAP: [your findings]\n"
    "HOMEPAGE: [your findings]"
)


def _build_v2_prompt(domain: str, ground_truth: GroundTruthResult) -> str:
    """Build the comprehensive V2 prompt from ground truth pages."""
    srp_url = ""
    vdp_url = ""
    for page in ground_truth.pages:
        if page.page_type == "srp" and page.url:
            srp_url = page.url
        elif page.page_type == "vdp" and page.url:
            vdp_url = page.url

    if vdp_url and srp_url:
        return _V2_PROMPT_TEMPLATE.format(domain=domain, srp_url=srp_url, vdp_url=vdp_url)
    if vdp_url:
        return _V2_PROMPT_TEMPLATE.format(
            domain=domain,
            srp_url=f"https://{domain}/inventory/",
            vdp_url=vdp_url,
        )
    return _V2_PROMPT_NO_VDP.format(domain=domain)


def _parse_section(text: str, section: str) -> str:
    """Extract a named section from AI response (e.g. 'ROBOTS: ...')."""
    next_sections = r"ROBOTS|INVENTORY|VDP|SITEMAP|HOMEPAGE"
    pattern = rf"(?:^|\n)\s*{section}\s*:\s*(.*?)(?=\n\s*(?:{next_sections})\s*:|$)"
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else ""


def _check_robots_response(section_text: str, ground_truth: GroundTruthResult) -> AIVerifyCheck:
    """Compare robots section of AI response against ground truth."""
    gt_robots = next((p for p in ground_truth.pages if p.page_type == "robots"), None)

    check = AIVerifyCheck(check_type="robots")
    if not section_text:
        return check

    is_blocked = _is_access_denied(section_text)
    check.could_access = not is_blocked
    check.data_returned = section_text[:200]

    if gt_robots:
        check.data_expected = "exists" if gt_robots.accessible else "not found"
        both_match = (check.could_access and gt_robots.accessible) or (
            not check.could_access and not gt_robots.accessible
        )
        check.match_score = 1.0 if both_match else 0.0

    return check


def _check_inventory_response(section_text: str, ground_truth: GroundTruthResult) -> AIVerifyCheck:
    """Compare inventory section against ground truth."""
    gt_srp = next((p for p in ground_truth.pages if p.page_type == "srp"), None)

    check = AIVerifyCheck(check_type="inventory")
    if not section_text:
        return check

    is_blocked = _is_access_denied(section_text)
    check.could_access = not is_blocked
    check.data_returned = section_text[:200]

    if gt_srp:
        check.data_expected = f"{gt_srp.vehicle_count} vehicles"
        if check.could_access and gt_srp.accessible:
            # Try to extract a count from the response
            count_match = re.search(r"(\d+)\s*(?:vehicle|car|listing|result)", section_text, re.I)
            if count_match:
                returned_count = int(count_match.group(1))
                gt_count = gt_srp.vehicle_count
                if gt_count > 0:
                    ratio = min(returned_count, gt_count) / max(returned_count, gt_count)
                    check.match_score = min(1.0, ratio)
                else:
                    check.match_score = 0.5
            else:
                # Got text back but no count — partial
                check.match_score = 0.5
        elif not check.could_access:
            check.match_score = 0.0

    return check


def _check_vdp_response(
    section_text: str, ground_truth: GroundTruthResult, check_type: str
) -> AIVerifyCheck:
    """Compare VDP price or VIN against ground truth."""
    gt_vdp = next((p for p in ground_truth.pages if p.page_type == "vdp"), None)

    check = AIVerifyCheck(check_type=check_type)
    if not section_text:
        return check

    is_blocked = _is_access_denied(section_text)
    check.could_access = not is_blocked
    check.data_returned = section_text[:200]

    if not gt_vdp:
        return check

    if check_type == "vdp_price":
        returned_price = _extract_price(section_text)
        check.data_returned = returned_price or section_text[:100]
        check.data_expected = gt_vdp.price

        if returned_price and gt_vdp.price:
            if _normalize_price(returned_price) == _normalize_price(gt_vdp.price):
                check.match_score = 1.0
            else:
                check.match_score = 0.3  # got a price but wrong
        elif not check.could_access:
            check.match_score = 0.0

    elif check_type == "vdp_vin":
        returned_vin = _extract_vin(section_text)
        check.data_returned = returned_vin or section_text[:100]
        check.data_expected = gt_vdp.vin

        if returned_vin and gt_vdp.vin:
            if _match_vin(gt_vdp.vin, section_text):
                check.match_score = 1.0
            else:
                check.match_score = 0.3
        elif not check.could_access:
            check.match_score = 0.0

    return check


def _check_sitemap_response(section_text: str, ground_truth: GroundTruthResult) -> AIVerifyCheck:
    """Compare sitemap section against ground truth."""
    gt_sitemap = next((p for p in ground_truth.pages if p.page_type == "sitemap"), None)

    check = AIVerifyCheck(check_type="sitemap")
    if not section_text:
        return check

    is_blocked = _is_access_denied(section_text)
    check.could_access = not is_blocked
    check.data_returned = section_text[:200]

    if gt_sitemap:
        check.data_expected = f"{gt_sitemap.sitemap_url_count} URLs"
        both_match = (check.could_access and gt_sitemap.accessible) or (
            not check.could_access and not gt_sitemap.accessible
        )
        check.match_score = 1.0 if both_match else 0.0

    return check


def _calculate_provider_score(checks: list[AIVerifyCheck]) -> tuple[float, str]:
    """Calculate access score (0-10) and overall access status for a provider.

    Scoring:
    - robots.txt accessible: 2 pts
    - VDP data match (price or VIN): 3 pts
    - Inventory browsable: 3 pts
    - Sitemap accessible: 2 pts
    """
    score = 0.0
    checks_accessible = 0
    checks_blocked = 0

    for check in checks:
        if not check.could_access:
            pass
        elif check.check_type == "robots":
            score += 2.0
        elif check.check_type in ("vdp_price", "vdp_vin"):
            score += check.match_score * 1.5
        elif check.check_type == "inventory":
            score += 3.0 * max(0.5, check.match_score)
        elif check.check_type == "sitemap":
            score += 2.0

        if check.could_access is True:
            checks_accessible += 1
        elif check.could_access is False:
            checks_blocked += 1

    total_checks = checks_accessible + checks_blocked
    if total_checks == 0:
        access = "unknown"
    elif checks_blocked == 0:
        access = "full"
    elif checks_accessible == 0:
        access = "blocked"
    else:
        access = "partial"

    return min(10.0, round(score, 1)), access


async def _verify_provider_v2(provider: str, prompt: str) -> AIProviderVerificationV2:
    """Send the V2 prompt to a single provider and get raw response."""
    result = AIProviderVerificationV2(provider_name=provider)

    try:
        if provider == "openai":
            text = await _call_openai(prompt)
        elif provider == "kimi":
            text = await _call_kimi(prompt)
        elif provider == "gemini":
            text = await _call_gemini(prompt)
        else:
            result.error = f"Unknown provider: {provider}"
            return result

        result.response_text = text[:1000]
        return result

    except Exception as e:
        result.error = str(e)[:200]
        logger.warning("%s V2 verification failed: %s", provider, e)
        return result


async def _call_openai(prompt: str) -> str:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await asyncio.wait_for(
        client.responses.create(
            model="gpt-4o-mini",
            tools=[{"type": "web_search"}],
            input=prompt,
        ),
        timeout=settings.ai_verify_timeout,
    )
    return response.output_text


async def _call_kimi(prompt: str) -> str:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        api_key=settings.kimi_api_key,
        base_url="https://api.moonshot.ai/v1",
    )
    response = await asyncio.wait_for(
        client.chat.completions.create(
            model="kimi-k2.5",
            messages=[{"role": "user", "content": prompt}],
            tools=[
                {
                    "type": "builtin_function",
                    "function": {"name": "$web_search"},
                }
            ],
            extra_body={"chat_template_kwargs": {"thinking": False}},
        ),
        timeout=settings.ai_verify_timeout,
    )
    return response.choices[0].message.content or ""


async def _call_gemini(prompt: str) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.gemini_api_key)
    response = await asyncio.wait_for(
        client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        ),
        timeout=settings.ai_verify_timeout,
    )
    return response.text or ""


class AILiveVerifyDetectorV2:
    """V2: Multi-page AI verification with ground truth comparison and scoring."""

    def __init__(self, domain: str, ground_truth: GroundTruthResult) -> None:
        self.domain = domain
        self.ground_truth = ground_truth

    async def verify(self) -> AILiveVerifyResultV2:
        """Run V2 verification against all configured providers."""
        prompt = _build_v2_prompt(self.domain, self.ground_truth)

        # Launch all providers in parallel
        tasks: list[tuple[str, asyncio.Task]] = []
        if settings.openai_api_key:
            tasks.append(("openai", asyncio.create_task(_verify_provider_v2("openai", prompt))))
        if settings.kimi_api_key:
            tasks.append(("kimi", asyncio.create_task(_verify_provider_v2("kimi", prompt))))
        if settings.gemini_api_key:
            tasks.append(("gemini", asyncio.create_task(_verify_provider_v2("gemini", prompt))))

        if not tasks:
            return AILiveVerifyResultV2(summary="No AI API keys configured")

        raw_results = await asyncio.gather(*[t for _, t in tasks], return_exceptions=True)

        providers: list[AIProviderVerificationV2] = []
        for (name, _), raw in zip(tasks, raw_results, strict=True):
            if isinstance(raw, AIProviderVerificationV2):
                # Parse response into checks
                if raw.response_text and not raw.error:
                    raw.checks = self._parse_response(raw.response_text)
                    raw.access_score, raw.overall_access = _calculate_provider_score(raw.checks)
                elif raw.error:
                    raw.overall_access = "error"
                providers.append(raw)
            elif isinstance(raw, Exception):
                providers.append(
                    AIProviderVerificationV2(
                        provider_name=name,
                        error=str(raw)[:200],
                        overall_access="error",
                    )
                )

        # Calculate aggregate score (average of provider scores)
        valid_scores = [p.access_score for p in providers if p.overall_access != "error"]
        avg_score = round(sum(valid_scores) / len(valid_scores), 1) if valid_scores else 0.0

        # Build summary
        accessible_count = sum(1 for p in providers if p.overall_access in ("full", "partial"))
        total_count = len([p for p in providers if p.overall_access != "error"])
        summary = f"{accessible_count} of {total_count} AI providers can access your site"

        return AILiveVerifyResultV2(
            ground_truth=self.ground_truth,
            providers=providers,
            summary=summary,
            ai_verify_score=avg_score,
        )

    def _parse_response(self, text: str) -> list[AIVerifyCheck]:
        """Parse AI response into individual checks compared against ground truth."""
        checks: list[AIVerifyCheck] = []

        # Parse each section
        robots_text = _parse_section(text, "ROBOTS")
        inventory_text = _parse_section(text, "INVENTORY")
        vdp_text = _parse_section(text, "VDP")
        sitemap_text = _parse_section(text, "SITEMAP")

        if robots_text:
            checks.append(_check_robots_response(robots_text, self.ground_truth))

        if inventory_text:
            checks.append(_check_inventory_response(inventory_text, self.ground_truth))

        if vdp_text:
            checks.append(_check_vdp_response(vdp_text, self.ground_truth, "vdp_price"))
            checks.append(_check_vdp_response(vdp_text, self.ground_truth, "vdp_vin"))

        if sitemap_text:
            checks.append(_check_sitemap_response(sitemap_text, self.ground_truth))

        return checks
