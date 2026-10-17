"""Application settings and target validation routes."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from accessmatrix.api.schemas.settings import (
    ResetApplicationSettingsRequest,
    ValidateTargetRequest,
)
from accessmatrix.audit.models import (
    AuditEvent,
    AuditOutcome,
)
from accessmatrix.audit.storage import (
    AuditEventRepository,
    AuditStorageError,
)
from accessmatrix.persistence.storage import get_storage_root
from accessmatrix.security.target_validation import (
    TargetValidationResult,
    validate_target_url,
)
from accessmatrix.settings.models import ApplicationSettings
from accessmatrix.settings.storage import (
    ApplicationSettingsRepository,
    SettingsStorageError,
)

SETTINGS_RESET_CONFIRMATION = "RESET APPLICATION SETTINGS"

router = APIRouter(
    prefix="/api/v1/settings",
    tags=["Settings"],
)

StorageDependency = Annotated[
    Path,
    Depends(get_storage_root),
]


def build_settings_repository(
    storage_root: Path,
) -> ApplicationSettingsRepository:
    """Create the application settings repository."""

    return ApplicationSettingsRepository(storage_root)


def settings_storage_error(
    exc: SettingsStorageError,
) -> HTTPException:
    """Convert a settings storage error to an API error."""

    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=str(exc),
    )


def record_audit_event(
    *,
    storage_root: Path,
    settings: ApplicationSettings,
    event_type: str,
    outcome: AuditOutcome,
    message: str,
    details: dict[
        str,
        str | int | float | bool | None,
    ],
) -> None:
    """Persist and retain one settings-related audit event."""

    if not settings.audit.enabled:
        return

    repository = AuditEventRepository(storage_root)

    try:
        repository.save(
            AuditEvent(
                event_id=str(uuid4()),
                occurred_at=datetime.now(UTC),
                event_type=event_type,
                outcome=outcome,
                message=message,
                details=details,
            )
        )

        repository.prune(
            retention_days=(settings.audit.retention_days),
            max_events=(settings.audit.max_events),
        )

    except AuditStorageError as exc:
        raise HTTPException(
            status_code=(status.HTTP_500_INTERNAL_SERVER_ERROR),
            detail=(f"The operation completed, but the audit event could not be stored: {exc}"),
        ) from exc


@router.get(
    "",
    response_model=ApplicationSettings,
)
def read_application_settings(
    storage_root: StorageDependency,
) -> ApplicationSettings:
    """Read effective application settings."""

    repository = build_settings_repository(storage_root)

    try:
        return repository.load()

    except SettingsStorageError as exc:
        raise settings_storage_error(exc) from exc


@router.put(
    "",
    response_model=ApplicationSettings,
)
def replace_application_settings(
    payload: ApplicationSettings,
    storage_root: StorageDependency,
) -> ApplicationSettings:
    """Replace persistent application settings."""

    repository = build_settings_repository(storage_root)

    try:
        saved_settings = repository.save(payload)

    except SettingsStorageError as exc:
        raise settings_storage_error(exc) from exc

    record_audit_event(
        storage_root=storage_root,
        settings=saved_settings,
        event_type="settings.updated",
        outcome="success",
        message=("Application security settings were updated."),
        details={
            "network_access_mode": (saved_settings.network.access_mode),
            "rate_limit_requests": (saved_settings.execution.rate_limit_requests),
            "max_response_bytes": (saved_settings.execution.max_response_bytes),
            "audit_enabled": (saved_settings.audit.enabled),
        },
    )

    return saved_settings


@router.post(
    "/reset",
    response_model=ApplicationSettings,
)
def reset_application_settings(
    payload: ResetApplicationSettingsRequest,
    storage_root: StorageDependency,
) -> ApplicationSettings:
    """Reset persistent settings to secure defaults."""

    if payload.confirmation.strip() != SETTINGS_RESET_CONFIRMATION:
        raise HTTPException(
            status_code=(status.HTTP_409_CONFLICT),
            detail=(
                "Resetting application settings "
                "requires the exact confirmation "
                "phrase: "
                f"{SETTINGS_RESET_CONFIRMATION}"
            ),
        )

    repository = build_settings_repository(storage_root)

    try:
        settings = repository.reset()

    except SettingsStorageError as exc:
        raise settings_storage_error(exc) from exc

    record_audit_event(
        storage_root=storage_root,
        settings=settings,
        event_type="settings.reset",
        outcome="success",
        message=("Application settings were reset to secure defaults."),
        details={
            "confirmation_verified": True,
        },
    )

    return settings


@router.post(
    "/validate-target",
    response_model=TargetValidationResult,
)
def inspect_target_safety(
    payload: ValidateTargetRequest,
    storage_root: StorageDependency,
) -> TargetValidationResult:
    """Resolve and classify a target URL without executing a request."""

    repository = build_settings_repository(storage_root)

    try:
        settings = repository.load()

    except SettingsStorageError as exc:
        raise settings_storage_error(exc) from exc

    result = validate_target_url(
        payload.url,
        settings=(settings.network),
    )

    audit_outcome: AuditOutcome = "success" if result.permitted else "denied"

    record_audit_event(
        storage_root=storage_root,
        settings=settings,
        event_type="target.validation",
        outcome=audit_outcome,
        message=(
            "Target URL passed network policy validation."
            if result.permitted
            else ("Target URL did not pass network policy validation.")
        ),
        details={
            "hostname": (result.hostname),
            "scheme": (result.scheme),
            "port": (result.port),
            "address_count": len(result.addresses),
            "permitted": (result.permitted),
            "network_access_mode": (settings.network.access_mode),
        },
    )

    return result
