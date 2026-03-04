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


class VerifyRequestModel(BaseModel):
    analysis_id: str
    name: str
    email: str
    dealership: str
    phone: str = ""
    method: str = "email"  # "email" or "sms"

    @field_validator("method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        if v not in ("email", "sms"):
            msg = "method must be 'email' or 'sms'"
            raise ValueError(msg)
        return v


class VerifyConfirmModel(BaseModel):
    analysis_id: str
    code: str
