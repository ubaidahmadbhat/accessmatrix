"""Authorization report domain models."""

from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    Field,
)

from accessmatrix.findings.models import (
    FindingRecord,
)
from accessmatrix.scanning.models import (
    BOLAScanSummary,
)

ReportFormat = Literal[
    "json",
    "markdown",
    "html",
    "sarif",
    "junit",
]


class ReportSummary(BaseModel):
    """Finding and scan counts included in a report."""

    finding_count: int = Field(
        ge=0,
    )

    open_count: int = Field(
        ge=0,
    )

    resolved_count: int = Field(
        ge=0,
    )

    false_positive_count: int = Field(
        ge=0,
    )

    accepted_risk_count: int = Field(
        ge=0,
    )

    scan_count: int = Field(
        ge=0,
    )

    scan_case_count: int = Field(
        ge=0,
    )

    scan_pass_count: int = Field(
        ge=0,
    )

    scan_finding_count: int = Field(
        ge=0,
    )

    scan_inconclusive_count: int = Field(
        ge=0,
    )

    scan_blocked_count: int = Field(
        ge=0,
    )


class ReportSnapshot(BaseModel):
    """Immutable report-generation input."""

    version: Literal[1] = 1

    report_id: str
    report_format: ReportFormat

    project_id: str
    project_name: str

    project_description: str | None
    target_base_url: str | None

    title: str
    generated_at: datetime

    summary: ReportSummary

    findings: list[
        FindingRecord
    ] = Field(
        default_factory=list,
    )

    scans: list[
        BOLAScanSummary
    ] = Field(
        default_factory=list,
    )


class ReportArtifactMetadata(BaseModel):
    """Metadata for one locally stored report artifact."""

    version: Literal[1] = 1

    report_id: str
    project_id: str
    project_name: str

    title: str
    report_format: ReportFormat

    generated_at: datetime

    finding_count: int = Field(
        ge=0,
    )

    scan_count: int = Field(
        ge=0,
    )

    filename: str
    media_type: str

    size_bytes: int = Field(
        ge=0,
    )

    sha256: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[a-f0-9]{64}$",
    )


class ReportArtifactList(BaseModel):
    """Stored reports for one project."""

    project_id: str

    items: list[
        ReportArtifactMetadata
    ] = Field(
        default_factory=list,
    )