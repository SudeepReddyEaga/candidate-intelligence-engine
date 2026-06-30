from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SourceType(str, Enum):
    CSV = "csv"
    ATS_JSON = "ats_json"
    RESUME_PDF = "resume_pdf"
    GITHUB_JSON = "github_json"
    NOTES = "notes"


class SourcePayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_type: SourceType
    name: str
    content: bytes


class ProvenanceEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_type: SourceType
    source_name: str
    field_path: str
    raw_value: Any = None
    parser: str


class PartialCandidate(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_name: str
    source_type: SourceType
    name: str | None = None
    emails: tuple[str, ...] = ()
    phones: tuple[str, ...] = ()
    location: str | None = None
    skills: tuple[str, ...] = ()
    experience_years: float | None = None
    github_url: str | None = None
    linkedin_url: str | None = None
    portfolio_url: str | None = None
    experience: tuple[dict[str, Any], ...] = ()
    projects: tuple[dict[str, Any], ...] = ()
    education: tuple[dict[str, Any], ...] = ()
    resume_text: str | None = None
    notes: str | None = None
    provenance: dict[str, tuple[ProvenanceEntry, ...]] = Field(default_factory=dict)


class ConfidenceReport(BaseModel):
    overall: float
    fields: dict[str, float]
    explanations: dict[str, str]


class CandidateRecord(BaseModel):
    candidate_id: str
    name: str | None = None
    emails: list[str] = Field(default_factory=list)
    phones: list[str] = Field(default_factory=list)
    location: str | None = None
    skills: list[str] = Field(default_factory=list)
    experience_years: float | None = None
    github_url: str | None = None
    linkedin_url: str | None = None
    portfolio_url: str | None = None
    experience: list[dict[str, Any]] = Field(default_factory=list)
    projects: list[dict[str, Any]] = Field(default_factory=list)
    education: list[dict[str, Any]] = Field(default_factory=list)
    resume_text: str | None = None
    notes: str | None = None
    provenance: dict[str, list[ProvenanceEntry]] = Field(default_factory=dict)
    confidence: ConfidenceReport = Field(
        default_factory=lambda: ConfidenceReport(overall=0.0, fields={}, explanations={})
    )


class ProjectionConfig(BaseModel):
    fields: list[str] | None = None
    rename: dict[str, str] = Field(default_factory=dict)
    normalize_keys: str = "snake_case"
    include_confidence: bool = True
    include_provenance: bool = True
    missing_value_policy: str = "include_null"


class TransformInput(BaseModel):
    sources: list[SourcePayload]
    projection: ProjectionConfig = Field(default_factory=ProjectionConfig)
