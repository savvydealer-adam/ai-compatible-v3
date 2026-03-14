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
    "not accessible",
    "is not accessible",
    "are not accessible",
    "currently inaccessible",
    "inaccessible",
    "inaccessibility",
]


def _is_access_denied(text: str) -> bool:
    """Check if AI response indicates access was denied."""
    text_lower = text.lower()
    return any(p in text_lower for p in _ACCESS_DENIED_PATTERNS)


_NOT_FOUND_PATTERNS = [
    "not found",
    "404",
    "does not exist",
    "doesn't exist",
    "no robots.txt",
    "no sitemap",
    "inaccessible",
    "unavailable",
    "missing",
]


def _is_not_found(text: str) -> bool:
    """Check if AI response indicates the page doesn't exist (404, not found).

    This is distinct from being blocked — a 404 means the AI reached the
    server successfully but the file isn't there.
    """
    text_lower = text.lower()
    return any(p in text_lower for p in _NOT_FOUND_PATTERNS)


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
    """Verify using Gemini API with URL context and Google Search."""
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
                    tools=[types.Tool(url_context=types.UrlContext())],
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
    "I need you to fetch specific pages and return exact data from each.\n\n"
    "1. ROBOTS: Fetch https://{domain}/robots.txt\n"
    "   Copy the first 5 lines of text exactly as they appear.\n\n"
    "2. INVENTORY: Fetch {srp_url}\n"
    "   Return the names and prices of the first 3 vehicles listed.\n\n"
    "3. VDP: Fetch {vdp_url}\n"
    "   Return the vehicle price (e.g. $XX,XXX) and the 17-character VIN.\n\n"
    "4. SITEMAP: Fetch https://{domain}/sitemap.xml\n"
    "   Return the total number of <loc> entries and the first 3 URLs.\n\n"
    "IMPORTANT: For each section, respond with one of:\n"
    "- The requested data if the page exists\n"
    '- "NOT FOUND" if the page returns a 404 or does not exist\n'
    '- "BLOCKED" only if you cannot reach the server at all '
    "(connection refused, timeout, Cloudflare block)\n\n"
    "ROBOTS:\nINVENTORY:\nVDP:\nSITEMAP:"
)

_V2_PROMPT_NO_VDP = (
    "I need you to fetch specific pages and return exact data from each.\n\n"
    "1. ROBOTS: Fetch https://{domain}/robots.txt\n"
    "   Copy the first 5 lines of text exactly as they appear.\n\n"
    "2. SITEMAP: Fetch https://{domain}/sitemap.xml\n"
    "   Return the total number of <loc> entries and the first 3 URLs.\n\n"
    "3. HOMEPAGE: Fetch https://{domain}\n"
    "   Return the dealership name shown on the page.\n\n"
    "IMPORTANT: For each section, respond with one of:\n"
    "- The requested data if the page exists\n"
    '- "NOT FOUND" if the page returns a 404 or does not exist\n'
    '- "BLOCKED" only if you cannot reach the server at all '
    "(connection refused, timeout, Cloudflare block)\n\n"
    "ROBOTS:\nSITEMAP:\nHOMEPAGE:"
)

# Discovery prompt: used when our server is DC-blocked and we have no ground truth.
# AI providers navigate the site themselves to find inventory/VDP data.
_DISCOVERY_PROMPT = (
    "Visit each URL below and return the data requested.\n\n"
    "HOMEPAGE: Visit https://{domain} — what is the dealership name and brands sold?\n\n"
    "ROBOTS: Visit https://{domain}/robots.txt — copy the first 5 lines exactly.\n\n"
    "INVENTORY: Visit https://{domain}/new-inventory/ — list the first 3 vehicles "
    "with their prices. If that URL fails, try /used-inventory/ or /inventory/.\n\n"
    "VDP: From any inventory listing, visit one vehicle detail page. "
    "Return the Year Make Model, price, and 17-character VIN.\n\n"
    "SITEMAP: Visit https://{domain}/sitemap.xml — how many URLs total? List the first 3.\n\n"
    'For each section respond with the data, "NOT FOUND" if 404, '
    'or "BLOCKED" if the server refuses the connection.\n\n'
    "HOMEPAGE:\nROBOTS:\nINVENTORY:\nVDP:\nSITEMAP:"
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
    # Strip markdown bold/heading markers so **HOMEPAGE:** and ## ROBOTS: both match
    cleaned = re.sub(r"\*\*", "", text)
    cleaned = re.sub(r"^#{1,3}\s*", "", cleaned, flags=re.MULTILINE)
    sections = r"HOMEPAGE|ROBOTS|INVENTORY|VDP|SITEMAP"
    num = r"(?:\d+[\.\)]\s*)?"
    pattern = rf"(?:^|\n)\s*{num}{section}\s*:\s*(.*?)(?=\n\s*{num}(?:{sections})\s*:|$)"
    match = re.search(pattern, cleaned, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else ""


def _check_robots_response(section_text: str, ground_truth: GroundTruthResult) -> AIVerifyCheck:
    """Compare robots section: do AI-returned lines appear in our raw robots.txt?"""
    gt_robots = next((p for p in ground_truth.pages if p.page_type == "robots"), None)

    check = AIVerifyCheck(check_type="robots")
    if not section_text:
        return check

    check.data_returned = section_text[:300]

    # AI says file doesn't exist (404) — that means it reached the server
    ai_says_not_found = section_text.strip().upper() == "NOT FOUND" or _is_not_found(section_text)
    ai_says_blocked = section_text.strip().upper() == "BLOCKED" or (
        _is_access_denied(section_text) and not ai_says_not_found
    )

    if ai_says_not_found:
        # AI reached the server and correctly identified 404
        check.could_access = True
        if gt_robots and not gt_robots.accessible:
            # Both agree: file doesn't exist — perfect match
            check.data_expected = "Not found"
            check.match_score = 1.0
        elif gt_robots and gt_robots.accessible:
            # We found it but AI says 404 — mismatch
            first_line = gt_robots.raw_content.splitlines()[0] if gt_robots.raw_content else ""
            check.data_expected = first_line or "Exists"
            check.match_score = 0.2
        return check

    if ai_says_blocked:
        check.could_access = False
        if gt_robots:
            gt_lines = gt_robots.raw_content.splitlines()[:5]
            check.data_expected = "\n".join(gt_lines) if gt_lines else "N/A"
        check.match_score = 0.0
        return check

    if not gt_robots or not gt_robots.raw_content:
        # No ground truth raw content — treat as accessible if substantive
        check.could_access = len(section_text.strip()) > 20
        if gt_robots:
            check.data_expected = "Not found" if not gt_robots.accessible else "Exists"
        # Discovery mode: give credit for returning robots.txt-like content
        if check.could_access and re.search(r"user-agent|disallow|allow|sitemap", section_text, re.I):
            check.match_score = 0.7
        elif check.could_access:
            check.match_score = 0.5
        return check

    # Compare: do lines from AI response appear as substrings in our raw content?
    gt_raw = gt_robots.raw_content.lower()
    gt_lines = [ln.strip() for ln in gt_robots.raw_content.splitlines()[:5] if ln.strip()]
    check.data_expected = "\n".join(gt_lines)

    ai_lines = [ln.strip() for ln in section_text.splitlines() if ln.strip()]
    matched = 0
    for ai_line in ai_lines:
        if ai_line.lower() in gt_raw:
            matched += 1

    if matched >= 3 or (gt_lines and matched >= len(gt_lines)):
        check.could_access = True
        check.match_score = 1.0
    elif matched >= 1:
        check.could_access = True
        check.match_score = round(matched / max(len(gt_lines), 1), 2)
    else:
        # AI returned text but none matches — they might have accessed a different version
        check.could_access = len(section_text.strip()) > 20
        check.match_score = 0.2 if check.could_access else 0.0

    return check


def _check_inventory_response(section_text: str, ground_truth: GroundTruthResult) -> AIVerifyCheck:
    """Compare inventory: do vehicle names from ground truth appear in AI response?"""
    gt_srp = next((p for p in ground_truth.pages if p.page_type == "srp"), None)

    check = AIVerifyCheck(check_type="inventory")
    if not section_text:
        return check

    check.data_returned = section_text[:300]

    ai_says_not_found = section_text.strip().upper() == "NOT FOUND" or _is_not_found(section_text)
    ai_says_blocked = section_text.strip().upper() == "BLOCKED" or (
        _is_access_denied(section_text) and not ai_says_not_found
    )

    if ai_says_not_found:
        check.could_access = True
        if gt_srp and not gt_srp.accessible:
            check.data_expected = "Not found"
            check.match_score = 1.0
        elif gt_srp:
            check.data_expected = gt_srp.raw_content or f"{gt_srp.vehicle_count} vehicles"
            check.match_score = 0.2
        return check

    if ai_says_blocked:
        check.could_access = False
        if gt_srp:
            check.data_expected = gt_srp.raw_content or f"{gt_srp.vehicle_count} vehicles"
        check.match_score = 0.0
        return check

    check.could_access = True

    # No ground truth or empty stub (DC-blocked site) — use discovery scoring
    gt_has_data = gt_srp and (gt_srp.raw_content or gt_srp.vehicle_count > 0)
    if not gt_has_data:
        has_price = bool(_extract_price(section_text))
        has_vehicles = bool(re.search(r"\d{4}\s+\w+", section_text))  # year + make
        if has_price or has_vehicles:
            check.match_score = 0.7  # substantive vehicle data without GT to compare
        elif len(section_text.strip()) > 50:
            check.match_score = 0.5  # got some text, might be useful
        return check

    check.data_expected = gt_srp.raw_content or f"{gt_srp.vehicle_count} vehicles"

    score = 0.0
    text_lower = section_text.lower()

    # Check if vehicle names from ground truth appear in AI's response
    if gt_srp.raw_content:
        gt_vehicles = [v.strip() for v in gt_srp.raw_content.split(";") if v.strip()]
        name_matches = 0
        for vehicle in gt_vehicles:
            # Match on year+make or year+model substring
            parts = vehicle.lower().split()
            if len(parts) >= 2 and any(p in text_lower for p in parts[:3]):
                name_matches += 1
        if gt_vehicles:
            score = round(name_matches / len(gt_vehicles), 2)

    # Also check count ratio as supplementary signal
    count_match = re.search(r"(\d+)\s*(?:vehicle|car|listing|result)", section_text, re.I)
    if count_match and gt_srp.vehicle_count > 0:
        returned_count = int(count_match.group(1))
        ratio = min(returned_count, gt_srp.vehicle_count) / max(
            returned_count, gt_srp.vehicle_count
        )
        score = max(score, round(ratio * 0.8, 2))  # count alone caps at 0.8

    check.match_score = min(1.0, score) if score > 0 else 0.3  # got text = at least partial

    return check


def _check_vdp_response(
    section_text: str, ground_truth: GroundTruthResult, check_type: str
) -> AIVerifyCheck:
    """Compare VDP price or VIN: exact data matching."""
    gt_vdp = next((p for p in ground_truth.pages if p.page_type == "vdp"), None)

    check = AIVerifyCheck(check_type=check_type)
    if not section_text:
        return check

    ai_says_not_found = section_text.strip().upper() == "NOT FOUND" or _is_not_found(section_text)
    ai_says_blocked = section_text.strip().upper() == "BLOCKED" or (
        _is_access_denied(section_text) and not ai_says_not_found
    )

    if ai_says_not_found:
        check.could_access = True
        if gt_vdp and not gt_vdp.accessible:
            check.data_expected = "Not found"
            check.match_score = 1.0
        elif gt_vdp:
            check.data_expected = gt_vdp.price if check_type == "vdp_price" else gt_vdp.vin
            check.match_score = 0.2
        return check

    if ai_says_blocked:
        check.could_access = False
        if gt_vdp:
            check.data_expected = gt_vdp.price if check_type == "vdp_price" else gt_vdp.vin
        check.match_score = 0.0
        return check

    check.could_access = True

    # No ground truth or empty stub (DC-blocked site) — use discovery scoring
    gt_has_data = gt_vdp and (gt_vdp.price or gt_vdp.vin)
    if not gt_has_data:
        check.data_returned = section_text[:200]
        if check_type == "vdp_price" and _extract_price(section_text):
            check.match_score = 0.7  # found a price without GT to compare
        elif check_type == "vdp_vin" and _extract_vin(section_text):
            check.match_score = 0.7  # found a VIN without GT to compare
        elif len(section_text.strip()) > 50:
            check.match_score = 0.4  # got text but no structured data
        return check

    if check_type == "vdp_price":
        returned_price = _extract_price(section_text)
        check.data_returned = returned_price or section_text[:100]
        check.data_expected = gt_vdp.price

        if returned_price and gt_vdp.price:
            if _normalize_price(returned_price) == _normalize_price(gt_vdp.price):
                check.match_score = 1.0
            else:
                # Close price (within $500) gets partial credit
                try:
                    ai_val = int(_normalize_price(returned_price))
                    gt_val = int(_normalize_price(gt_vdp.price))
                    if abs(ai_val - gt_val) <= 500:
                        check.match_score = 0.5
                    else:
                        check.match_score = 0.3
                except ValueError:
                    check.match_score = 0.3

    elif check_type == "vdp_vin":
        returned_vin = _extract_vin(section_text)
        check.data_returned = returned_vin or section_text[:100]
        check.data_expected = gt_vdp.vin

        if returned_vin and gt_vdp.vin:
            if returned_vin.upper() == gt_vdp.vin.upper():
                check.match_score = 1.0
            else:
                check.match_score = 0.3
        elif not returned_vin:
            check.match_score = 0.0

    return check


def _check_sitemap_response(section_text: str, ground_truth: GroundTruthResult) -> AIVerifyCheck:
    """Compare sitemap: check URL count and whether AI returned known URLs."""
    gt_sitemap = next((p for p in ground_truth.pages if p.page_type == "sitemap"), None)

    check = AIVerifyCheck(check_type="sitemap")
    if not section_text:
        return check

    check.data_returned = section_text[:300]

    # AI says file doesn't exist (404) — that means it reached the server
    ai_says_not_found = section_text.strip().upper() == "NOT FOUND" or _is_not_found(section_text)
    ai_says_blocked = section_text.strip().upper() == "BLOCKED" or (
        _is_access_denied(section_text) and not ai_says_not_found
    )

    if ai_says_not_found:
        check.could_access = True
        if gt_sitemap and not gt_sitemap.accessible:
            check.data_expected = "Not found"
            check.match_score = 1.0
        elif gt_sitemap and gt_sitemap.accessible:
            check.data_expected = f"{gt_sitemap.sitemap_url_count} URLs"
            check.match_score = 0.2
        return check

    if ai_says_blocked:
        check.could_access = False
        if gt_sitemap:
            check.data_expected = f"{gt_sitemap.sitemap_url_count} URLs" + (
                f"\n{gt_sitemap.raw_content}" if gt_sitemap.raw_content else ""
            )
        check.match_score = 0.0
        return check

    check.could_access = True

    # No ground truth or empty stub (DC-blocked site) — use discovery scoring
    gt_has_data = gt_sitemap and gt_sitemap.sitemap_url_count > 0
    if not gt_has_data:
        if re.search(r"<loc>|\.xml|url", section_text, re.I) and len(section_text.strip()) > 30:
            check.match_score = 0.6
        elif len(section_text.strip()) > 30:
            check.match_score = 0.4
        return check

    check.data_expected = f"{gt_sitemap.sitemap_url_count} URLs"
    if gt_sitemap.raw_content:
        check.data_expected += f"\n{gt_sitemap.raw_content}"

    score = 0.0

    # Check if any ground truth URLs appear in AI response
    if gt_sitemap.raw_content:
        gt_urls = [u.strip() for u in gt_sitemap.raw_content.split("\n") if u.strip()]
        url_matches = sum(1 for u in gt_urls if u in section_text)
        if gt_urls:
            score = round(url_matches / len(gt_urls), 2)

    # Count comparison
    count_match = re.search(r"(\d[\d,]*)\s*(?:<loc>|url|entries|total)", section_text, re.I)
    if not count_match:
        count_match = re.search(r"(?:total|contains|found|has)\s*(\d[\d,]*)", section_text, re.I)
    if count_match and gt_sitemap.sitemap_url_count > 0:
        returned_count = int(count_match.group(1).replace(",", ""))
        gt_count = gt_sitemap.sitemap_url_count
        ratio = min(returned_count, gt_count) / max(returned_count, gt_count)
        score = max(score, round(ratio * 0.8, 2))

    check.match_score = min(1.0, score) if score > 0 else 0.3

    return check


def _check_homepage_response(section_text: str) -> AIVerifyCheck:
    """Check if AI could access the homepage (discovery mode)."""
    check = AIVerifyCheck(check_type="homepage")
    if not section_text:
        return check

    check.data_returned = section_text[:300]

    ai_says_blocked = section_text.strip().upper() == "BLOCKED" or (
        _is_access_denied(section_text) and not _is_not_found(section_text)
    )

    if ai_says_blocked:
        check.could_access = False
        check.match_score = 0.0
        return check

    # Any substantive response means the AI accessed the page
    if len(section_text.strip()) > 20:
        check.could_access = True
        check.match_score = 1.0
    else:
        check.could_access = None

    return check


def _calculate_provider_score(checks: list[AIVerifyCheck]) -> tuple[float, str]:
    """Calculate access score (0-10) and overall access status for a provider.

    Scoring:
    - robots.txt accessible: 2 pts
    - VDP data match (price or VIN): 3 pts
    - Inventory browsable: 3 pts
    - Sitemap accessible: 2 pts

    Access classification:
    - "full": Provider retrieved real data from key pages (inventory/VDP)
    - "partial": Provider reached the site but couldn't get deep data
    - "blocked": Provider was blocked from the site entirely
    """
    score = 0.0
    checks_accessible = 0
    checks_blocked = 0
    key_checks_with_data = 0  # inventory/vdp with match_score >= 0.5

    for check in checks:
        if not check.could_access:
            pass
        elif check.check_type == "robots":
            # Weight by data quality — "NOT FOUND" (match=0) gets minimal credit
            score += 2.0 * max(0.3, check.match_score)
        elif check.check_type in ("vdp_price", "vdp_vin"):
            score += check.match_score * 1.5
        elif check.check_type == "inventory":
            score += 3.0 * max(0.3, check.match_score)
        elif check.check_type == "sitemap":
            score += 2.0 * max(0.3, check.match_score)
        elif check.check_type == "homepage":
            score += 1.0

        if check.could_access is True:
            checks_accessible += 1
            # Track if key checks (inventory, VDP) have real vehicle data
            if check.check_type in ("inventory", "vdp_price", "vdp_vin"):
                if check.match_score >= 0.6:
                    key_checks_with_data += 1
        elif check.could_access is False:
            checks_blocked += 1

    total_checks = checks_accessible + checks_blocked
    if total_checks == 0:
        access = "unknown"
    elif checks_accessible == 0:
        access = "blocked"
    elif checks_blocked > 0 and checks_accessible > 0:
        access = "partial"
    elif key_checks_with_data >= 1:
        # Provider retrieved real inventory/VDP data — true full access
        access = "full"
    elif checks_accessible > 0:
        # Reached the site (homepage, etc.) but no real inventory/VDP data
        access = "partial"
    else:
        access = "unknown"

    return min(10.0, round(score, 1)), access


async def _verify_provider_v2(
    provider: str, prompt: str, domain: str = ""
) -> AIProviderVerificationV2:
    """Send the V2 prompt to a single provider and get raw response."""
    result = AIProviderVerificationV2(provider_name=provider)

    try:
        if provider == "openai":
            text = await _call_openai(prompt)
        elif provider == "kimi":
            text = await _call_kimi(prompt)
        elif provider == "gemini":
            text = await _call_gemini(prompt, domain=domain)
        elif provider == "anthropic":
            text = await _call_claude(prompt)
        elif provider == "perplexity":
            text = await _call_perplexity(prompt)
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

    # gpt-4o-mini has web access but is inconsistent — retry once if blocked
    for attempt in range(2):
        response = await asyncio.wait_for(
            client.responses.create(
                model="gpt-4o-mini",
                tools=[{"type": "web_search"}],
                input=prompt,
            ),
            timeout=settings.ai_verify_timeout,
        )
        text = response.output_text
        if attempt == 0 and _is_access_denied(text):
            logger.info("OpenAI first attempt returned access denied, retrying...")
            continue
        return text
    return text  # return last attempt regardless


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


_GEMINI_PROMPT = (
    "Search for information about the car dealership at {domain}.\n\n"
    "1. HOMEPAGE: What is the dealership name and what brands do they sell?\n\n"
    "2. ROBOTS: Fetch https://{domain}/robots.txt\n"
    "   Return the first 5 lines of text exactly as they appear.\n\n"
    "3. INVENTORY: Find vehicle inventory listings on the site.\n"
    "   Return the names and prices of the first 3 vehicles.\n\n"
    "4. SITEMAP: Fetch https://{domain}/sitemap.xml\n"
    "   Return the total number of URLs and the first 3.\n\n"
    "IMPORTANT: For each section, respond with one of:\n"
    "- The requested data if found\n"
    '- "NOT FOUND" if the page does not exist\n'
    '- "BLOCKED" if you cannot reach the server\n\n'
    "HOMEPAGE:\nROBOTS:\nINVENTORY:\nSITEMAP:"
)


async def _call_gemini(prompt: str, domain: str = "") -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.gemini_api_key)
    # Use Gemini-specific prompt that works with url_context
    # (full discovery prompt with VDP causes 500 errors)
    gemini_prompt = _GEMINI_PROMPT.format(domain=domain) if domain else prompt
    response = await asyncio.wait_for(
        client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=gemini_prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(url_context=types.UrlContext())],
            ),
        ),
        timeout=max(settings.ai_verify_timeout, 90.0),
    )
    return response.text or ""


async def _call_perplexity(prompt: str) -> str:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        api_key=settings.perplexity_api_key,
        base_url="https://api.perplexity.ai",
    )
    response = await asyncio.wait_for(
        client.chat.completions.create(
            model="sonar-pro",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a web research assistant. Use your web search "
                        "capabilities to find information from the URLs provided. "
                        "Search for the specific pages and return the data requested."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        ),
        timeout=settings.ai_verify_timeout,
    )
    return response.choices[0].message.content or ""


async def _call_claude(prompt: str) -> str:
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await asyncio.wait_for(
        client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            tools=[{"type": "web_search_20250305"}],
            messages=[{"role": "user", "content": prompt}],
        ),
        timeout=settings.ai_verify_timeout,
    )
    return "".join(block.text for block in response.content if hasattr(block, "text"))


class AILiveVerifyDetectorV2:
    """V2: Multi-page AI verification with ground truth comparison and scoring."""

    def __init__(
        self,
        domain: str,
        ground_truth: GroundTruthResult,
        discovery_mode: bool = False,
    ) -> None:
        self.domain = domain
        self.ground_truth = ground_truth
        self.discovery_mode = discovery_mode

    async def verify(self) -> AILiveVerifyResultV2:
        """Run V2 verification against all configured providers."""
        # Use canonical domain from ground truth (resolves www vs non-www)
        domain = self.ground_truth.domain or self.domain

        if self.discovery_mode:
            prompt = _DISCOVERY_PROMPT.format(domain=domain)
        else:
            prompt = _build_v2_prompt(domain, self.ground_truth)

        # Launch all providers in parallel (including Claude)
        tasks: list[tuple[str, asyncio.Task]] = []
        if settings.openai_api_key:
            tasks.append(("openai", asyncio.create_task(_verify_provider_v2("openai", prompt))))
        if settings.gemini_api_key:
            tasks.append(("gemini", asyncio.create_task(
                _verify_provider_v2("gemini", prompt, domain=domain)
            )))
        if settings.perplexity_api_key:
            tasks.append(
                ("perplexity", asyncio.create_task(_verify_provider_v2("perplexity", prompt)))
            )
        elif settings.kimi_api_key:
            tasks.append(("kimi", asyncio.create_task(_verify_provider_v2("kimi", prompt))))
        if settings.anthropic_api_key:
            tasks.append(
                ("anthropic", asyncio.create_task(_verify_provider_v2("anthropic", prompt)))
            )

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
        full_count = sum(1 for p in providers if p.overall_access == "full")
        partial_count = sum(1 for p in providers if p.overall_access == "partial")
        blocked_count = sum(1 for p in providers if p.overall_access == "blocked")
        total_count = len([p for p in providers if p.overall_access != "error"])

        if self.discovery_mode:
            if full_count == total_count and total_count > 0:
                summary = (
                    f"All {total_count} AI providers have full access to your site "
                    "— only our test server is blocked (datacenter IP block)"
                )
            elif full_count > 0 and (partial_count > 0 or blocked_count > 0):
                full_names = ", ".join(
                    p.provider_name for p in providers if p.overall_access == "full"
                )
                summary = (
                    f"Only {full_names} can fully access your inventory — "
                    f"{partial_count + blocked_count} other AI provider(s) have "
                    "limited or no access (narrow AI whitelist detected)"
                )
            elif partial_count > 0 and full_count == 0:
                summary = (
                    f"{partial_count} AI providers can reach your homepage but none can "
                    "access inventory or vehicle details"
                )
            else:
                summary = (
                    f"0 of {total_count} AI providers can access your site "
                    "— site appears to block AI access"
                )
        else:
            accessible_count = full_count + partial_count
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

        # In discovery mode, ground truth is unreliable (our server was blocked).
        # Use an empty GT so check functions use discovery-mode scoring.
        if self.discovery_mode:
            gt = GroundTruthResult(domain=self.ground_truth.domain)
        else:
            gt = self.ground_truth

        # Parse each section
        homepage_text = _parse_section(text, "HOMEPAGE")
        robots_text = _parse_section(text, "ROBOTS")
        inventory_text = _parse_section(text, "INVENTORY")
        vdp_text = _parse_section(text, "VDP")
        sitemap_text = _parse_section(text, "SITEMAP")

        if homepage_text:
            checks.append(_check_homepage_response(homepage_text))

        if robots_text:
            checks.append(_check_robots_response(robots_text, gt))

        if inventory_text:
            checks.append(_check_inventory_response(inventory_text, gt))

        if vdp_text:
            checks.append(_check_vdp_response(vdp_text, gt, "vdp_price"))
            checks.append(_check_vdp_response(vdp_text, gt, "vdp_vin"))

        if sitemap_text:
            checks.append(_check_sitemap_response(sitemap_text, gt))

        return checks
