"""Local persistence for BOLA scan results."""

import json
import os
import re
from contextlib import suppress
from pathlib import Path
from threading import Lock
from uuid import uuid4

from pydantic import (
    ValidationError,
)

from accessmatrix.scanning.models import (
    BOLAScan,
    BOLAScanSummary,
)

PROJECT_ID_PATTERN = re.compile(r"^[A-Za-z0-9-]{1,128}$")

SCAN_ID_PATTERN = re.compile(r"^[A-Za-z0-9-]{1,128}$")

DEFAULT_MAX_SCAN_BYTES = 16 * 1024 * 1024

_WRITE_LOCK = Lock()


class ScanStorageError(RuntimeError):
    """Raised when scan data cannot be safely read or stored."""


class BOLAScanRepository:
    """Persist BOLA scans under project-specific directories."""

    def __init__(
        self,
        storage_root: Path,
        *,
        max_scan_bytes: int = (DEFAULT_MAX_SCAN_BYTES),
    ) -> None:
        """Initialize the scan repository."""

        if max_scan_bytes < 1:
            raise ValueError("The scan size limit must be positive.")

        self._root = storage_root / "bola-scans"

        self._max_scan_bytes = max_scan_bytes

    def _validate_identifier(
        self,
        value: str,
        *,
        pattern: re.Pattern[str],
        label: str,
    ) -> None:
        """Validate a path identifier."""

        if pattern.fullmatch(value) is None:
            raise ScanStorageError(f"The {label} identifier is invalid.")

    def _project_directory(
        self,
        project_id: str,
    ) -> Path:
        """Return the scan directory for a project."""

        self._validate_identifier(
            project_id,
            pattern=PROJECT_ID_PATTERN,
            label="project",
        )

        return self._root / project_id

    def _scan_path(
        self,
        project_id: str,
        scan_id: str,
    ) -> Path:
        """Return the path for one scan."""

        self._validate_identifier(
            scan_id,
            pattern=SCAN_ID_PATTERN,
            label="scan",
        )

        return self._project_directory(project_id) / f"{scan_id}.json"

    def save(
        self,
        scan: BOLAScan,
    ) -> BOLAScan:
        """Atomically persist a scan."""

        scan_path = self._scan_path(
            scan.project_id,
            scan.scan_id,
        )

        serialized = json.dumps(
            scan.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )

        encoded_content = serialized.encode("utf-8")

        if len(encoded_content) > self._max_scan_bytes:
            raise ScanStorageError("The scan result exceeds the configured size limit.")

        temporary_path = scan_path.with_name(f".{scan_path.name}.{uuid4().hex}.tmp")

        try:
            scan_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            with _WRITE_LOCK:
                temporary_path.write_bytes(encoded_content)

                os.replace(
                    temporary_path,
                    scan_path,
                )

        except OSError as exc:
            raise ScanStorageError("The scan result could not be saved.") from exc

        finally:
            with suppress(OSError):
                temporary_path.unlink(missing_ok=True)

        return scan

    def load(
        self,
        project_id: str,
        scan_id: str,
    ) -> BOLAScan:
        """Load one persisted scan."""

        scan_path = self._scan_path(
            project_id,
            scan_id,
        )

        if not scan_path.is_file():
            raise ScanStorageError("The requested scan does not exist.")

        try:
            file_size = scan_path.stat().st_size

            if file_size > self._max_scan_bytes:
                raise ScanStorageError("The scan result exceeds the configured size limit.")

            raw_content = scan_path.read_text(encoding="utf-8")

            parsed_content = json.loads(raw_content)

            scan = BOLAScan.model_validate(parsed_content)

        except ScanStorageError:
            raise

        except (
            OSError,
            UnicodeError,
            json.JSONDecodeError,
            ValidationError,
        ) as exc:
            raise ScanStorageError("The scan result is corrupted or invalid.") from exc

        if scan.project_id != project_id:
            raise ScanStorageError(
                "The scan project identifier does not match its storage location."
            )

        if scan.scan_id != scan_id:
            raise ScanStorageError("The scan identifier does not match its storage location.")

        return scan

    def list_summaries(
        self,
        project_id: str,
    ) -> list[BOLAScanSummary]:
        """List persisted scans newest first."""

        project_directory = self._project_directory(project_id)

        if not project_directory.is_dir():
            return []

        summaries: list[BOLAScanSummary] = []

        for scan_path in project_directory.glob("*.json"):
            scan = self.load(
                project_id,
                scan_path.stem,
            )

            summaries.append(
                BOLAScanSummary(
                    scan_id=scan.scan_id,
                    project_id=(scan.project_id),
                    started_at=(scan.started_at),
                    completed_at=(scan.completed_at),
                    status=scan.status,
                    total_count=(scan.total_count),
                    pass_count=(scan.pass_count),
                    finding_count=(scan.finding_count),
                    inconclusive_count=(scan.inconclusive_count),
                    blocked_count=(scan.blocked_count),
                )
            )

        summaries.sort(
            key=lambda summary: summary.completed_at,
            reverse=True,
        )

        return summaries

    def delete(
        self,
        project_id: str,
        scan_id: str,
    ) -> None:
        """Delete one persisted scan evidence file."""

        scan_path = self._scan_path(
            project_id,
            scan_id,
        )

        if not scan_path.is_file():
            raise ScanStorageError("The requested scan does not exist.")

        try:
            with _WRITE_LOCK:
                scan_path.unlink()

        except OSError as exc:
            raise ScanStorageError("The scan result could not be deleted.") from exc

        project_directory = self._project_directory(project_id)

        with suppress(OSError):
            project_directory.rmdir()

    def prune(
        self,
        project_id: str,
        *,
        keep_latest: int,
    ) -> list[str]:
        """Delete all but the newest requested scan count."""

        if keep_latest < 1:
            raise ValueError("At least one scan must be retained.")

        summaries = self.list_summaries(project_id)

        deleted_scan_ids: list[str] = []

        for summary in summaries[keep_latest:]:
            self.delete(
                project_id,
                summary.scan_id,
            )

            deleted_scan_ids.append(summary.scan_id)

        return deleted_scan_ids
