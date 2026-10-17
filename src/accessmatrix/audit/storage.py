"""Local audit-event persistence and retention."""

import json
import os
import re
from contextlib import suppress
from datetime import (
    UTC,
    datetime,
    timedelta,
)
from pathlib import Path
from threading import Lock
from uuid import uuid4

from pydantic import ValidationError

from accessmatrix.audit.models import (
    AuditEvent,
)

EVENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9-]{1,128}$")

DEFAULT_MAX_EVENT_BYTES = 256 * 1024

_WRITE_LOCK = Lock()


class AuditStorageError(RuntimeError):
    """Raised when audit events cannot be stored safely."""


class AuditEventRepository:
    """Persist immutable audit events as individual JSON files."""

    def __init__(
        self,
        storage_root: Path,
        *,
        max_event_bytes: int = (DEFAULT_MAX_EVENT_BYTES),
    ) -> None:
        """Initialize the audit repository."""

        if max_event_bytes < 1:
            raise ValueError("The audit event size limit must be positive.")

        self._root = storage_root / "audit-events"

        self._max_event_bytes = max_event_bytes

    def _validate_event_id(
        self,
        event_id: str,
    ) -> None:
        """Reject unsafe audit event identifiers."""

        if EVENT_ID_PATTERN.fullmatch(event_id) is None:
            raise AuditStorageError("The audit event identifier is invalid.")

    def _event_path(
        self,
        event: AuditEvent,
    ) -> Path:
        """Return the path for one audit event."""

        self._validate_event_id(event.event_id)

        day = event.occurred_at.astimezone(UTC).strftime("%Y-%m-%d")

        return self._root / day / f"{event.event_id}.json"

    def _load_path(
        self,
        event_path: Path,
    ) -> AuditEvent:
        """Load and validate one event file."""

        try:
            file_size = event_path.stat().st_size

            if file_size > self._max_event_bytes:
                raise AuditStorageError("An audit event exceeds the configured size limit.")

            raw_content = event_path.read_text(encoding="utf-8")

            event = AuditEvent.model_validate(json.loads(raw_content))

        except AuditStorageError:
            raise

        except (
            OSError,
            UnicodeError,
            json.JSONDecodeError,
            ValidationError,
        ) as exc:
            raise AuditStorageError("An audit event is corrupted or invalid.") from exc

        if event_path.stem != event.event_id:
            raise AuditStorageError(
                "An audit event identifier does not match its storage location."
            )

        return event

    def _event_paths(
        self,
    ) -> list[Path]:
        """Return all persisted audit event paths."""

        if not self._root.is_dir():
            return []

        return [event_path for event_path in self._root.glob("*/*.json") if event_path.is_file()]

    def save(
        self,
        event: AuditEvent,
    ) -> AuditEvent:
        """Atomically persist one immutable audit event."""

        event_path = self._event_path(event)

        serialized = json.dumps(
            event.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )

        encoded_content = serialized.encode("utf-8")

        if len(encoded_content) > self._max_event_bytes:
            raise AuditStorageError("The audit event exceeds the configured size limit.")

        temporary_path = event_path.with_name(f".{event_path.name}.{uuid4().hex}.tmp")

        try:
            event_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            with _WRITE_LOCK:
                if event_path.exists():
                    raise AuditStorageError("The audit event already exists.")

                temporary_path.write_bytes(encoded_content)

                os.replace(
                    temporary_path,
                    event_path,
                )

        except AuditStorageError:
            raise

        except OSError as exc:
            raise AuditStorageError("The audit event could not be saved.") from exc

        finally:
            with suppress(OSError):
                temporary_path.unlink(missing_ok=True)

        return event

    def list_latest(
        self,
        *,
        limit: int = 100,
    ) -> list[AuditEvent]:
        """List the newest audit events."""

        if not (1 <= limit <= 500):
            raise ValueError("The audit-event limit must be between 1 and 500.")

        events = [self._load_path(event_path) for event_path in self._event_paths()]

        events.sort(
            key=lambda event: event.occurred_at,
            reverse=True,
        )

        return events[:limit]

    def prune(
        self,
        *,
        retention_days: int,
        max_events: int,
        now: datetime | None = None,
    ) -> int:
        """Apply age and maximum-count audit retention."""

        if retention_days < 1:
            raise ValueError("Audit retention must be at least one day.")

        if max_events < 1:
            raise ValueError("At least one audit event must be retained.")

        reference_time = now if now is not None else datetime.now(UTC)

        if reference_time.tzinfo is None:
            reference_time = reference_time.replace(tzinfo=UTC)

        cutoff = reference_time - timedelta(days=retention_days)

        events_with_paths = [
            (
                self._load_path(event_path),
                event_path,
            )
            for event_path in self._event_paths()
        ]

        events_with_paths.sort(
            key=lambda item: item[0].occurred_at,
            reverse=True,
        )

        deleted_count = 0

        for (
            index,
            (
                event,
                event_path,
            ),
        ) in enumerate(events_with_paths):
            should_delete = event.occurred_at < cutoff or index >= max_events

            if not should_delete:
                continue

            try:
                with _WRITE_LOCK:
                    event_path.unlink()

                deleted_count += 1

            except OSError as exc:
                raise AuditStorageError("An audit event could not be removed.") from exc

            with suppress(OSError):
                event_path.parent.rmdir()

        with suppress(OSError):
            self._root.rmdir()

        return deleted_count
