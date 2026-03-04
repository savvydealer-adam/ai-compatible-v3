import re

from pydantic import BaseModel, field_validator


class AnalysisRequest(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def normalize_url(cls, v: str) -> str:
        v = v.strip().rstrip("/")
        # Strip protocol if present, we'll re-add it
        v = re.sub(r"^https?://", "", v)
        # Remove trailing paths/slashes for domain-only input
        if not v:
            msg = "URL cannot be empty"
            raise ValueError(msg)
        return f"https://{v}"


class LeadRequest(BaseModel):
    name: str
    email: str
    dealership: str
    phone: str = ""
    analysis_url: str = ""
    score: int | None = None
