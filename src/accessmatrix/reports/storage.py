"""Secure local report artifact persistence."""

import hashlib
import json
import os
import re
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import Lock
from uuid import uuid4

from pydantic import ValidationError

from accessmatrix.reports.models import (
    ReportArtifactMetadata,
    ReportFormat,
)

PROJECT_ID_PATTERN = re.compile(r"^[A-Za-z0-9-]{1,128}$")

REPORT_ID_PATTERN = re.compile(r"^[A-Za-z0-9-]{1,128}$")

FILENAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{1,240}$")

DEFAULT_MAX_REPORT_BYTES = 32 * 1024 * 1024

DEFAULT_MAX_METADATA_BYTES = 1024 * 1024

_WRITE_LOCK = Lock()


class ReportStorageError(RuntimeError):
    """Raised when report artifacts cannot be stored safely."""


@dataclass(
    frozen=True,
    slots=True,
)
class ReportArtifactInput:
    """Input used to persist one report artifact."""

    report_id: str
    project_id: str
    project_name: str

    title: str
    report_format: ReportFormat

    generated_at: datetime

    finding_count: int
    scan_count: int

    filename: str
    media_type: str
    content: bytes


class ReportRepository:
    """Persist report artifacts under project directories."""

    def __init__(
        self,
        storage_root: Path,
        *,
        max_report_bytes: int = (DEFAULT_MAX_REPORT_BYTES),
    ) -> None:
        """Initialize the report repository."""

        if max_report_bytes < 1:
            raise ValueError("The report size limit must be positive.")

        self._root = storage_root / "reports"

        self._max_report_bytes = max_report_bytes

    def _validate_identifier(
        self,
        value: str,
        *,
        pattern: re.Pattern[str],
        label: str,
    ) -> None:
        """Validate an identifier used in a path."""

        if pattern.fullmatch(value) is None:
            raise ReportStorageError(f"The {label} identifier is invalid.")

    def _project_directory(
        self,
        project_id: str,
    ) -> Path:
        """Return the project report directory."""

        self._validate_identifier(
            project_id,
            pattern=PROJECT_ID_PATTERN,
            label="project",
        )

        return self._root / project_id

    def _report_directory(
        self,
        project_id: str,
        report_id: str,
    ) -> Path:
        """Return the directory for one report."""

        self._validate_identifier(
            report_id,
            pattern=REPORT_ID_PATTERN,
            label="report",
        )

        return self._project_directory(project_id) / report_id

    def _metadata_path(
        self,
        project_id: str,
        report_id: str,
    ) -> Path:
        """Return the metadata path for one report."""

        return (
            self._report_directory(
                project_id,
                report_id,
            )
            / "metadata.json"
        )

    def _validate_filename(
        self,
        filename: str,
    ) -> None:
        """Reject unsafe artifact filenames."""

        if Path(filename).name != filename or FILENAME_PATTERN.fullmatch(filename) is None:
            raise ReportStorageError("The report filename is invalid.")

    def save(
        self,
        artifact: ReportArtifactInput,
    ) -> ReportArtifactMetadata:
        """Atomically persist report content and metadata."""

        self._validate_filename(artifact.filename)

        if len(artifact.content) > self._max_report_bytes:
            raise ReportStorageError("The report exceeds the configured size limit.")

        report_directory = self._report_directory(
            artifact.project_id,
            artifact.report_id,
        )

        artifact_path = report_directory / artifact.filename

        metadata_path = report_directory / "metadata.json"

        sha256 = hashlib.sha256(artifact.content).hexdigest()

        metadata = ReportArtifactMetadata(
            report_id=(artifact.report_id),
            project_id=(artifact.project_id),
            project_name=(artifact.project_name),
            title=artifact.title,
            report_format=(artifact.report_format),
            generated_at=(artifact.generated_at),
            finding_count=(artifact.finding_count),
            scan_count=(artifact.scan_count),
            filename=(artifact.filename),
            media_type=(artifact.media_type),
            size_bytes=len(artifact.content),
            sha256=sha256,
        )

        metadata_content = metadata.model_dump_json(
            indent=2,
        ).encode("utf-8")

        temporary_artifact_path = report_directory / (f".{artifact.filename}.{uuid4().hex}.tmp")

        temporary_metadata_path = report_directory / (f".metadata.{uuid4().hex}.tmp")

        try:
            report_directory.mkdir(
                parents=True,
                exist_ok=False,
            )

            with _WRITE_LOCK:
                temporary_artifact_path.write_bytes(artifact.content)

                os.replace(
                    temporary_artifact_path,
                    artifact_path,
                )

                temporary_metadata_path.write_bytes(metadata_content)

                os.replace(
                    temporary_metadata_path,
                    metadata_path,
                )

        except FileExistsError as exc:
            raise ReportStorageError("A report with this identifier already exists.") from exc

        except OSError as exc:
            raise ReportStorageError("The report could not be saved.") from exc

        finally:
            for temporary_path in (
                temporary_artifact_path,
                temporary_metadata_path,
            ):
                with suppress(OSError):
                    temporary_path.unlink(missing_ok=True)

        return metadata

    def load_metadata(
        self,
        project_id: str,
        report_id: str,
    ) -> ReportArtifactMetadata:
        """Load report metadata."""

        metadata_path = self._metadata_path(
            project_id,
            report_id,
        )

        if not metadata_path.is_file():
            raise ReportStorageError("The requested report does not exist.")

        try:
            metadata_size = metadata_path.stat().st_size

            if metadata_size > DEFAULT_MAX_METADATA_BYTES:
                raise ReportStorageError("The report metadata exceeds the configured size limit.")

            raw_content = metadata_path.read_text(encoding="utf-8")

            metadata = ReportArtifactMetadata.model_validate(json.loads(raw_content))

        except ReportStorageError:
            raise

        except (
            OSError,
            UnicodeError,
            json.JSONDecodeError,
            ValidationError,
        ) as exc:
            raise ReportStorageError("The report metadata is corrupted or invalid.") from exc

        if metadata.project_id != project_id:
            raise ReportStorageError(
                "The report project identifier does not match its storage location."
            )

        if metadata.report_id != report_id:
            raise ReportStorageError("The report identifier does not match its storage location.")

        self._validate_filename(metadata.filename)

        return metadata

    def artifact_path(
        self,
        project_id: str,
        report_id: str,
    ) -> Path:
        """Return a validated report artifact path."""

        metadata = self.load_metadata(
            project_id,
            report_id,
        )

        report_directory = self._report_directory(
            project_id,
            report_id,
        ).resolve()

        artifact_path = (report_directory / metadata.filename).resolve()

        if not artifact_path.is_relative_to(report_directory):
            raise ReportStorageError("The report artifact path is invalid.")

        if not artifact_path.is_file():
            raise ReportStorageError("The report artifact is missing.")

        try:
            artifact_size = artifact_path.stat().st_size

        except OSError as exc:
            raise ReportStorageError("The report artifact metadata could not be read.") from exc

        if artifact_size > self._max_report_bytes:
            raise ReportStorageError("The report exceeds the configured size limit.")

        return artifact_path

    def read_preview(
        self,
        project_id: str,
        report_id: str,
    ) -> str:
        """Read a UTF-8 report artifact for safe source preview."""

        artifact_path = self.artifact_path(
            project_id,
            report_id,
        )

        try:
            return artifact_path.read_text(encoding="utf-8")

        except (
            OSError,
            UnicodeError,
        ) as exc:
            raise ReportStorageError("The report preview could not be read.") from exc

    def list_metadata(
        self,
        project_id: str,
    ) -> list[ReportArtifactMetadata]:
        """List stored reports newest first."""

        project_directory = self._project_directory(project_id)

        if not project_directory.is_dir():
            return []

        reports: list[ReportArtifactMetadata] = []

        for report_directory in project_directory.iterdir():
            if not report_directory.is_dir():
                continue

            reports.append(
                self.load_metadata(
                    project_id,
                    report_directory.name,
                )
            )

        reports.sort(
            key=lambda report: report.generated_at,
            reverse=True,
        )

        return reports
