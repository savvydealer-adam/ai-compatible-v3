from pydantic import BaseModel


class BotPermission(BaseModel):
    bot_name: str
    user_agent: str
    robots_status: str = "unknown"  # "allowed", "blocked", "no_robots"
    http_status: int | None = None
    http_accessible: bool | None = None
    response_time: float | None = None
    details: str = ""
    cloudflare_ip_whitelisted: bool = False
    cf_mitigated_header: bool = False
    challenge_platform_detected: bool = False


class SchemaItem(BaseModel):
    schema_type: str
    properties_found: list[str] = []
    properties_missing: list[str] = []
    completeness: float = 0.0
    raw_data: dict | None = None


class SitemapInfo(BaseModel):
    found: bool = False
    url: str = ""
    entry_count: int = 0
    has_lastmod: bool = False
    has_images: bool = False
    issues: list[str] = []


class MetaTagsInfo(BaseModel):
    title: str = ""
    description: str = ""
    canonical: str = ""
    has_og_tags: bool = False
    has_twitter_cards: bool = False
    x_robots_tag: str = ""
    noai_directive: bool = False
    noimageai_directive: bool = False
    issues: list[str] = []


class ProviderInfo(BaseModel):
    name: str = "Unknown"
    confidence: float = 0.0
    signals: list[str] = []


class InventoryInfo(BaseModel):
    found: bool = False
    url: str = ""
    vehicle_count: int = 0
    schemas: list[SchemaItem] = []
    issues: list[str] = []


class VdpInfo(BaseModel):
    found: bool = False
    url: str = ""
    schemas: list[SchemaItem] = []
    issues: list[str] = []


class BlockingInfo(BaseModel):
    is_blocked: bool = False
    cloudflare_detected: bool = False
    captcha_detected: bool = False
    rate_limited: bool = False
    js_challenge: bool = False
    blocking_provider: str = ""
    status_code: int | None = None
    details: list[str] = []
    cloudflare_blocking_tier: str = "none"
    cloudflare_tier_signals: list[str] = []


class MarkdownAgentsInfo(BaseModel):
    available: bool = False
    url: str = ""
    token_count: int = 0
    content_signal_header: str = ""
    details: str = ""


class LlmsTxtInfo(BaseModel):
    found: bool = False
    url: str = ""
    valid_format: bool = False
    has_full_version: bool = False
    details: str = ""


class ContentSignalInfo(BaseModel):
    found: bool = False
    ai_train: str = ""
    search: str = ""
    ai_input: str = ""
    raw_directive: str = ""


class RslInfo(BaseModel):
    found: bool = False
    license_url: str = ""
    license_data: dict | None = None
    details: str = ""


class FaqSchemaInfo(BaseModel):
    found: bool = False
    question_count: int = 0
    details: str = ""


class BotProtectionInfo(BaseModel):
    vendor: str = ""
    detected: bool = False
    signals: list[str] = []


class GroundTruth(BaseModel):
    vdp_url: str = ""
    expected_price: str = ""
    expected_vin: str = ""
    vehicle_title: str = ""


class AIProviderVerification(BaseModel):
    provider_name: str  # "openai", "anthropic", "gemini"
    could_access: bool | None = None  # None = inconclusive
    returned_price: str = ""
    price_matches: bool = False
    returned_vin: str = ""
    vin_matches: bool = False
    response_text: str = ""
    error: str = ""


class AILiveVerifyResult(BaseModel):
    verified: bool = False
    providers: list[AIProviderVerification] = []
    ground_truth_used: GroundTruth | None = None
    details: str = ""


# ── V2 Models ──


class GroundTruthPage(BaseModel):
    """Single crawled page from ground truth (Playwright or httpx fallback)."""

    url: str = ""
    page_type: str = ""  # "robots", "sitemap", "srp", "vdp"
    accessible: bool = False
    price: str = ""
    vin: str = ""
    vehicle_title: str = ""
    vehicle_count: int = 0
    robots_rules: dict[str, str] = {}  # bot_name -> "allowed"|"blocked"
    sitemap_url_count: int = 0


class GroundTruthResult(BaseModel):
    """Collection of ground truth pages from headless crawl."""

    pages: list[GroundTruthPage] = []
    source: str = "playwright"  # "playwright" or "httpx_fallback"
    crawl_time: float = 0.0
    domain: str = ""


class AIVerifyCheck(BaseModel):
    """Single comparison check: AI provider vs ground truth."""

    check_type: str = ""  # "robots", "inventory", "vdp_price", "vdp_vin", "sitemap"
    could_access: bool | None = None
    data_returned: str = ""
    data_expected: str = ""
    match_score: float = 0.0  # 0.0-1.0


class AIProviderVerificationV2(BaseModel):
    """Per-provider verification result with detailed checks."""

    provider_name: str
    checks: list[AIVerifyCheck] = []
    overall_access: str = "unknown"  # "full", "partial", "blocked", "error"
    access_score: float = 0.0  # 0-10
    response_text: str = ""
    error: str = ""


class AILiveVerifyResultV2(BaseModel):
    """Full V2 live verification result with ground truth comparison."""

    ground_truth: GroundTruthResult | None = None
    providers: list[AIProviderVerificationV2] = []
    summary: str = ""
    ai_verify_score: float = 0.0  # 0-10, used by scorer
