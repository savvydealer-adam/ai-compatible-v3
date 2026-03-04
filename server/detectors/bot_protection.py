"""WAF/bot management vendor detection."""

import logging

from server.data.provider_patterns import BOT_MANAGEMENT_PATTERNS
from server.detectors.base import BaseDetector
from server.models.schemas import BotProtectionInfo

logger = logging.getLogger(__name__)


class BotProtectionDetector(BaseDetector):
    """Detect bot protection/WAF vendors (not just CDN presence)."""

    def detect(self, homepage_content: str, base_analysis: dict | None = None) -> BotProtectionInfo:
        """Check for active bot management (not just CDN headers)."""
        info = BotProtectionInfo()
        content_lower = homepage_content.lower() if homepage_content else ""
        signals: list[str] = []

        for vendor, patterns in BOT_MANAGEMENT_PATTERNS.items():
            for pattern in patterns:
                if pattern in content_lower:
                    info.detected = True
                    info.vendor = vendor
                    signals.append(pattern)

        info.signals = signals
        return info
