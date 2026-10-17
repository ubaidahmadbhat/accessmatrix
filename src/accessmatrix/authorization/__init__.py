"""Authorization dataset configuration for AccessMatrix."""

from accessmatrix.authorization.bola import (
    build_bola_test_plan,
)
from accessmatrix.authorization.demo_seed import (
    DemoAuthorizationSeedError,
    build_demo_authorization_dataset,
)
from accessmatrix.authorization.models import (
    AccessExpectation,
    AuthorizationCase,
    AuthorizationDataset,
    AuthorizationDatasetValidation,
    BOLATestPlan,
    BOLATestPlanItem,
    ObjectRecord,
    OperationObjectBinding,
    ResourceDefinition,
)
from accessmatrix.authorization.storage import (
    AuthorizationDatasetRepository,
    AuthorizationDatasetStorageError,
)
from accessmatrix.authorization.validation import (
    validate_authorization_dataset,
)

__all__ = [
    "AccessExpectation",
    "AuthorizationCase",
    "AuthorizationDataset",
    "AuthorizationDatasetRepository",
    "AuthorizationDatasetStorageError",
    "AuthorizationDatasetValidation",
    "BOLATestPlan",
    "BOLATestPlanItem",
    "DemoAuthorizationSeedError",
    "ObjectRecord",
    "OperationObjectBinding",
    "ResourceDefinition",
    "build_bola_test_plan",
    "build_demo_authorization_dataset",
    "validate_authorization_dataset",
]
