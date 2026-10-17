"""Central finding domain models."""

from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    Field,
)

from accessmatrix.scanning.models import (
    FindingConfidence,
    FindingSeverity,
)

FindingCategory = Literal[
    "BOLA",
    "BFLA",
    "BOPLA",
]

FindingStatus = Literal[
    "open",
    "resolved",
    "false_positive",
    "accepted_risk",
]


class FindingRecord(BaseModel):
    """Deduplicated authorization finding."""

    version: Literal[1] = 1

    finding_id: str
    fingerprint: str
    project_id: str

    category: FindingCategory

    title: str
    description: str

    severity: FindingSeverity
    confidence: FindingConfidence
    status: FindingStatus = "open"

    operation_key: str

    identity_id: str
    identity_name: str

    resource_type: str

    baseline_object_id: str | None
    probe_object_id: str

    first_seen_at: datetime
    last_seen_at: datetime
    updated_at: datetime

    occurrence_count: int = Field(
        ge=1,
    )

    reopened_count: int = Field(
        default=0,
        ge=0,
    )

    last_observed_status_code: int = Field(
        ge=100,
        le=599,
    )

    matching_response_fields: dict[
        str,
        bool,
    ] = Field(
        default_factory=dict,
    )

    scan_ids: list[str] = Field(
        default_factory=list,
    )

    source_finding_ids: list[str] = Field(
        default_factory=list,
    )

    resolution_note: str | None = Field(
        default=None,
        max_length=4000,
    )


class FindingList(BaseModel):
    """Filtered project finding collection."""

    project_id: str

    total_count: int
    open_count: int
    resolved_count: int
    false_positive_count: int
    accepted_risk_count: int

    items: list[FindingRecord] = Field(
        default_factory=list,
    )
