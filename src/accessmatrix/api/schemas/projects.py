"""Project API schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProjectCreate(BaseModel):
    """Input used to create a project."""

    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=4000)
    base_url: str | None = Field(default=None, max_length=2048)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        """Remove unnecessary whitespace from the project name."""

        normalized = value.strip()

        if len(normalized) < 2:
            raise ValueError("Project name must contain at least two characters.")

        return normalized

    @field_validator("description", "base_url")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        """Normalize optional string values."""

        if value is None:
            return None

        normalized = value.strip()

        return normalized or None


class ProjectRead(BaseModel):
    """Project information returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None
    base_url: str | None
    openapi_version: str | None
    openapi_title: str | None
    spec_filename: str | None
    operation_count: int
    created_at: datetime
    updated_at: datetime
