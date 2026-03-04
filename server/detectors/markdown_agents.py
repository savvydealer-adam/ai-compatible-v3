"""Cloudflare Markdown for Agents detection."""

import contextlib
import logging

from server.detectors.base import BaseDetector
from server.models.schemas import MarkdownAgentsInfo

logger = logging.getLogger(__name__)


class MarkdownAgentsDetector(BaseDetector):
    """Check Cloudflare's Markdown for Agents feature."""

    async def check(self, domain: str) -> MarkdownAgentsInfo:
        """Test if site supports Markdown for Agents via Accept: text/markdown."""
        info = MarkdownAgentsInfo()
        url = self.make_url(domain)

        resp = await self.fetch_response(
            url,
            headers={
                "Accept": "text/markdown",
                "User-Agent": "Mozilla/5.0 (compatible; AI-Agent/1.0)",
            },
        )

        if not resp:
            return info

        content_type = resp.headers.get("content-type", "").lower()

        if "text/markdown" in content_type:
            info.available = True
            info.url = str(resp.url)

            # Token count from header
            tokens = resp.headers.get("x-markdown-tokens", "")
            if tokens:
                with contextlib.suppress(ValueError):
                    info.token_count = int(tokens)

            # Content-Signal header
            content_signal = resp.headers.get("content-signal", "")
            if content_signal:
                info.content_signal_header = content_signal

            info.details = f"Markdown for Agents supported ({len(resp.text)} chars)"

        return info
