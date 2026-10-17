"""Automatic BOLA scan API schemas."""

from pydantic import (
    BaseModel,
    Field,
)


class RunBOLAScanRequest(BaseModel):
    """Confirmation required before running a BOLA scan."""

    acknowledge_authorization: bool = False

    confirmation: str = Field(
        min_length=1,
        max_length=100,
    )

    max_cases: int = Field(
        default=100,
        ge=1,
        le=100,
    )


class DeleteBOLAScanRequest(BaseModel):
    """Confirmation required before deleting scan evidence."""

    acknowledge_evidence_loss: bool = False

    confirmation: str = Field(
        min_length=1,
        max_length=300,
    )


class PruneBOLAScansRequest(BaseModel):
    """Project scan-retention request."""

    acknowledge_evidence_loss: bool = False

    confirmation: str = Field(
        min_length=1,
        max_length=300,
    )

    keep_latest: int = Field(
        ge=1,
        le=500,
    )
