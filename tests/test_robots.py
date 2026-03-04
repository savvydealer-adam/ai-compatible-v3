"""Tests for robots.txt parsing."""

from server.detectors.robots import RobotsDetector


class TestRobotsParsing:
    def setup_method(self):
        self.det = RobotsDetector.__new__(RobotsDetector)
        self.det.page_cache = {}

    def test_allow_all(self, mock_robots_allow_all):
        result = {
            "robots_txt_exists": True,
            "crawl_delay": None,
            "crawl_delay_tier": "friendly",
            "json_endpoints_blocked": False,
            "json_blocked_patterns": [],
            "ai_access_status": "accessible",
            "bot_permissions": {},
            "ai_bots_blocked_count": 0,
            "ai_bots_allowed_count": 0,
            "warnings": [],
        }
        self.det._parse_robots(mock_robots_allow_all, result)
        assert result["ai_access_status"] == "accessible"
        assert result["ai_bots_blocked_count"] == 0
        # All bots should be allowed
        for perm in result["bot_permissions"].values():
            assert perm == "allowed"

    def test_block_specific_bots(self, mock_robots_block_ai):
        result = {
            "robots_txt_exists": True,
            "crawl_delay": None,
            "crawl_delay_tier": "friendly",
            "json_endpoints_blocked": False,
            "json_blocked_patterns": [],
            "ai_access_status": "accessible",
            "bot_permissions": {},
            "ai_bots_blocked_count": 0,
            "ai_bots_allowed_count": 0,
            "warnings": [],
        }
        self.det._parse_robots(mock_robots_block_ai, result)
        assert result["bot_permissions"].get("GPTBot") == "blocked"
        assert result["bot_permissions"].get("Claude-Web") == "blocked"
        assert result["ai_bots_blocked_count"] > 0

    def test_block_all(self, mock_robots_block_all):
        result = {
            "robots_txt_exists": True,
            "crawl_delay": None,
            "crawl_delay_tier": "friendly",
            "json_endpoints_blocked": False,
            "json_blocked_patterns": [],
            "ai_access_status": "accessible",
            "bot_permissions": {},
            "ai_bots_blocked_count": 0,
            "ai_bots_allowed_count": 0,
            "warnings": [],
        }
        self.det._parse_robots(mock_robots_block_all, result)
        assert result["ai_access_status"] == "blocked"
        # All bots blocked via wildcard
        for perm in result["bot_permissions"].values():
            assert perm == "blocked"

    def test_crawl_delay_tiers(self):
        robots_moderate = "User-agent: *\nCrawl-delay: 7\nAllow: /\n"
        result = {
            "robots_txt_exists": True,
            "crawl_delay": None,
            "crawl_delay_tier": "friendly",
            "json_endpoints_blocked": False,
            "json_blocked_patterns": [],
            "ai_access_status": "accessible",
            "bot_permissions": {},
            "ai_bots_blocked_count": 0,
            "ai_bots_allowed_count": 0,
            "warnings": [],
        }
        self.det._parse_robots(robots_moderate, result)
        assert result["crawl_delay"] == 7.0
        assert result["crawl_delay_tier"] == "moderate"

    def test_json_endpoint_blocking(self):
        robots = "User-agent: *\nDisallow: /*.json\nDisallow: /api/\nAllow: /\n"
        result = {
            "robots_txt_exists": True,
            "crawl_delay": None,
            "crawl_delay_tier": "friendly",
            "json_endpoints_blocked": False,
            "json_blocked_patterns": [],
            "ai_access_status": "accessible",
            "bot_permissions": {},
            "ai_bots_blocked_count": 0,
            "ai_bots_allowed_count": 0,
            "warnings": [],
        }
        self.det._parse_robots(robots, result)
        assert result["json_endpoints_blocked"] is True
