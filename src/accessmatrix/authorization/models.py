"""Authorization dataset domain models."""

from typing import Literal
from uuid import uuid4

from pydantic import (
    BaseModel,
    Field,
)

AccessExpectation = Literal[
    "allow",
    "deny",
]


class ResourceDefinition(BaseModel):
    """An API resource type containing protected objects."""

    name: str = Field(
        min_length=1,
        max_length=64,
        pattern=(
            r"^[A-Za-z]"
            r"[A-Za-z0-9_.-]{0,63}$"
        ),
    )

    display_name: str = Field(
        min_length=1,
        max_length=120,
    )

    description: str | None = Field(
        default=None,
        max_length=2000,
    )


class ObjectRecord(BaseModel):
    """A known object and its expected ownership."""

    resource_type: str = Field(
        min_length=1,
        max_length=64,
    )

    object_id: str = Field(
        min_length=1,
        max_length=2048,
    )

    display_name: str | None = Field(
        default=None,
        max_length=200,
    )

    owner_identity_id: str | None = Field(
        default=None,
        max_length=128,
    )

    tenant: str | None = Field(
        default=None,
        max_length=200,
    )

    attributes: dict[
        str,
        str,
    ] = Field(
        default_factory=dict,
    )


class OperationObjectBinding(BaseModel):
    """Bind an imported operation to an object resource."""

    operation_key: str = Field(
        min_length=3,
        max_length=4096,
    )

    resource_type: str = Field(
        min_length=1,
        max_length=64,
    )

    path_parameter: str = Field(
        min_length=1,
        max_length=256,
    )

    response_id_field: str | None = Field(
        default=None,
        max_length=256,
    )

    response_owner_field: str | None = Field(
        default=None,
        max_length=256,
    )

    response_tenant_field: str | None = Field(
        default=None,
        max_length=256,
    )


class AuthorizationCase(BaseModel):
    """An expected access result for an identity and object."""

    case_id: str = Field(
        default_factory=lambda: str(uuid4()),
        min_length=1,
        max_length=128,
    )

    name: str = Field(
        min_length=1,
        max_length=200,
    )

    operation_key: str = Field(
        min_length=3,
        max_length=4096,
    )

    identity_id: str = Field(
        min_length=1,
        max_length=128,
    )

    resource_type: str = Field(
        min_length=1,
        max_length=64,
    )

    object_id: str = Field(
        min_length=1,
        max_length=2048,
    )

    expectation: AccessExpectation

    expected_status_codes: list[int] = Field(
        default_factory=list,
    )

    enabled: bool = True


class AuthorizationDataset(BaseModel):
    """Complete authorization dataset for one project."""

    version: Literal[1] = 1

    resources: list[ResourceDefinition] = Field(
        default_factory=list,
    )

    objects: list[ObjectRecord] = Field(
        default_factory=list,
    )

    bindings: list[OperationObjectBinding] = Field(
        default_factory=list,
    )

    cases: list[AuthorizationCase] = Field(
        default_factory=list,
    )


class AuthorizationDatasetValidation(BaseModel):
    """Validation result for an authorization dataset."""

    valid: bool
    issue_count: int
    issues: list[str]


class BOLATestPlanItem(BaseModel):
    """One comparative cross-object BOLA test."""

    case_id: str
    case_name: str

    operation_key: str

    identity_id: str
    identity_name: str

    resource_type: str
    path_parameter: str | None

    baseline_object_id: str | None
    probe_object_id: str

    probe_owner_identity_id: str | None
    probe_owner_identity_name: str | None

    baseline_path_parameters: dict[
        str,
        str,
    ] = Field(
        default_factory=dict,
    )

    probe_path_parameters: dict[
        str,
        str,
    ] = Field(
        default_factory=dict,
    )

    expected_probe_status_codes: list[int] = Field(
        default_factory=list,
    )

    ready: bool
    issues: list[str]


class BOLATestPlan(BaseModel):
    """Generated BOLA test plan for a project."""

    project_id: str
    total_count: int
    ready_count: int
    blocked_count: int

    items: list[BOLATestPlanItem]
