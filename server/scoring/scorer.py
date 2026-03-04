"""AI Compatibility scoring engine — faithfully ported from v2."""

import logging

from server.data.bot_user_agents import KEY_AI_BOTS, VEHICLE_SCHEMA_TYPES
from server.models.responses import CategoryScore, Issue, ScoreResponse

logger = logging.getLogger(__name__)

GRADE_LABELS = {
    "A+": "Exceptional AI Compatibility",
    "A": "Excellent AI Compatibility",
    "B": "Good - Minor improvements needed",
    "C": "Fair - Significant gaps",
    "D": "Poor - Major issues",
    "F": "AI Hostile - Needs immediate attention",
}


class AICompatibilityScorer:
    """Score a website's AI compatibility (100-point scale)."""

    def score(self, analysis: dict) -> tuple[ScoreResponse, list[Issue]]:
        """Calculate full score from analysis results."""
        issues: list[Issue] = []
        site_blocked = analysis.get("site_blocked", False)

        # Calculate blocking multiplier
        multiplier = self._blocking_multiplier(analysis)

        # Category scores
        blocking_score, blocking_details = self._score_blocking(analysis, issues)
        structured_score, structured_details = self._score_structured_data(analysis, issues)
        discover_score, discover_details = self._score_discoverability(analysis, issues)

        # Apply blocking multiplier to non-blocking categories
        if site_blocked:
            structured_score = 0
            structured_details.append("Zeroed: site is blocked")
            discover_score = 0
            discover_details.append("Zeroed: site is blocked")
        elif multiplier < 1.0:
            structured_score = int(structured_score * multiplier)
            discover_score = int(discover_score * multiplier)
            if multiplier < 0.5:
                structured_details.append(
                    f"Reduced by {int((1 - multiplier) * 100)}% due to blocking"
                )
                discover_details.append(
                    f"Reduced by {int((1 - multiplier) * 100)}% due to blocking"
                )

        # Clamp category scores
        blocking_score = max(0, min(blocking_score, 25))
        structured_score = max(0, min(structured_score, 60))
        discover_score = max(0, min(discover_score, 15))

        total = max(0, blocking_score + structured_score + discover_score)
        grade = self._get_grade(total)

        return ScoreResponse(
            total_score=total,
            max_score=100,
            grade=grade,
            grade_label=GRADE_LABELS.get(grade, ""),
            categories=[
                CategoryScore(
                    name="Blocking Prevention",
                    score=blocking_score,
                    max_score=25,
                    details=blocking_details,
                ),
                CategoryScore(
                    name="Structured Data",
                    score=structured_score,
                    max_score=60,
                    details=structured_details,
                ),
                CategoryScore(
                    name="Discoverability",
                    score=discover_score,
                    max_score=15,
                    details=discover_details,
                ),
            ],
            bonus_points=0,
        ), issues

    def _blocking_multiplier(self, analysis: dict) -> float:
        """Calculate multiplier for structured data / discoverability based on blocking severity."""
        if analysis.get("site_blocked"):
            return 0.0

        base = analysis.get("base_analysis", {})
        if base.get("js_challenge") or base.get("captcha_detected"):
            return 0.3

        # Count blocked bots
        bots = analysis.get("ai_bots", {})
        robots = bots.get("robots_analysis", {})
        access = bots.get("access_test", {})

        robots_blocked = robots.get("ai_bots_blocked_count", 0)
        access_blocked = len(access.get("bots_blocked", []))
        total_blocked = max(robots_blocked, access_blocked)

        if total_blocked >= 4:
            return 0.2
        if total_blocked >= 3:
            return 0.4
        if total_blocked >= 1:
            return 0.7
        return 1.0

    def _score_blocking(self, analysis: dict, issues: list[Issue]) -> tuple[int, list[str]]:
        """Score blocking prevention (max 25 points)."""
        score = 0
        details: list[str] = []
        base = analysis.get("base_analysis", {})
        bots = analysis.get("ai_bots", {})
        robots = bots.get("robots_analysis", {})
        access = bots.get("access_test", {})

        # Site fully blocked — capped at 2-5 points
        if analysis.get("site_blocked"):
            has_cf = base.get("cloudflare_detected", False)
            has_403 = base.get("forbidden_access", False)
            has_js = base.get("js_challenge", False)
            if has_cf or has_403 or has_js:
                score = 2
                details.append("Site blocked (+2)")
            else:
                score = 5
                details.append("Site partially blocked (+5)")
            issues.append(
                Issue(
                    severity="critical",
                    category="blocking",
                    message="Site is blocked to AI crawlers",
                )
            )
            return score, details

        # A. Robots.txt AI bot permissions (max 10)
        bot_permissions = robots.get("bot_permissions", {})
        for bot in KEY_AI_BOTS:
            perm = bot_permissions.get(bot, "not_specified")
            if perm != "blocked":
                score += 2
                details.append(f"{bot}: allowed (+2)")
            else:
                issues.append(
                    Issue(
                        severity="critical",
                        category="blocking",
                        message=f"{bot} is blocked in robots.txt",
                        recommendation=f"Remove Disallow: / for {bot} in robots.txt",
                    )
                )

        # B. WAF / Accessibility (max 7)
        resp_code = base.get("response_code")
        if resp_code == 200:
            score += 3
            details.append("Homepage accessible (+3)")

        bot_protection = analysis.get("bot_protection", {})
        if not bot_protection.get("bot_protection_detected", False):
            score += 2
            details.append("No bot protection (+2)")
        else:
            issues.append(
                Issue(
                    severity="warning",
                    category="blocking",
                    message=(
                        "Bot protection detected: "
                        f"{bot_protection.get('protection_type', 'Unknown')}"
                    ),
                )
            )

        if not base.get("forbidden_access", False):
            score += 2
            details.append("No 403 Forbidden (+2)")

        # C. Bot access test (starts at 5, can go to -15)
        bots_blocked = access.get("bots_blocked", [])
        bots_allowed = access.get("bots_allowed", [])
        num_blocked = len(bots_blocked)
        num_allowed = len(bots_allowed)
        # Unknown = total - blocked - allowed
        total_bots = len(access.get("bot_access_results", {}))
        num_unknown = max(0, total_bots - num_blocked - num_allowed)

        if num_blocked == 0 and num_unknown == 0:
            bot_access_score = 5
            details.append("All bots have access (+5)")
        else:
            blocked_penalty = num_blocked * -3
            unknown_penalty = num_unknown * -2
            # Whitelist detection: some allowed + some blocked = selective blocking
            has_whitelist = num_allowed >= 2 and num_blocked >= 2
            whitelist_penalty = -8 if has_whitelist else 0
            bot_access_score = max(-15, 5 + blocked_penalty + unknown_penalty + whitelist_penalty)

            if has_whitelist:
                issues.append(
                    Issue(
                        severity="critical",
                        category="blocking",
                        message=(
                            f"WHITELIST detected: {num_allowed} bots allowed, {num_blocked} blocked"
                        ),
                        recommendation="Remove bot-specific blocking or allow all AI crawlers",
                    )
                )
                details.append(f"Whitelist blocking ({bot_access_score})")
            elif num_blocked > 0:
                details.append(f"{num_blocked} bots blocked ({bot_access_score})")

        score += bot_access_score

        # D. Rate limiting (max 2, or -8 penalty)
        if not base.get("rate_limited", False):
            score += 2
            details.append("No rate limiting (+2)")
        else:
            score -= 8
            details.append("Rate limited (-8)")
            issues.append(
                Issue(severity="critical", category="blocking", message="Rate limiting detected")
            )

        # E. Crawl delay penalties
        delay_tier = robots.get("crawl_delay_tier", "friendly")
        delay_penalties = {"friendly": 0, "moderate": -0.5, "slow": -1, "excessive": -2}
        penalty = delay_penalties.get(delay_tier, 0)
        if penalty:
            score += penalty
            details.append(f"Crawl delay {delay_tier} ({penalty})")

        # F. JS Challenge
        if base.get("js_challenge"):
            score -= 3
            details.append("JS challenge (-3)")

        # G. No datacenter blocking
        if not base.get("datacenter_blocked", False):
            score += 1
            details.append("No IP blocking (+1)")

        return score, details

    def _score_structured_data(self, analysis: dict, issues: list[Issue]) -> tuple[int, list[str]]:
        """Score structured data (max 60 points)."""
        score = 0
        details: list[str] = []
        homepage_ld = analysis.get("homepage_json_ld", {})
        inv_page = analysis.get("inventory_page", {})
        vdp_page = analysis.get("vdp_page", {})

        # A. Homepage JSON-LD (max 18)
        if homepage_ld.get("has_dealer_schema"):
            score += 10
            details.append("Dealer schema found (+10)")
        else:
            issues.append(
                Issue(
                    severity="warning",
                    category="structured_data",
                    message="No dealer schema (LocalBusiness/AutoDealer) on homepage",
                    recommendation="Add JSON-LD with @type AutoDealer or LocalBusiness",
                )
            )

        # Schema completeness
        best_completeness = 0
        for detail in homepage_ld.get("schema_details", []):
            cs = detail.get("completeness_score", 0)
            if cs > best_completeness:
                best_completeness = cs
        if best_completeness >= 70:
            score += 5
            details.append(f"Schema completeness {best_completeness}% (+5)")

        # Valid JSON-LD
        if homepage_ld.get("json_ld_found") and not homepage_ld.get("validation_errors"):
            score += 3
            details.append("Valid JSON-LD (+3)")

        # B. Inventory page (max 18)
        if inv_page.get("inventory_found", False):
            score += 2
            details.append("Inventory page found (+2)")

            if inv_page.get("has_itemlist_schema", False):
                score += 10
                details.append("ItemList/OfferCatalog schema (+10)")
            else:
                issues.append(
                    Issue(
                        severity="warning",
                        category="structured_data",
                        message="No ItemList/OfferCatalog schema on inventory page",
                    )
                )

            # Vehicle count scoring
            vehicle_count = self._get_vehicle_count(inv_page)
            if vehicle_count >= 10:
                score += 6
                details.append(f"{vehicle_count} vehicles listed (+6)")
            elif vehicle_count >= 1:
                score += 2
                details.append(f"{vehicle_count} vehicles listed (+2)")
        else:
            issues.append(
                Issue(
                    severity="warning",
                    category="structured_data",
                    message="No inventory page found",
                )
            )

        # C. VDP (max 18)
        if vdp_page.get("vdp_found", False):
            score += 2
            details.append("VDP found (+2)")

            if vdp_page.get("has_vehicle_schema", False):
                score += 9
                details.append("Vehicle schema on VDP (+9)")
            else:
                issues.append(
                    Issue(
                        severity="warning",
                        category="structured_data",
                        message="No vehicle schema on VDP",
                    )
                )

            # Check for price and VIN in schema
            for detail in vdp_page.get("vdp_json_ld", {}).get("schema_details", []):
                props = detail.get("properties_found", [])
                if "offers" in props or "price" in props:
                    score += 4
                    details.append("Price in schema (+4)")
                    break

            for detail in vdp_page.get("vdp_json_ld", {}).get("schema_details", []):
                props = detail.get("properties_found", [])
                if "vehicleIdentificationNumber" in props:
                    score += 3
                    details.append("VIN in schema (+3)")
                    break
        else:
            issues.append(
                Issue(
                    severity="warning",
                    category="structured_data",
                    message="No vehicle detail page found",
                )
            )

        # D. All schemas valid bonus (6 points)
        has_any = (
            homepage_ld.get("json_ld_found")
            or inv_page.get("has_itemlist_schema")
            or vdp_page.get("has_vehicle_schema")
        )
        all_valid = True
        for key in ("homepage_json_ld", "inventory_page", "vdp_page"):
            data = analysis.get(key, {})
            if data.get("validation_errors"):
                all_valid = False
                break

        if has_any and all_valid:
            score += 6
            details.append("All schemas valid (+6)")

        return score, details

    def _score_discoverability(self, analysis: dict, issues: list[Issue]) -> tuple[int, list[str]]:
        """Score discoverability (max 15 points)."""
        score = 0
        details: list[str] = []
        sitemap = analysis.get("sitemap", {})
        meta = analysis.get("meta_tags", {}).get("homepage", {})
        vdp = analysis.get("vdp_page", {})
        markdown = analysis.get("markdown_for_agents", {})

        # A. Sitemap (max 5)
        if sitemap.get("sitemap_found"):
            score += 2
            details.append("Sitemap found (+2)")
            if sitemap.get("has_vehicle_urls"):
                score += 2
                details.append("Vehicle URLs in sitemap (+2)")
            if sitemap.get("sitemap_fresh"):
                score += 1
                details.append("Sitemap fresh (+1)")
        else:
            issues.append(
                Issue(
                    severity="warning",
                    category="discoverability",
                    message="No sitemap found",
                    recommendation="Add an XML sitemap at /sitemap.xml",
                )
            )

        # B. Meta tags (max 5)
        if meta.get("title"):
            score += 1
            details.append("Title tag (+1)")
        if meta.get("meta_description") or meta.get("description"):
            score += 2
            details.append("Meta description (+2)")
        if meta.get("canonical_valid") or meta.get("canonical"):
            score += 1
            details.append("Canonical URL (+1)")
        if meta.get("has_og_tags") or meta.get("og_title") or meta.get("og_description"):
            score += 1
            details.append("Open Graph tags (+1)")

        # C. Content & Headers (max 5)
        content_html = vdp.get("content_in_html", {})
        if content_html.get("price_visible") or content_html.get("vin_visible"):
            score += 3
            details.append("Price/VIN visible in HTML (+3)")

        # X-Robots-Tag blocking check
        x_robots_blocked = False
        for key in ("homepage", "inventory", "vdp"):
            xr = analysis.get("x_robots", {}).get(key, {})
            if xr.get("x_robots_noindex") or xr.get("x_robots_noai"):
                x_robots_blocked = True
                issues.append(
                    Issue(
                        severity="warning",
                        category="discoverability",
                        message=f"X-Robots-Tag blocking on {key} page",
                    )
                )
        if not x_robots_blocked:
            score += 2
            details.append("No X-Robots-Tag blocking (+2)")

        # D. Markdown for Agents bonus (2 points)
        if markdown.get("markdown_supported") or markdown.get("available"):
            score += 2
            details.append("Markdown for Agents (+2)")

        # E. llms.txt bonus (1 point, new in v3)
        llms = analysis.get("llms_txt", {})
        if llms.get("found"):
            score += 1
            details.append("llms.txt found (+1)")

        # F. FAQPage schema bonus (3 points, new in v3)
        faq = analysis.get("faq_schema", {})
        if faq.get("found"):
            score += 3
            details.append("FAQPage schema (+3)")

        return score, details

    @staticmethod
    def _get_vehicle_count(inv_page: dict) -> int:
        """Get vehicle count from inventory page data."""
        # Try schema-based count first
        schema_details = inv_page.get("inventory_json_ld", {}).get("schema_details", [])
        jsonld_count = 0
        for detail in schema_details:
            schema_type = detail.get("type", "")
            if schema_type in VEHICLE_SCHEMA_TYPES or schema_type == "Offer":
                jsonld_count += 1
            elif schema_type == "ItemList":
                raw = detail.get("raw_data", {})
                items = raw.get("itemListElement", [])
                jsonld_count += len(items)

        if jsonld_count > 0:
            return jsonld_count
        return inv_page.get("vehicle_count_estimate", inv_page.get("vehicle_count", 0))

    @staticmethod
    def _get_grade(score: int) -> str:
        if score >= 95:
            return "A+"
        if score >= 90:
            return "A"
        if score >= 80:
            return "B"
        if score >= 70:
            return "C"
        if score >= 60:
            return "D"
        return "F"
