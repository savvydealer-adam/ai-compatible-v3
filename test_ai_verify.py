"""Local test harness for AI Live Verification.

Usage:
    python test_ai_verify.py alanjaykia.com
    python test_ai_verify.py alanjaykia.com --provider openai
    python test_ai_verify.py alanjaykia.com --provider gemini
    python test_ai_verify.py alanjaykia.com --provider perplexity
    python test_ai_verify.py alanjaykia.com --provider all
"""

import argparse
import asyncio
import os
import re
import sys
import time

# Load .env before importing server modules
from dotenv import load_dotenv
load_dotenv()

from server.config import settings
from server.detectors.ai_live_verify import (
    _DISCOVERY_PROMPT,
    _GEMINI_PROMPT,
    _call_openai,
    _call_gemini,
    _call_perplexity,
    _check_homepage_response,
    _check_inventory_response,
    _check_robots_response,
    _check_sitemap_response,
    _check_vdp_response,
    _calculate_provider_score,
    _parse_section,
    _extract_price,
    _extract_vin,
)
from server.models.schemas import GroundTruthResult, GroundTruthPage


def make_empty_ground_truth(domain: str) -> GroundTruthResult:
    """Empty GT for discovery mode — no page stubs since our server was blocked."""
    return GroundTruthResult(
        domain=domain,
        source="test_harness",
        pages=[],
    )


PROVIDERS = {
    "openai": (_call_openai, settings.openai_api_key),
    "gemini": (_call_gemini, settings.gemini_api_key),
    "perplexity": (_call_perplexity, settings.perplexity_api_key),
}

# Add claude if key exists
try:
    from server.detectors.ai_live_verify import _call_claude
    if settings.anthropic_api_key:
        PROVIDERS["anthropic"] = (_call_claude, settings.anthropic_api_key)
except ImportError:
    pass


async def test_provider(name: str, call_fn, prompt: str, ground_truth: GroundTruthResult, domain: str = ""):
    """Test a single provider and print detailed results."""
    print(f"\n{'='*70}")
    print(f"  PROVIDER: {name.upper()}")
    print(f"{'='*70}")

    # Call the provider
    start = time.time()
    try:
        if name == "gemini":
            raw_text = await asyncio.wait_for(call_fn(prompt, domain=domain), timeout=max(settings.ai_verify_timeout, 90.0))
        else:
            raw_text = await asyncio.wait_for(call_fn(prompt), timeout=settings.ai_verify_timeout)
        elapsed = time.time() - start
        print(f"\n  Response time: {elapsed:.1f}s")
        print(f"  Response length: {len(raw_text)} chars")
    except asyncio.TimeoutError:
        elapsed = time.time() - start
        print(f"\n  TIMEOUT after {elapsed:.1f}s (limit: {settings.ai_verify_timeout}s)")
        return
    except Exception as e:
        elapsed = time.time() - start
        print(f"\n  ERROR ({type(e).__name__}): {e}")
        return

    # Show raw response
    print(f"\n  --- RAW RESPONSE ---")
    for line in raw_text.splitlines():
        print(f"  | {line}")

    # Parse sections
    print(f"\n  --- PARSED SECTIONS ---")
    sections = {}
    for section_name in ["HOMEPAGE", "ROBOTS", "INVENTORY", "VDP", "SITEMAP"]:
        text = _parse_section(raw_text, section_name)
        sections[section_name] = text
        status = f"{len(text)} chars" if text else "EMPTY"
        preview = text[:80].replace('\n', ' ') if text else ""
        print(f"  {section_name:12s}: [{status}] {preview}")

    # Run checks
    print(f"\n  --- CHECK RESULTS ---")
    checks = []

    if sections["HOMEPAGE"]:
        check = _check_homepage_response(sections["HOMEPAGE"])
        checks.append(check)
        _print_check(check)

    if sections["ROBOTS"]:
        check = _check_robots_response(sections["ROBOTS"], ground_truth)
        checks.append(check)
        _print_check(check)

    if sections["INVENTORY"]:
        check = _check_inventory_response(sections["INVENTORY"], ground_truth)
        checks.append(check)
        _print_check(check)

    if sections["VDP"]:
        check_price = _check_vdp_response(sections["VDP"], ground_truth, "vdp_price")
        check_vin = _check_vdp_response(sections["VDP"], ground_truth, "vdp_vin")
        checks.extend([check_price, check_vin])
        _print_check(check_price)
        _print_check(check_vin)

    if sections["SITEMAP"]:
        check = _check_sitemap_response(sections["SITEMAP"], ground_truth)
        checks.append(check)
        _print_check(check)

    # Calculate score
    score, access = _calculate_provider_score(checks)
    print(f"\n  --- FINAL RESULT ---")
    print(f"  Access Score: {score}/10")
    print(f"  Classification: {access.upper()}")

    # Debug: show key_checks_with_data count
    key_checks = [c for c in checks if c.check_type in ("inventory", "vdp_price", "vdp_vin")]
    key_good = [c for c in key_checks if c.could_access is True and c.match_score >= 0.5]
    print(f"  Key checks with data (>=0.5): {len(key_good)}/{len(key_checks)}")

    accessible = sum(1 for c in checks if c.could_access is True)
    blocked = sum(1 for c in checks if c.could_access is False)
    print(f"  Accessible: {accessible}, Blocked: {blocked}, None: {len(checks) - accessible - blocked}")

    # Data extraction
    inv_text = sections.get("INVENTORY", "")
    vdp_text = sections.get("VDP", "")
    if inv_text or vdp_text:
        print(f"\n  --- DATA FOUND ---")
        prices = re.findall(r"\$[\d,]+(?:\.\d{2})?", inv_text + " " + vdp_text)
        vins = re.findall(r"[A-HJ-NPR-Z0-9]{17}", inv_text + " " + vdp_text, re.I)
        years = re.findall(r"20\d{2}\s+\w+\s+\w+", inv_text + " " + vdp_text)
        if prices:
            print(f"  Prices: {prices[:5]}")
        if vins:
            print(f"  VINs: {vins[:3]}")
        if years:
            print(f"  Vehicles: {years[:5]}")


def _print_check(check):
    access_str = {True: "YES", False: "NO", None: "N/A"}.get(check.could_access, "?")
    print(
        f"  {check.check_type:12s}: "
        f"access={access_str:3s}  "
        f"match={check.match_score:.2f}  "
        f"data={check.data_returned[:60] if check.data_returned else '-'}"
    )


async def main():
    parser = argparse.ArgumentParser(description="Test AI Live Verification locally")
    parser.add_argument("domain", help="Domain to test (e.g. alanjaykia.com)")
    parser.add_argument("--provider", "-p", default="all",
                        help="Provider to test: openai, gemini, perplexity, anthropic, all")
    parser.add_argument("--timeout", "-t", type=float, default=None,
                        help="Override timeout in seconds")
    args = parser.parse_args()

    domain = args.domain.replace("https://", "").replace("http://", "").rstrip("/")

    if args.timeout:
        settings.ai_verify_timeout = args.timeout

    # Show config
    print(f"Domain: {domain}")
    print(f"Timeout: {settings.ai_verify_timeout}s")
    print(f"API Keys configured:")
    for name, (_, key) in PROVIDERS.items():
        print(f"  {name}: {'YES' if key else 'NO'}")

    # Build prompt
    prompt = _DISCOVERY_PROMPT.format(domain=domain)
    print(f"\nPrompt length: {len(prompt)} chars")

    # Build empty ground truth (simulates DC-blocked site)
    gt = make_empty_ground_truth(domain)

    # Run providers
    if args.provider == "all":
        providers_to_test = [(n, fn) for n, (fn, key) in PROVIDERS.items() if key]
    else:
        if args.provider not in PROVIDERS:
            print(f"Unknown provider: {args.provider}")
            print(f"Available: {', '.join(PROVIDERS.keys())}")
            sys.exit(1)
        fn, key = PROVIDERS[args.provider]
        if not key:
            print(f"No API key for {args.provider}")
            sys.exit(1)
        providers_to_test = [(args.provider, fn)]

    for name, call_fn in providers_to_test:
        await test_provider(name, call_fn, prompt, gt, domain=domain)

    print(f"\n{'='*70}")
    print("  DONE")
    print(f"{'='*70}")


if __name__ == "__main__":
    asyncio.run(main())
