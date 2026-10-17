"""Local audit-event domain models."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

AuditOutcome = Literal[
    "success",
    "failure",
    "denied",
]

type AuditDetailValue = str | int | float | bool | None


class AuditEvent(BaseModel):
    """One immutable local audit event."""

    version: Literal[1] = 1

    event_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9-]+$",
    )

    occurred_at: datetime

    event_type: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[a-z0-9_.-]+$",
    )

    outcome: AuditOutcome

    actor: str = Field(
        default="local-user",
        min_length=1,
        max_length=128,
    )

    message: str = Field(
        min_length=1,
        max_length=2000,
    )

    project_id: str | None = Field(
        default=None,
        max_length=128,
    )

    resource_id: str | None = Field(
        default=None,
        max_length=256,
    )

    details: dict[
        str,
        AuditDetailValue,
    ] = Field(
        default_factory=dict,
    )


class AuditEventList(BaseModel):
    """Recent audit events."""

    total_count: int = Field(
        ge=0,
    )

    items: list[AuditEvent] = Field(
        default_factory=list,
    )
