"""robots.txt parsing and AI bot permission analysis."""

import logging

from server.data.bot_user_agents import ALL_AI_BOTS
from server.detectors.base import BaseDetector

logger = logging.getLogger(__name__)

# Bot names to look for in robots.txt (lowercase)
AI_BOT_NAMES = [
    "gptbot",
    "chatgpt",
    "chatgpt-user",
    "oai-searchbot",
    "ccbot",
    "claude",
    "claude-web",
    "claudebot",
    "claude-searchbot",
    "claude-user",
    "anthropic",
    "anthropic-ai",
    "perplexity",
    "perplexitybot",
    "bytespider",
    "google-extended",
    "openai",
    "amazonbot",
    "meta-externalagent",
    "meta-webindexer",
    "applebot-extended",
    "duckassistbot",
    "mistralaI-user",
    "gemini-deep-research",
]


class RobotsDetector(BaseDetector):
    """Parse robots.txt and analyze AI bot permissions."""

    async def check(self, domain: str) -> dict:
        """Analyze robots.txt for AI bot access."""
        result = {
            "robots_txt_exists": False,
            "robots_txt_url": self.make_url(domain, "/robots.txt"),
            "crawl_delay": None,
            "crawl_delay_tier": "friendly",
            "json_endpoints_blocked": False,
            "json_blocked_patterns": [],
            "ai_access_status": "accessible",
            "bot_permissions": {},
            "ai_bots_blocked_count": 0,
            "ai_bots_allowed_count": 0,
            "warnings": [],
            "raw_robots_txt": "",
        }

        # Fetch robots.txt
        content = await self.fetch_page(self.make_url(domain, "/robots.txt"))
        if not content:
            # Try HTTP fallback
            content = await self._fetch_url(f"http://{domain}/robots.txt")

        if not content or len(content.strip()) < 5:
            result["ai_access_status"] = "no_robots"
            # Set all bots as "not_specified" (no robots.txt means default allow)
            for bot_name in ALL_AI_BOTS:
                result["bot_permissions"][bot_name] = "not_specified"
            return result

        # Check for CloudFlare challenge masquerading as robots.txt
        from server.detectors.blocking import BlockingDetector

        bd = BlockingDetector(self.client, self.page_cache)
        if bd.is_cloudflare_challenge(content):
            result["warnings"].append("robots.txt appears to be a CloudFlare challenge page")
            for bot_name in ALL_AI_BOTS:
                result["bot_permissions"][bot_name] = "unknown"
            return result

        result["robots_txt_exists"] = True
        result["raw_robots_txt"] = content[:5000]

        self._parse_robots(content, result)
        return result

    def _parse_robots(self, content: str, result: dict) -> None:
        """Parse robots.txt content for AI bot permissions."""
        lines = content.strip().split("\n")

        current_agents: list[str] = []
        wildcard_rules: list[tuple[str, str]] = []  # (allow/disallow, path)
        bot_rules: dict[str, list[tuple[str, str]]] = {}

        for raw_line in lines:
            line = raw_line.split("#")[0].strip()
            if not line:
                continue

            lower = line.lower()

            if lower.startswith("user-agent:"):
                agent = line.split(":", 1)[1].strip().lower()
                # Per spec, consecutive user-agent lines form a group
                if not current_agents or (
                    current_agents
                    and lines.index(raw_line) > 0
                    and lines[lines.index(raw_line) - 1]
                    .split("#")[0]
                    .strip()
                    .lower()
                    .startswith("user-agent:")
                ):
                    current_agents.append(agent)
                else:
                    current_agents = [agent]

            elif lower.startswith("disallow:"):
                path = line.split(":", 1)[1].strip()
                for agent in current_agents:
                    if agent == "*":
                        wildcard_rules.append(("disallow", path))
                    else:
                        bot_rules.setdefault(agent, []).append(("disallow", path))

            elif lower.startswith("allow:"):
                path = line.split(":", 1)[1].strip()
                for agent in current_agents:
                    if agent == "*":
                        wildcard_rules.append(("allow", path))
                    else:
                        bot_rules.setdefault(agent, []).append(("allow", path))

            elif lower.startswith("crawl-delay:"):
                try:
                    delay = float(line.split(":", 1)[1].strip())
                    result["crawl_delay"] = delay
                    if delay < 5:
                        result["crawl_delay_tier"] = "friendly"
                    elif delay < 10:
                        result["crawl_delay_tier"] = "moderate"
                    elif delay < 30:
                        result["crawl_delay_tier"] = "slow"
                    else:
                        result["crawl_delay_tier"] = "excessive"
                except ValueError:
                    pass

            elif lower.startswith("sitemap:"):
                pass  # Handled by sitemap detector

        # Check wildcard blocks root
        wildcard_blocks_root = any(
            action == "disallow" and path in ("/", "") for action, path in wildcard_rules
        )

        # Check for JSON endpoint blocking in wildcard rules
        json_patterns = ["*.json", "/api/", "/feed"]
        for action, path in wildcard_rules:
            if action == "disallow" and any(jp in path for jp in json_patterns):
                result["json_endpoints_blocked"] = True
                result["json_blocked_patterns"].append(path)

        # Determine per-bot permissions
        for bot_name in ALL_AI_BOTS:
            bot_lower = bot_name.lower()

            # Check if this bot has specific rules
            specific_rules = None
            for agent_name, rules in bot_rules.items():
                if bot_lower in agent_name or agent_name in bot_lower:
                    specific_rules = rules
                    break

            if specific_rules is not None:
                # Bot has specific rules - check if fully blocked
                blocked = any(
                    action == "disallow" and path in ("/", "") for action, path in specific_rules
                )
                # Check if explicitly allowed (Allow: / overrides Disallow: /)
                allowed = any(action == "allow" and path == "/" for action, path in specific_rules)
                if allowed:
                    result["bot_permissions"][bot_name] = "allowed"
                elif blocked:
                    result["bot_permissions"][bot_name] = "blocked"
                else:
                    result["bot_permissions"][bot_name] = "allowed"
            elif wildcard_blocks_root:
                result["bot_permissions"][bot_name] = "blocked"
            else:
                result["bot_permissions"][bot_name] = "allowed"

        # Count blocked/allowed
        blocked_count = sum(1 for s in result["bot_permissions"].values() if s == "blocked")
        allowed_count = sum(
            1 for s in result["bot_permissions"].values() if s in ("allowed", "not_specified")
        )
        result["ai_bots_blocked_count"] = blocked_count
        result["ai_bots_allowed_count"] = allowed_count

        # Overall status
        total = len(result["bot_permissions"])
        if blocked_count == 0:
            result["ai_access_status"] = "accessible"
        elif blocked_count >= total * 0.5:
            result["ai_access_status"] = "blocked"
        elif (
            blocked_count > 0
            or result["crawl_delay_tier"] in ("slow", "excessive")
            or result["json_endpoints_blocked"]
        ):
            result["ai_access_status"] = "restricted"
        else:
            result["ai_access_status"] = "accessible"
