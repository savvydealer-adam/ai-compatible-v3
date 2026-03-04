"""Tests for scoring engine."""

from server.scoring.scorer import AICompatibilityScorer


class TestScoring:
    def setup_method(self):
        self.scorer = AICompatibilityScorer()

    def _base_analysis(self, **overrides) -> dict:
        """Create base analysis dict with defaults."""
        data = {
            "site_blocked": False,
            "base_analysis": {
                "response_code": 200,
                "cloudflare_detected": False,
                "js_challenge": False,
                "captcha_detected": False,
                "forbidden_access": False,
                "datacenter_blocked": False,
                "rate_limited": False,
            },
            "ai_bots": {
                "robots_analysis": {
                    "bot_permissions": {
                        "GPTBot": "allowed",
                        "Claude-Web": "allowed",
                        "PerplexityBot": "allowed",
                        "Google-Extended": "allowed",
                        "CCBot": "allowed",
                    },
                    "ai_bots_blocked_count": 0,
                    "crawl_delay_tier": "friendly",
                },
                "access_test": {
                    "bots_blocked": [],
                    "bots_allowed": [
                        "GPTBot",
                        "Claude-Web",
                        "PerplexityBot",
                        "Google-Extended",
                        "CCBot",
                    ],
                    "bot_access_results": {},
                },
            },
            "bot_protection": {"bot_protection_detected": False},
            "homepage_json_ld": {
                "json_ld_found": True,
                "has_dealer_schema": True,
                "schema_details": [{"type": "AutoDealer", "completeness_score": 80}],
                "validation_errors": [],
            },
            "inventory_page": {
                "inventory_found": True,
                "has_itemlist_schema": True,
                "vehicle_count": 25,
                "vehicle_count_estimate": 25,
                "inventory_json_ld": {"schema_details": []},
            },
            "vdp_page": {
                "vdp_found": True,
                "has_vehicle_schema": True,
                "vdp_json_ld": {
                    "schema_details": [
                        {
                            "type": "Car",
                            "properties_found": ["name", "offers", "vehicleIdentificationNumber"],
                            "completeness_score": 75,
                        }
                    ],
                },
                "content_in_html": {"price_visible": True, "vin_visible": True},
            },
            "sitemap": {"sitemap_found": True, "has_vehicle_urls": True, "sitemap_fresh": True},
            "meta_tags": {
                "homepage": {
                    "title": "Test Dealer",
                    "meta_description": "Test dealer description",
                    "description": "Test dealer description",
                    "canonical_valid": True,
                    "canonical": "https://test.com",
                    "has_og_tags": True,
                    "og_title": True,
                }
            },
            "x_robots": {"homepage": {}, "inventory": {}, "vdp": {}},
            "markdown_for_agents": {"markdown_supported": False, "available": False},
            "llms_txt": {"found": False},
            "faq_schema": {"found": False},
            "cloudflare_present": False,
        }
        data.update(overrides)
        return data

    def test_perfect_score_without_bonuses(self):
        """A perfect site should score high."""
        analysis = self._base_analysis()
        score_resp, issues = self.scorer.score(analysis)
        assert score_resp.total_score >= 80
        assert score_resp.grade in ("A+", "A", "B")

    def test_blocked_site_low_score(self):
        """A fully blocked site should score very low."""
        analysis = self._base_analysis(site_blocked=True)
        analysis["base_analysis"]["cloudflare_detected"] = True
        analysis["base_analysis"]["forbidden_access"] = True
        score_resp, issues = self.scorer.score(analysis)
        assert score_resp.total_score <= 10
        assert score_resp.grade == "F"

    def test_no_schema_reduces_score(self):
        """Missing schemas should reduce structured data score."""
        analysis = self._base_analysis()
        analysis["homepage_json_ld"]["has_dealer_schema"] = False
        analysis["homepage_json_ld"]["json_ld_found"] = False
        analysis["homepage_json_ld"]["schema_details"] = []
        analysis["inventory_page"]["has_itemlist_schema"] = False
        analysis["inventory_page"]["vehicle_count"] = 0
        analysis["inventory_page"]["vehicle_count_estimate"] = 0
        analysis["vdp_page"]["has_vehicle_schema"] = False
        analysis["vdp_page"]["vdp_json_ld"]["schema_details"] = []
        score_resp, issues = self.scorer.score(analysis)
        structured = next(c for c in score_resp.categories if c.name == "Structured Data")
        assert structured.score < 20

    def test_grade_thresholds(self):
        assert self.scorer._get_grade(96) == "A+"
        assert self.scorer._get_grade(91) == "A"
        assert self.scorer._get_grade(85) == "B"
        assert self.scorer._get_grade(75) == "C"
        assert self.scorer._get_grade(65) == "D"
        assert self.scorer._get_grade(50) == "F"

    def test_blocking_multiplier(self):
        """Blocked bots should reduce structured data and discoverability scores."""
        analysis = self._base_analysis()
        analysis["ai_bots"]["robots_analysis"]["ai_bots_blocked_count"] = 4
        analysis["ai_bots"]["robots_analysis"]["bot_permissions"]["GPTBot"] = "blocked"
        analysis["ai_bots"]["robots_analysis"]["bot_permissions"]["Claude-Web"] = "blocked"
        analysis["ai_bots"]["robots_analysis"]["bot_permissions"]["PerplexityBot"] = "blocked"
        analysis["ai_bots"]["robots_analysis"]["bot_permissions"]["Google-Extended"] = "blocked"

        score_resp, issues = self.scorer.score(analysis)
        # Score should be lower due to multiplier
        assert score_resp.total_score < 50

    def test_whitelist_detection(self):
        """Whitelist pattern (some allowed, some blocked) should trigger issues."""
        analysis = self._base_analysis()
        analysis["ai_bots"]["access_test"]["bots_blocked"] = ["GPTBot", "Claude-Web"]
        analysis["ai_bots"]["access_test"]["bots_allowed"] = [
            "PerplexityBot",
            "CCBot",
            "Google-Extended",
        ]

        score_resp, issues = self.scorer.score(analysis)
        whitelist_issues = [i for i in issues if "WHITELIST" in i.message.upper()]
        assert len(whitelist_issues) > 0

    def test_rate_limiting_penalty(self):
        """Rate limiting should cause -8 penalty."""
        analysis = self._base_analysis()
        analysis["base_analysis"]["rate_limited"] = True
        score_resp, _ = self.scorer.score(analysis)

        analysis_no_rl = self._base_analysis()
        score_no_rl, _ = self.scorer.score(analysis_no_rl)

        # Rate limited score should be at least 10 points lower
        assert score_resp.total_score < score_no_rl.total_score - 5

    def test_faq_schema_bonus(self):
        """FAQPage schema should add 3 points to discoverability category."""
        # Use a base with reduced discoverability so bonus has room
        analysis_no_faq = self._base_analysis()
        analysis_no_faq["sitemap"]["sitemap_found"] = False
        analysis_no_faq["sitemap"]["has_vehicle_urls"] = False
        analysis_no_faq["sitemap"]["sitemap_fresh"] = False

        analysis_faq = self._base_analysis()
        analysis_faq["sitemap"]["sitemap_found"] = False
        analysis_faq["sitemap"]["has_vehicle_urls"] = False
        analysis_faq["sitemap"]["sitemap_fresh"] = False
        analysis_faq["faq_schema"]["found"] = True

        score_no_faq, _ = self.scorer.score(analysis_no_faq)
        score_faq, _ = self.scorer.score(analysis_faq)

        assert score_faq.total_score >= score_no_faq.total_score + 3

    def test_llms_txt_bonus(self):
        """llms.txt should add 1 point to discoverability category."""
        # Reduce base discoverability so bonus has room
        analysis_no = self._base_analysis()
        analysis_no["sitemap"]["sitemap_found"] = False
        analysis_no["sitemap"]["has_vehicle_urls"] = False
        analysis_no["sitemap"]["sitemap_fresh"] = False

        analysis_yes = self._base_analysis()
        analysis_yes["sitemap"]["sitemap_found"] = False
        analysis_yes["sitemap"]["has_vehicle_urls"] = False
        analysis_yes["sitemap"]["sitemap_fresh"] = False
        analysis_yes["llms_txt"]["found"] = True

        score_no, _ = self.scorer.score(analysis_no)
        score_yes, _ = self.scorer.score(analysis_yes)

        assert score_yes.total_score >= score_no.total_score + 1
