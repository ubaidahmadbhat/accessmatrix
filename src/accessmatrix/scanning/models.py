"""BOLA scan result domain models."""

from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    Field,
)

BOLAOutcome = Literal[
    "pass",
    "finding",
    "inconclusive",
    "blocked",
]

FindingSeverity = Literal[
    "info",
    "low",
    "medium",
    "high",
    "critical",
]

FindingConfidence = Literal[
    "low",
    "medium",
    "high",
]

ScanStatus = Literal[
    "completed",
    "partial",
    "failed",
]


class ResponseEvidence(BaseModel):
    """Redacted evidence captured from one request."""

    request_url: str
    status_code: int
    reason_phrase: str
    elapsed_ms: float

    response_headers: dict[
        str,
        str,
    ] = Field(
        default_factory=dict,
    )

    body_excerpt: str | None
    body_sha256: str | None

    body_bytes_captured: int
    body_truncated: bool
    declared_content_length: int | None
    redirect_blocked: bool


class BOLACaseResult(BaseModel):
    """Result of one baseline and cross-owner comparison."""

    case_id: str
    case_name: str

    operation_key: str

    identity_id: str
    identity_name: str

    resource_type: str

    baseline_object_id: str | None
    probe_object_id: str

    expected_probe_status_codes: list[int] = Field(
        default_factory=list,
    )

    outcome: BOLAOutcome
    explanation: str

    matching_response_fields: dict[
        str,
        bool,
    ] = Field(
        default_factory=dict,
    )

    issues: list[str] = Field(
        default_factory=list,
    )

    baseline_evidence: ResponseEvidence | None = None

    probe_evidence: ResponseEvidence | None = None


class BOLAFinding(BaseModel):
    """Persisted broken object-level authorization finding."""

    finding_id: str
    case_id: str

    category: Literal["BOLA"] = "BOLA"

    title: str
    description: str

    severity: FindingSeverity
    confidence: FindingConfidence

    operation_key: str

    identity_id: str
    identity_name: str

    resource_type: str

    baseline_object_id: str | None
    probe_object_id: str

    observed_status_code: int

    matching_response_fields: dict[
        str,
        bool,
    ] = Field(
        default_factory=dict,
    )


class BOLAScan(BaseModel):
    """Persisted automatic BOLA scan."""

    version: Literal[1] = 1

    scan_id: str
    project_id: str

    started_at: datetime
    completed_at: datetime

    status: ScanStatus

    total_count: int
    pass_count: int
    finding_count: int
    inconclusive_count: int
    blocked_count: int

    results: list[BOLACaseResult] = Field(
        default_factory=list,
    )

    findings: list[BOLAFinding] = Field(
        default_factory=list,
    )


class BOLAScanSummary(BaseModel):
    """Compact scan information used in scan listings."""

    scan_id: str
    project_id: str

    started_at: datetime
    completed_at: datetime

    status: ScanStatus

    total_count: int
    pass_count: int
    finding_count: int
    inconclusive_count: int
    blocked_count: int


class BOLAScanList(BaseModel):
    """List of persisted scans for one project."""

    project_id: str

    items: list[BOLAScanSummary] = Field(
        default_factory=list,
    )


class ScanDeletionResult(BaseModel):
    """Result of deleting one persisted scan."""

    project_id: str
    scan_id: str
    deleted: bool

    retained_finding_history: bool = True


class ScanRetentionResult(BaseModel):
    """Result of applying project scan retention."""

    project_id: str

    keep_latest: int

    before_count: int
    after_count: int
    deleted_count: int

    deleted_scan_ids: list[str] = Field(
        default_factory=list,
    )

    retained_finding_history: bool = True
