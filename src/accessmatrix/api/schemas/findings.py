"""Central finding API schemas."""

from pydantic import (
    BaseModel,
    Field,
)

from accessmatrix.findings.models import (
    FindingStatus,
)


class UpdateFindingRequest(BaseModel):
    """Update a finding lifecycle status."""

    status: FindingStatus

    note: str | None = Field(
        default=None,
        max_length=4000,
    )
