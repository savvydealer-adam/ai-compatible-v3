"""Tests for website provider detection."""

from server.detectors.provider import ProviderDetector


class TestProviderDetection:
    def setup_method(self):
        self.det = ProviderDetector.__new__(ProviderDetector)
        self.det.page_cache = {}

    def test_detect_savvy_dealer_footer(self, mock_html_dealer):
        result = self.det.detect(mock_html_dealer)
        assert result.name == "Savvy Dealer"
        assert result.confidence >= 0.8

    def test_detect_wordpress(self):
        html = (
            '<html><head><link rel="stylesheet"'
            ' href="/wp-content/themes/style.css">'
            "</head><body></body></html>"
        )
        result = self.det.detect(html)
        assert result.name == "WordPress"

    def test_detect_dealeron(self):
        html = '<html><body><footer>Website by <a href="https://www.dealeron.com">DealerON</a></footer></body></html>'
        result = self.det.detect(html)
        assert result.name == "DealerON"

    def test_unknown_provider(self):
        html = "<html><body><h1>Plain site</h1></body></html>"
        result = self.det.detect(html)
        assert result.name == "Unknown"

    def test_meta_generator(self):
        html = (
            '<html><head><meta name="generator"'
            ' content="Dealer Inspire Platform">'
            "</head><body></body></html>"
        )
        result = self.det.detect(html)
        assert result.name == "Dealer Inspire"
