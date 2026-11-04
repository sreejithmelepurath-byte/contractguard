from typing import Literal

from pydantic import BaseModel, Field


class RedFlag(BaseModel):
    category: Literal[
        "payment_terms",
        "scope_revisions",
        "intellectual_property",
        "termination",
        "liability",
        "non_compete",
        "other",
    ]
    severity: Literal["low", "medium", "high"]
    clause: str = Field(..., description="Short excerpt of the clause that triggered the flag")
    explanation: str = Field(..., description="Plain-English reason this matters to a freelancer")


class AnalysisResult(BaseModel):
    summary: str = Field(..., description="Plain-English summary of deliverables and key terms")
    red_flags: list[RedFlag] = Field(default_factory=list)


class AnalysisResponse(AnalysisResult):
    filename: str
    pages: int
    ocr_pages: int
    processing_seconds: float
    disclaimer: str = "Informational analysis only - not a substitute for legal advice."
