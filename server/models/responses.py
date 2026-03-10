from pydantic import BaseModel

from server.models.schemas import (
    AILiveVerifyResult,
    AILiveVerifyResultV2,
    BlockingInfo,
    BotPermission,
    BotProtectionInfo,
    ContentSignalInfo,
    FaqSchemaInfo,
    InventoryInfo,
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
    gated: bool = False
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
    content_signal: ContentSignalInfo | None = None
    rsl: RslInfo | None = None
    faq_schema: FaqSchemaInfo | None = None
    ai_live_verify: AILiveVerifyResultV2 | AILiveVerifyResult | None = None
    issues: list[Issue] = []
    recommendations: list[str] = []
    analysis_time: float | None = None


class AnalysisStartResponse(BaseModel):
    id: str
    status: str = "running"


class LeadResponse(BaseModel):
    success: bool
    message: str = ""


class VerifyResponse(BaseModel):
    success: bool
    message: str = ""
    method: str = ""


class VerifyConfirmResponse(BaseModel):
    success: bool
    token: str = ""
    jwt: str = ""
    message: str = ""


class AuthMeResponse(BaseModel):
    email: str
    name: str
    dealership: str
    phone: str = ""


def to_public_response(response: AnalysisResponse) -> AnalysisResponse:
    """Strip detailed results, keeping only total score + grade. Returns a gated copy."""
    public_score = None
    if response.score:
        public_score = ScoreResponse(
            total_score=response.score.total_score,
            max_score=response.score.max_score,
            grade=response.score.grade,
            grade_label=response.score.grade_label,
        )
    return AnalysisResponse(
        id=response.id,
        url=response.url,
        status=response.status,
        gated=True,
        score=public_score,
    )
