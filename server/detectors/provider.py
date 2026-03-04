"""Website platform/provider detection."""

import logging

from server.data.provider_patterns import PROVIDER_PATTERNS
from server.detectors.base import BaseDetector
from server.models.schemas import ProviderInfo

logger = logging.getLogger(__name__)


class ProviderDetector(BaseDetector):
    """Detect which website platform/provider built the site."""

    def detect(self, html_content: str) -> ProviderInfo:
        """Detect website provider from page content."""
        if not html_content:
            return ProviderInfo()

        soup = self.parse_html(html_content)
        lower = html_content.lower()

        # Priority 1: Footer links (high confidence)
        result = self._check_footer_links(soup)
        if result:
            return result

        # Priority 2: Footer text (high confidence)
        result = self._check_footer_text(soup, lower)
        if result:
            return result

        # Priority 3: Meta tags (high confidence)
        result = self._check_meta_tags(soup)
        if result:
            return result

        # Priority 4: Script/link sources (medium confidence)
        result = self._check_scripts(soup)
        if result:
            return result

        # Priority 5: Full page content scan (low confidence)
        return self._check_page_content(lower)

    def _check_footer_links(self, soup) -> ProviderInfo | None:
        """Check footer links for provider attribution."""
        footer = soup.find("footer")
        if not footer:
            return None

        links = footer.find_all("a", href=True)
        for link in links:
            href = link.get("href", "").lower()
            text = link.get_text(strip=True).lower()
            combined = href + " " + text
            for pattern, name, _url in PROVIDER_PATTERNS:
                if pattern in combined:
                    return ProviderInfo(
                        name=name,
                        confidence=0.9,
                        signals=[f"Footer link: {pattern}"],
                    )
        return None

    def _check_footer_text(self, soup, lower: str) -> ProviderInfo | None:
        """Check footer text for provider mentions."""
        footer = soup.find("footer")
        if not footer:
            return None

        footer_text = footer.get_text(strip=True).lower()
        for pattern, name, _url in PROVIDER_PATTERNS:
            if pattern in footer_text:
                return ProviderInfo(
                    name=name,
                    confidence=0.85,
                    signals=[f"Footer text: {pattern}"],
                )
        return None

    def _check_meta_tags(self, soup) -> ProviderInfo | None:
        """Check meta generator/author/designer tags."""
        for attr in ("generator", "author", "designer"):
            meta = soup.find("meta", {"name": attr})
            if meta:
                content = (meta.get("content", "") or "").lower()
                for pattern, name, _url in PROVIDER_PATTERNS:
                    if pattern in content:
                        return ProviderInfo(
                            name=name,
                            confidence=0.9,
                            signals=[f"Meta {attr}: {pattern}"],
                        )
        return None

    def _check_scripts(self, soup) -> ProviderInfo | None:
        """Check script and link src attributes."""
        for tag in soup.find_all(["script", "link"]):
            src = (tag.get("src") or tag.get("href") or "").lower()
            if not src:
                continue
            for pattern, name, _url in PROVIDER_PATTERNS:
                if pattern in src:
                    return ProviderInfo(
                        name=name,
                        confidence=0.7,
                        signals=[f"Script/link src: {pattern}"],
                    )
        return None

    def _check_page_content(self, lower: str) -> ProviderInfo:
        """Scan full page content as last resort."""
        for pattern, name, _url in PROVIDER_PATTERNS:
            if pattern in lower:
                return ProviderInfo(
                    name=name,
                    confidence=0.4,
                    signals=[f"Page content: {pattern}"],
                )
        return ProviderInfo()
