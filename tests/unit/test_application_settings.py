"""Unit tests for application settings and target validation."""

from datetime import (
    UTC,
    datetime,
    timedelta,
)
from pathlib import Path
from uuid import uuid4

from accessmatrix.audit.models import (
    AuditEvent,
)
from accessmatrix.audit.storage import (
    AuditEventRepository,
)
from accessmatrix.security.target_validation import (
    validate_target_url,
)
from accessmatrix.settings.models import (
    ApplicationSettings,
    NetworkSafetySettings,
)
from accessmatrix.settings.storage import (
    ApplicationSettingsRepository,
)


def test_settings_repository_returns_defaults(
    tmp_path: Path,
) -> None:
    """Missing settings should return secure defaults."""

    repository = ApplicationSettingsRepository(tmp_path)

    settings = repository.load()

    assert settings.network.access_mode == "public_and_loopback"

    assert settings.audit.enabled is True


def test_settings_repository_round_trip(
    tmp_path: Path,
) -> None:
    """Stored settings should load without data loss."""

    repository = ApplicationSettingsRepository(tmp_path)

    settings = ApplicationSettings()

    settings.execution.rate_limit_requests = 75

    repository.save(settings)

    loaded = repository.load()

    assert loaded == settings


def test_settings_repository_reset(
    tmp_path: Path,
) -> None:
    """Reset should restore secure defaults."""

    repository = ApplicationSettingsRepository(tmp_path)

    settings = ApplicationSettings()

    settings.network.access_mode = "private_networks"

    repository.save(settings)

    reset_settings = repository.reset()

    assert reset_settings.network.access_mode == "public_and_loopback"


def test_public_ip_is_allowed() -> None:
    """A global literal address should pass public-only policy."""

    result = validate_target_url(
        "https://8.8.8.8",
        settings=NetworkSafetySettings(access_mode="public_only"),
    )

    assert result.valid is True
    assert result.permitted is True

    assert result.addresses[0].classification == "global"


def test_loopback_is_denied_by_public_only_policy() -> None:
    """Loopback should be denied by public-only policy."""

    result = validate_target_url(
        "http://127.0.0.1:9000",
        settings=NetworkSafetySettings(access_mode="public_only"),
    )

    assert result.valid is True
    assert result.permitted is False

    assert result.addresses[0].classification == "loopback"


def test_loopback_is_allowed_by_default_policy() -> None:
    """The demonstration API should remain permitted by default."""

    result = validate_target_url(
        "http://127.0.0.1:9000",
        settings=(NetworkSafetySettings()),
    )

    assert result.valid is True
    assert result.permitted is True


def test_private_ip_requires_private_network_mode() -> None:
    """RFC1918 targets require explicit private-network access."""

    denied = validate_target_url(
        "https://192.168.0.20",
        settings=(NetworkSafetySettings()),
    )

    permitted = validate_target_url(
        "https://192.168.0.20",
        settings=NetworkSafetySettings(access_mode="private_networks"),
    )

    assert denied.permitted is False
    assert permitted.permitted is True


def test_link_local_requires_explicit_permission() -> None:
    """Link-local access requires its dedicated control."""

    denied = validate_target_url(
        "http://169.254.10.10",
        settings=NetworkSafetySettings(access_mode="private_networks"),
    )

    permitted = validate_target_url(
        "http://169.254.10.10",
        settings=NetworkSafetySettings(
            access_mode="private_networks",
            allow_link_local=True,
        ),
    )

    assert denied.permitted is False
    assert permitted.permitted is True


def test_target_credentials_are_rejected() -> None:
    """Target URLs must not embed credentials."""

    result = validate_target_url(
        "https://admin:secret@8.8.8.8",
        settings=(NetworkSafetySettings()),
    )

    assert result.valid is False
    assert result.permitted is False

    assert any("credentials" in issue.lower() for issue in result.issues)


def test_target_query_and_fragment_are_rejected() -> None:
    """Base URLs must not contain queries or fragments."""

    result = validate_target_url(
        "https://8.8.8.8/api?key=value#section",
        settings=(NetworkSafetySettings()),
    )

    assert result.valid is False

    assert len(result.issues) == 2


def build_audit_event(
    *,
    occurred_at: datetime,
    event_type: str,
) -> AuditEvent:
    """Create a test audit event."""

    return AuditEvent(
        event_id=str(uuid4()),
        occurred_at=occurred_at,
        event_type=event_type,
        outcome="success",
        message="Test audit event.",
        details={
            "test": True,
        },
    )


def test_audit_repository_lists_newest_first(
    tmp_path: Path,
) -> None:
    """Audit events should be returned newest first."""

    repository = AuditEventRepository(tmp_path)

    first_time = datetime(
        2026,
        8,
        1,
        10,
        0,
        tzinfo=UTC,
    )

    second_time = first_time + timedelta(hours=1)

    first = build_audit_event(
        occurred_at=first_time,
        event_type="test.first",
    )

    second = build_audit_event(
        occurred_at=second_time,
        event_type="test.second",
    )

    repository.save(first)

    repository.save(second)

    events = repository.list_latest(limit=10)

    assert [event.event_id for event in events] == [
        second.event_id,
        first.event_id,
    ]


def test_audit_retention_removes_old_events(
    tmp_path: Path,
) -> None:
    """Age-based audit retention should remove older events."""

    repository = AuditEventRepository(tmp_path)

    now = datetime(
        2026,
        8,
        10,
        10,
        0,
        tzinfo=UTC,
    )

    old_event = build_audit_event(
        occurred_at=(now - timedelta(days=20)),
        event_type="test.old",
    )

    current_event = build_audit_event(
        occurred_at=now,
        event_type="test.current",
    )

    repository.save(old_event)

    repository.save(current_event)

    deleted_count = repository.prune(
        retention_days=5,
        max_events=100,
        now=now,
    )

    assert deleted_count == 1

    events = repository.list_latest(limit=10)

    assert [event.event_id for event in events] == [
        current_event.event_id,
    ]
