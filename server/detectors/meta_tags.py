"""Title, description, canonical, OG, X-Robots-Tag, noai meta detection."""

import logging

from server.detectors.base import BaseDetector
from server.models.schemas import MetaTagsInfo

logger = logging.getLogger(__name__)


class MetaTagsDetector(BaseDetector):
    """Analyze meta tags and HTTP headers for SEO/AI signals."""

    async def check(self, url: str, html_content: str | None = None) -> MetaTagsInfo:
        """Check meta tags on a page."""
        info = MetaTagsInfo()

        if html_content is None:
            html_content = await self.fetch_page(url)
        if not html_content:
            info.issues.append("Could not fetch page content")
            return info

        soup = self.parse_html(html_content)

        # Title
        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            info.title = title_tag.string.strip()
        else:
            info.issues.append("Missing title tag")

        # Meta description
        desc = soup.find("meta", {"name": "description"})
        if desc and desc.get("content"):
            info.description = desc["content"].strip()
        else:
            info.issues.append("Missing meta description")

        # Canonical
        canonical = soup.find("link", {"rel": "canonical"})
        if canonical and canonical.get("href"):
            info.canonical = canonical["href"]

        # Open Graph
        og_tags = ["og:title", "og:description", "og:image", "og:url"]
        found_og = sum(1 for tag in og_tags if soup.find("meta", {"property": tag}))
        info.has_og_tags = found_og >= 2

        # Twitter Cards
        twitter_tags = ["twitter:card", "twitter:title"]
        found_twitter = sum(1 for tag in twitter_tags if soup.find("meta", {"name": tag}))
        info.has_twitter_cards = found_twitter >= 1

        # Robots meta tag
        robots_meta = soup.find("meta", {"name": "robots"})
        if robots_meta and robots_meta.get("content"):
            content = robots_meta["content"].lower()
            # noai/noimageai detection
            if "noai" in content:
                info.noai_directive = True
                info.issues.append("noai directive found in robots meta tag")
            if "noimageai" in content:
                info.noimageai_directive = True
                info.issues.append("noimageai directive found in robots meta tag")

        return info

    async def check_x_robots_header(self, url: str) -> dict:
        """Check X-Robots-Tag HTTP header."""
        result = {
            "x_robots_tag": "",
            "x_robots_noindex": False,
            "x_robots_nofollow": False,
            "x_robots_noai": False,
        }

        resp = await self.fetch_response(url)
        if not resp:
            return result

        x_robots = resp.headers.get("x-robots-tag", "")
        if x_robots:
            result["x_robots_tag"] = x_robots
            lower = x_robots.lower()
            result["x_robots_noindex"] = "noindex" in lower
            result["x_robots_nofollow"] = "nofollow" in lower
            result["x_robots_noai"] = "noai" in lower or "noimageai" in lower

        return result
