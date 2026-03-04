"""Really Simple Licensing (RSL) detection."""

import json
import logging

from server.detectors.base import BaseDetector
from server.models.schemas import RslInfo

logger = logging.getLogger(__name__)


class RslDetector(BaseDetector):
    """Check for Really Simple Licensing in robots.txt."""

    async def check(self, domain: str, robots_content: str | None = None) -> RslInfo:
        """Check for License: directive in robots.txt and fetch RSL JSON."""
        info = RslInfo()

        if robots_content is None:
            robots_content = await self.fetch_page(self.make_url(domain, "/robots.txt"))

        if not robots_content:
            return info

        # Look for License: directive
        for line in robots_content.split("\n"):
            stripped = line.strip()
            if stripped.lower().startswith("license:"):
                license_url = stripped.split(":", 1)[1].strip()
                if license_url:
                    info.found = True
                    info.license_url = license_url
                    break

        if not info.found:
            return info

        # Try to fetch RSL JSON
        resp = await self.fetch_response(info.license_url, timeout=8.0)
        if resp and resp.status_code == 200 and resp.text:
            try:
                info.license_data = json.loads(resp.text)
                info.details = "RSL license data retrieved"
            except json.JSONDecodeError:
                info.details = "License URL found but not valid JSON"

        return info
