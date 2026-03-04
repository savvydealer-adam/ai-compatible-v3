"""llms.txt and llms-full.txt detection."""

import logging

from server.detectors.base import BaseDetector
from server.models.schemas import LlmsTxtInfo

logger = logging.getLogger(__name__)


class LlmsTxtDetector(BaseDetector):
    """Check for llms.txt and llms-full.txt files."""

    async def check(self, domain: str) -> LlmsTxtInfo:
        """Fetch and validate llms.txt."""
        info = LlmsTxtInfo()

        # Check /llms.txt
        url = self.make_url(domain, "/llms.txt")
        resp = await self.fetch_response(url, timeout=8.0)

        if resp and resp.status_code == 200 and resp.text:
            content = resp.text.strip()
            # Validate it looks like actual llms.txt (markdown-ish format)
            if len(content) > 10 and not content.startswith("<!"):
                info.found = True
                info.url = str(resp.url)
                info.valid_format = self._validate_format(content)
                info.details = f"llms.txt found ({len(content)} chars)"

        # Check /llms-full.txt
        full_url = self.make_url(domain, "/llms-full.txt")
        resp_full = await self.fetch_response(full_url, timeout=8.0)

        if resp_full and resp_full.status_code == 200 and resp_full.text:
            content_full = resp_full.text.strip()
            if len(content_full) > 10 and not content_full.startswith("<!"):
                info.has_full_version = True
                if not info.found:
                    info.found = True
                    info.url = str(resp_full.url)
                    info.details = f"llms-full.txt found ({len(content_full)} chars)"

        return info

    @staticmethod
    def _validate_format(content: str) -> bool:
        """Check if content looks like valid llms.txt markdown format."""
        lines = content.split("\n")
        # Should have a title (# heading) and some content
        has_heading = any(line.strip().startswith("#") for line in lines[:10])
        has_links = any("[" in line and "](" in line for line in lines)
        has_content = len(lines) >= 3

        return has_heading and has_content or has_links
