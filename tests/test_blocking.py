"""Tests for blocking detection."""

from server.detectors.blocking import BlockingDetector


class TestBlockingDetection:
    def setup_method(self):
        self.det = BlockingDetector.__new__(BlockingDetector)
        self.det.page_cache = {}

    def test_cloudflare_detection_content(self):
        content = "checking your browser before accessing this site. cloudflare ray id: abc123"
        assert self.det._detect_captcha(content) is False  # Not CAPTCHA, just CF

    def test_captcha_site_blocking(self):
        content = "verify you are human to access this website"
        assert self.det._detect_captcha(content) is True

    def test_captcha_form_context_not_flagged(self):
        content = "contact form - please complete the captcha to submit your message"
        assert self.det._detect_captcha(content) is False

    def test_captcha_site_blocking_context(self):
        content = (
            "captcha - verify to continue browsing this site. access denied until verification."
        )
        assert self.det._detect_captcha(content) is True

    def test_js_challenge_detection(self):
        from server.detectors.blocking import JS_CHALLENGE_PATTERNS

        content = "just a moment... checking your browser... _cf_chl_opt challenge-running"
        matches = sum(1 for p in JS_CHALLENGE_PATTERNS if p in content)
        assert matches >= 2

    def test_cloudflare_challenge_page(self):
        content = """
        <html><body>
        <title>Just a moment...</title>
        <div id="cf-browser-verification">
        Checking your browser... _cf_chl_opt challenge-running
        </div></body></html>
        """
        assert self.det.is_cloudflare_challenge(content) is True

    def test_normal_page_not_challenge(self):
        content = "<html><body><h1>Welcome to our dealership</h1></body></html>"
        assert self.det.is_cloudflare_challenge(content) is False
