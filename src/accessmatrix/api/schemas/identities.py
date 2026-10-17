"""Identity profile API schemas."""

import re
from datetime import datetime
from typing import Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

AuthType = Literal[
    "none",
    "bearer",
    "api_key",
    "basic",
    "cookie",
    "custom_header",
]

SecretSource = Literal[
    "environment",
    "keyring",
]

AuthLocation = Literal[
    "header",
    "query",
    "cookie",
]

ENVIRONMENT_REFERENCE_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class IdentityPayload(BaseModel):
    """Shared identity creation and update fields."""

    name: str = Field(
        min_length=2,
        max_length=120,
    )

    description: str | None = Field(
        default=None,
        max_length=4000,
    )

    role: str = Field(
        min_length=1,
        max_length=120,
    )

    tenant: str | None = Field(
        default=None,
        max_length=120,
    )

    department: str | None = Field(
        default=None,
        max_length=120,
    )

    auth_type: AuthType = "none"

    secret_source: SecretSource = "environment"

    secret_reference: str | None = Field(
        default=None,
        max_length=255,
    )

    username_reference: str | None = Field(
        default=None,
        max_length=255,
    )

    password_reference: str | None = Field(
        default=None,
        max_length=255,
    )

    auth_location: AuthLocation | None = None

    auth_name: str | None = Field(
        default=None,
        max_length=255,
    )

    auth_prefix: str | None = Field(
        default=None,
        max_length=255,
    )

    enabled: bool = True

    @field_validator(
        "name",
        "role",
    )
    @classmethod
    def normalize_required_text(
        cls,
        value: str,
    ) -> str:
        """Normalize required text values."""

        normalized = value.strip()

        if not normalized:
            raise ValueError("The value must not be empty.")

        return normalized

    @field_validator(
        "description",
        "tenant",
        "department",
        "secret_reference",
        "username_reference",
        "password_reference",
        "auth_name",
        "auth_prefix",
    )
    @classmethod
    def normalize_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        """Normalize optional text values."""

        if value is None:
            return None

        normalized = value.strip()

        return normalized or None

    @model_validator(mode="after")
    def validate_authentication_configuration(
        self,
    ) -> Self:
        """Validate fields required by each authentication type."""

        references = (
            self.secret_reference,
            self.username_reference,
            self.password_reference,
        )

        if self.secret_source == "environment":
            for reference in references:
                if (
                    reference is not None
                    and ENVIRONMENT_REFERENCE_PATTERN.fullmatch(reference) is None
                ):
                    raise ValueError(
                        "Environment secret references must be valid environment-variable names."
                    )

        if self.auth_type == "none":
            self._reject_fields(
                {
                    "secret_reference": self.secret_reference,
                    "username_reference": self.username_reference,
                    "password_reference": self.password_reference,
                    "auth_location": self.auth_location,
                    "auth_name": self.auth_name,
                    "auth_prefix": self.auth_prefix,
                }
            )

            return self

        if self.auth_type == "bearer":
            self._require(
                self.secret_reference,
                "secret_reference",
            )

            self._reject_fields(
                {
                    "username_reference": self.username_reference,
                    "password_reference": self.password_reference,
                    "auth_location": self.auth_location,
                    "auth_name": self.auth_name,
                }
            )

            if self.auth_prefix is None:
                self.auth_prefix = "Bearer"

            return self

        if self.auth_type == "api_key":
            self._require(
                self.secret_reference,
                "secret_reference",
            )

            self._require(
                self.auth_name,
                "auth_name",
            )

            self._require(
                self.auth_location,
                "auth_location",
            )

            self._reject_fields(
                {
                    "username_reference": self.username_reference,
                    "password_reference": self.password_reference,
                }
            )

            return self

        if self.auth_type == "basic":
            self._require(
                self.username_reference,
                "username_reference",
            )

            self._require(
                self.password_reference,
                "password_reference",
            )

            self._reject_fields(
                {
                    "secret_reference": self.secret_reference,
                    "auth_location": self.auth_location,
                    "auth_name": self.auth_name,
                    "auth_prefix": self.auth_prefix,
                }
            )

            return self

        if self.auth_type == "cookie":
            self._require(
                self.secret_reference,
                "secret_reference",
            )

            self._require(
                self.auth_name,
                "auth_name",
            )

            if self.auth_location is not None and self.auth_location != "cookie":
                raise ValueError("Cookie authentication must use the cookie location.")

            self.auth_location = "cookie"

            self._reject_fields(
                {
                    "username_reference": self.username_reference,
                    "password_reference": self.password_reference,
                    "auth_prefix": self.auth_prefix,
                }
            )

            return self

        if self.auth_type == "custom_header":
            self._require(
                self.secret_reference,
                "secret_reference",
            )

            self._require(
                self.auth_name,
                "auth_name",
            )

            if self.auth_location is not None and self.auth_location != "header":
                raise ValueError("Custom-header authentication must use the header location.")

            self.auth_location = "header"

            self._reject_fields(
                {
                    "username_reference": self.username_reference,
                    "password_reference": self.password_reference,
                }
            )

            return self

        return self

    @staticmethod
    def _require(
        value: object,
        field_name: str,
    ) -> None:
        """Require a configured authentication field."""

        if value is None:
            raise ValueError(f"{field_name} is required for this authentication type.")

    @staticmethod
    def _reject_fields(
        fields: dict[str, object],
    ) -> None:
        """Reject authentication fields that are not applicable."""

        configured_fields = [
            field_name for field_name, value in fields.items() if value is not None
        ]

        if configured_fields:
            field_list = ", ".join(configured_fields)

            raise ValueError(
                "The following fields are not valid for the selected "
                f"authentication type: {field_list}."
            )


class IdentityCreate(IdentityPayload):
    """Input used to create an identity profile."""


class IdentityUpdate(IdentityPayload):
    """Input used to replace an identity profile."""


class IdentityRead(BaseModel):
    """Identity profile returned by the API."""

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: str
    project_id: str
    name: str
    description: str | None
    role: str
    tenant: str | None
    department: str | None
    auth_type: AuthType
    secret_source: SecretSource
    secret_reference: str | None
    username_reference: str | None
    password_reference: str | None
    auth_location: AuthLocation | None
    auth_name: str | None
    auth_prefix: str | None
    enabled: bool
    created_at: datetime
    updated_at: datetime
