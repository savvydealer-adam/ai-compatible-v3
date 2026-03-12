"""Recommendation engine based on analysis issues."""

from server.models.responses import Issue


def generate_recommendations(issues: list[Issue], analysis: dict) -> list[str]:
    """Generate prioritized recommendations from issues."""
    recs: list[str] = []

    # Priority 1: Whitelist blocking
    has_whitelist = any(
        "WHITELIST" in i.message.upper() for i in issues if i.severity == "critical"
    )
    if has_whitelist:
        recs.append(
            "CRITICAL: Remove bot-specific blocking (whitelist detected). "
            "Your site allows some AI crawlers but blocks others, creating a default-deny pattern. "
            "Allow all AI crawlers for maximum visibility."
        )

    # Priority 1.5: Narrow whitelist warning
    has_narrow_whitelist = any(
        "narrow ai whitelist" in i.message.lower() for i in issues
    )
    if has_narrow_whitelist:
        # Build specific provider list from issues
        blocked_names = []
        for i in issues:
            if "narrow ai whitelist" in i.message.lower():
                # Extract blocked names from "Narrow AI whitelist: X allowed, Y, Z blocked"
                if "blocked" in i.message:
                    parts = i.message.split("blocked")[0]
                    if "," in parts:
                        after_comma = parts.rsplit(",", 1)[-1].strip()
                        blocked_names.append(after_comma)
        recs.append(
            "Your site uses a narrow AI whitelist — only select providers (likely OpenAI/ChatGPT) "
            "can access your inventory, while other major AI platforms including Google Gemini "
            "and Perplexity are blocked. This severely limits your dealership's visibility. "
            "As AI-powered car shopping grows, being invisible to most AI platforms "
            "means losing potential buyers who use those services to research vehicles."
        )

    # Priority 1.5: DC IP block (not a critical AI block)
    has_dc_block = any(
        "datacenter ips" in i.message.lower() for i in issues
    )
    if has_dc_block and not has_whitelist:
        recs.append(
            "Your site blocks datacenter IPs, which affects automated testing "
            "but does not block major AI providers. Consider allowing datacenter "
            "access so third-party tools can audit your AI compatibility."
        )

    # Priority 1/2: Critical blocking issues (true AI blocks only)
    blocking_criticals = [
        i
        for i in issues
        if i.severity == "critical"
        and i.category == "blocking"
        and "WHITELIST" not in i.message.upper()
    ]
    if blocking_criticals:
        msgs = [i.recommendation or i.message for i in blocking_criticals[:3]]
        recs.append(f"Fix critical blocking issues: {'; '.join(msgs)}")

    # Priority 2: Robots.txt issues
    robots_issues = [i for i in issues if "robots.txt" in i.message.lower()]
    if robots_issues:
        recs.append(
            "Update robots.txt to allow AI crawlers. "
            "Remove Disallow: / for GPTBot, Claude-Web, PerplexityBot, and Google-Extended."
        )

    # Priority 3: Structured data
    schema_issues = [
        i for i in issues if i.category == "structured_data" and i.severity == "warning"
    ]
    if schema_issues:
        missing = []
        if any("dealer schema" in i.message.lower() for i in schema_issues):
            missing.append("AutoDealer/LocalBusiness on homepage")
        if any(
            "itemlist" in i.message.lower() or "inventory" in i.message.lower()
            for i in schema_issues
        ):
            missing.append("ItemList on inventory page")
        if any(
            "vehicle schema" in i.message.lower() or "vdp" in i.message.lower()
            for i in schema_issues
        ):
            missing.append("Vehicle/Car schema on VDP")
        if missing:
            recs.append(f"Add structured data (JSON-LD): {', '.join(missing)}")

    # Priority 4: Discoverability
    discover_issues = [i for i in issues if i.category == "discoverability"]
    if discover_issues:
        recs.append(
            "Improve discoverability: add an XML sitemap with vehicle URLs, "
            "ensure meta tags are complete, and add Open Graph tags."
        )

    # Priority 5: Cloudflare Markdown for Agents
    cf_present = analysis.get("cloudflare_present", False) or analysis.get("base_analysis", {}).get(
        "cloudflare_detected", False
    )
    md_supported = analysis.get("markdown_for_agents", {}).get(
        "markdown_supported", False
    ) or analysis.get("markdown_for_agents", {}).get("available", False)
    if cf_present and not md_supported:
        recs.append(
            "Enable Cloudflare Markdown for Agents to provide clean, "
            "structured content to AI systems."
        )

    # Priority 6: noai directives (new in v3)
    noai_issues = [i for i in issues if "noai" in i.message.lower()]
    if noai_issues:
        recs.append(
            "Remove noai/noimageai meta directives to allow AI systems to access your content."
        )

    # Fallback
    if not recs:
        recs.append("Maintain current AI-friendly configuration. Your site scores well!")

    return recs
