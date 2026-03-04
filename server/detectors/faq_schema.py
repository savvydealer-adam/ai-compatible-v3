"""FAQPage schema detection."""

import logging

from server.detectors.base import BaseDetector
from server.detectors.schema_parser import SchemaParser
from server.models.schemas import FaqSchemaInfo

logger = logging.getLogger(__name__)


class FaqSchemaDetector(BaseDetector):
    """Detect FAQPage JSON-LD schema (3.2x more AI citations)."""

    async def check(self, domain: str) -> FaqSchemaInfo:
        """Check homepage and common FAQ pages for FAQPage schema."""
        info = FaqSchemaInfo()
        parser = SchemaParser(self.client, self.page_cache)

        # Check homepage first
        pages_to_check = [
            self.make_url(domain),
            self.make_url(domain, "/faq"),
            self.make_url(domain, "/faqs"),
            self.make_url(domain, "/frequently-asked-questions"),
        ]

        for url in pages_to_check:
            if self._check_timeout():
                break

            content = await self.fetch_page(url)
            if not content:
                continue

            result = parser.parse_content(content)
            for detail in result.get("schema_details", []):
                if detail["type"] == "FAQPage":
                    info.found = True
                    # Count questions
                    raw = detail.get("raw_data", {})
                    main_entity = raw.get("mainEntity", [])
                    if isinstance(main_entity, list):
                        info.question_count = len(main_entity)
                    else:
                        info.question_count = 1
                    info.details = f"FAQPage found on {url} with {info.question_count} questions"
                    return info

        return info
