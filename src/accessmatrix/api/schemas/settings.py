"""Application settings API schemas."""

from pydantic import (
    BaseModel,
    Field,
)


class ResetApplicationSettingsRequest(BaseModel):
    """Confirmation required before resetting settings."""

    confirmation: str = Field(
        min_length=1,
        max_length=100,
    )


class ValidateTargetRequest(BaseModel):
    """Target URL safety-inspection request."""

    url: str = Field(
        min_length=1,
        max_length=4096,
    )
