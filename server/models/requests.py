from pydantic import BaseModel, HttpUrl


class AnalysisRequest(BaseModel):
    url: HttpUrl


class LeadRequest(BaseModel):
    name: str
    email: str
    dealership: str
    phone: str = ""
    analysis_url: str = ""
    score: int | None = None
