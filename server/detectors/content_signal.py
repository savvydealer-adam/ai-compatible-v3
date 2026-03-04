"""Content-Signal directives from robots.txt."""

import logging
import re

from server.detectors.base import BaseDetector
from server.models.schemas import ContentSignalInfo

logger = logging.getLogger(__name__)


class ContentSignalDetector(BaseDetector):
    """Parse Content-Signal directives from robots.txt."""

    async def check(self, domain: str, robots_content: str | None = None) -> ContentSignalInfo:
        """Check for Content-Signal directives."""
        info = ContentSignalInfo()

        if robots_content is None:
            robots_content = await self.fetch_page(self.make_url(domain, "/robots.txt"))

        if not robots_content:
            return info

        # Look for Content-Signal directive
        for line in robots_content.split("\n"):
            stripped = line.strip()
            if stripped.lower().startswith("content-signal:"):
                info.found = True
                info.raw_directive = stripped.split(":", 1)[1].strip()
                self._parse_directive(info)
                break

        return info

    @staticmethod
    def _parse_directive(info: ContentSignalInfo) -> None:
        """Parse Content-Signal key=value pairs."""
        raw = info.raw_directive
        # Parse comma-separated key=value pairs
        pairs = [p.strip() for p in raw.split(",")]
        for pair in pairs:
            match = re.match(r"(\w[\w-]*)=(\S+)", pair)
            if match:
                key = match.group(1).lower().replace("-", "_")
                val = match.group(2)
                if key == "ai_train":
                    info.ai_train = val
                elif key == "search":
                    info.search = val
                elif key == "ai_input":
                    info.ai_input = val
