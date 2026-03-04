from pydantic import BaseModel

from server.models.schemas import (
    BlockingInfo,
    BotPermission,
    BotProtectionInfo,
    ContentSignalInfo,
    FaqSchemaInfo,
    InventoryInfo,
    LlmsTxtInfo,
    MarkdownAgentsInfo,
    MetaTagsInfo,
    ProviderInfo,
    RslInfo,
    SitemapInfo,
    VdpInfo,
)


class Issue(BaseModel):
    severity: str  # "critical", "warning", "info"
    category: str
    message: str
    recommendation: str = ""


class CategoryScore(BaseModel):
    name: str
    score: float
    max_score: float
    details: list[str] = []


class ScoreResponse(BaseModel):
    total_score: int
    max_score: int
    grade: str  # A+, A, B, C, D, F
    grade_label: str  # "Excellent", "Good", etc.
    categories: list[CategoryScore] = []
    bonus_points: int = 0


class AnalysisResponse(BaseModel):
    id: str
    url: str
    status: str  # "running", "complete", "error"
    progress: dict | None = None
    error: str | None = None

    # Results (populated when status == "complete")
    score: ScoreResponse | None = None
    blocking: BlockingInfo | None = None
    bot_permissions: list[BotPermission] = []
    bot_protection: BotProtectionInfo | None = None
    schemas: list[dict] = []
    inventory: InventoryInfo | None = None
    vdp: VdpInfo | None = None
    sitemap: SitemapInfo | None = None
    meta_tags: MetaTagsInfo | None = None
    provider: ProviderInfo | None = None
    markdown_agents: MarkdownAgentsInfo | None = None
    llms_txt: LlmsTxtInfo | None = None
    content_signal: ContentSignalInfo | None = None
    rsl: RslInfo | None = None
    faq_schema: FaqSchemaInfo | None = None
    issues: list[Issue] = []
    recommendations: list[str] = []
    analysis_time: float | None = None


class AnalysisStartResponse(BaseModel):
    id: str
    status: str = "running"


class LeadResponse(BaseModel):
    success: bool
    message: str = ""
