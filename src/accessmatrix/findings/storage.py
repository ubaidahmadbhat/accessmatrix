"""Local persistence and deduplication for findings."""

import hashlib
import json
import os
import re
from contextlib import suppress
from datetime import (
    UTC,
    datetime,
)
from pathlib import Path
from threading import Lock
from uuid import uuid4

from pydantic import (
    ValidationError,
)

from accessmatrix.findings.models import (
    FindingRecord,
    FindingStatus,
)
from accessmatrix.scanning.models import (
    BOLAFinding,
    BOLAScan,
)

PROJECT_ID_PATTERN = re.compile(r"^[A-Za-z0-9-]{1,128}$")

FINGERPRINT_PATTERN = re.compile(r"^[a-f0-9]{64}$")

DEFAULT_MAX_FINDING_BYTES = 2 * 1024 * 1024

_WRITE_LOCK = Lock()


class FindingStorageError(RuntimeError):
    """Raised when findings cannot be read or stored safely."""


def build_finding_fingerprint(
    project_id: str,
    finding: BOLAFinding,
) -> str:
    """Build a stable deduplication fingerprint."""

    fingerprint_input = {
        "version": 1,
        "project_id": project_id,
        "category": finding.category,
        "operation_key": finding.operation_key,
        "identity_id": finding.identity_id,
        "resource_type": finding.resource_type,
        "probe_object_id": finding.probe_object_id,
    }

    canonical_content = json.dumps(
        fingerprint_input,
        ensure_ascii=True,
        separators=(
            ",",
            ":",
        ),
        sort_keys=True,
    ).encode()

    return hashlib.sha256(canonical_content).hexdigest()


def append_unique(
    values: list[str],
    value: str,
) -> list[str]:
    """Append a string only when it is not already present."""

    if value in values:
        return list(values)

    return [
        *values,
        value,
    ]


class FindingRepository:
    """Persist deduplicated findings per project."""

    def __init__(
        self,
        storage_root: Path,
        *,
        max_finding_bytes: int = DEFAULT_MAX_FINDING_BYTES,
    ) -> None:
        """Initialize the finding repository."""

        if max_finding_bytes < 1:
            raise ValueError("The finding size limit must be positive.")

        self._root = storage_root / "findings"

        self._max_finding_bytes = max_finding_bytes

    def _validate_identifier(
        self,
        value: str,
        *,
        pattern: re.Pattern[str],
        label: str,
    ) -> None:
        """Validate an identifier used in a file path."""

        if pattern.fullmatch(value) is None:
            raise FindingStorageError(f"The {label} identifier is invalid.")

    def _project_directory(
        self,
        project_id: str,
    ) -> Path:
        """Return the finding directory for a project."""

        self._validate_identifier(
            project_id,
            pattern=PROJECT_ID_PATTERN,
            label="project",
        )

        return self._root / project_id

    def _finding_path(
        self,
        project_id: str,
        fingerprint: str,
    ) -> Path:
        """Return the path for one finding."""

        self._validate_identifier(
            fingerprint,
            pattern=FINGERPRINT_PATTERN,
            label="finding fingerprint",
        )

        return self._project_directory(project_id) / f"{fingerprint}.json"

    def _load_optional(
        self,
        project_id: str,
        fingerprint: str,
    ) -> FindingRecord | None:
        """Load a finding when it exists."""

        finding_path = self._finding_path(
            project_id,
            fingerprint,
        )

        if not finding_path.is_file():
            return None

        return self.load(
            project_id,
            fingerprint,
        )

    def save(
        self,
        finding: FindingRecord,
    ) -> FindingRecord:
        """Atomically persist one finding."""

        finding_path = self._finding_path(
            finding.project_id,
            finding.fingerprint,
        )

        serialized = json.dumps(
            finding.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )

        encoded_content = serialized.encode()

        if len(encoded_content) > self._max_finding_bytes:
            raise FindingStorageError("The finding exceeds the configured size limit.")

        temporary_path = finding_path.with_name(f".{finding_path.name}.{uuid4().hex}.tmp")

        try:
            finding_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            with _WRITE_LOCK:
                temporary_path.write_bytes(encoded_content)

                os.replace(
                    temporary_path,
                    finding_path,
                )

        except OSError as exc:
            raise FindingStorageError("The finding could not be saved.") from exc

        finally:
            with suppress(OSError):
                temporary_path.unlink(missing_ok=True)

        return finding

    def load(
        self,
        project_id: str,
        fingerprint: str,
    ) -> FindingRecord:
        """Load one finding."""

        finding_path = self._finding_path(
            project_id,
            fingerprint,
        )

        if not finding_path.is_file():
            raise FindingStorageError("The requested finding does not exist.")

        try:
            file_size = finding_path.stat().st_size

            if file_size > self._max_finding_bytes:
                raise FindingStorageError("The finding exceeds the configured size limit.")

            raw_content = finding_path.read_text(encoding="utf-8")

            parsed_content = json.loads(raw_content)

            finding = FindingRecord.model_validate(parsed_content)

        except FindingStorageError:
            raise

        except (
            OSError,
            UnicodeError,
            json.JSONDecodeError,
            ValidationError,
        ) as exc:
            raise FindingStorageError("The finding is corrupted or invalid.") from exc

        if finding.project_id != project_id:
            raise FindingStorageError(
                "The finding project identifier does not match its storage location."
            )

        if finding.fingerprint != fingerprint:
            raise FindingStorageError(
                "The finding fingerprint does not match its storage location."
            )

        return finding

    def list_all(
        self,
        project_id: str,
    ) -> list[FindingRecord]:
        """List project findings newest first."""

        project_directory = self._project_directory(project_id)

        if not project_directory.is_dir():
            return []

        findings: list[FindingRecord] = []

        for finding_path in project_directory.glob("*.json"):
            findings.append(
                self.load(
                    project_id,
                    finding_path.stem,
                )
            )

        findings.sort(
            key=lambda finding: (
                finding.last_seen_at,
                finding.updated_at,
            ),
            reverse=True,
        )

        return findings

    def update_status(
        self,
        *,
        project_id: str,
        fingerprint: str,
        status: FindingStatus,
        note: str | None,
    ) -> FindingRecord:
        """Update a finding lifecycle status."""

        existing = self.load(
            project_id,
            fingerprint,
        )

        normalized_note = note.strip() if note is not None else None

        if normalized_note == "":
            normalized_note = None

        updated = FindingRecord.model_validate(
            {
                **existing.model_dump(mode="python"),
                "status": status,
                "resolution_note": (normalized_note),
                "updated_at": (datetime.now(UTC)),
            }
        )

        return self.save(updated)

    def upsert_scan(
        self,
        scan: BOLAScan,
    ) -> list[FindingRecord]:
        """Ingest and deduplicate all findings from a scan."""

        records: list[FindingRecord] = []

        for finding in scan.findings:
            fingerprint = build_finding_fingerprint(
                scan.project_id,
                finding,
            )

            existing = self._load_optional(
                scan.project_id,
                fingerprint,
            )

            if existing is not None and scan.scan_id in existing.scan_ids:
                records.append(existing)

                continue

            if existing is None:
                record = FindingRecord(
                    finding_id=str(uuid4()),
                    fingerprint=fingerprint,
                    project_id=(scan.project_id),
                    category=(finding.category),
                    title=(finding.title),
                    description=(finding.description),
                    severity=(finding.severity),
                    confidence=(finding.confidence),
                    status="open",
                    operation_key=(finding.operation_key),
                    identity_id=(finding.identity_id),
                    identity_name=(finding.identity_name),
                    resource_type=(finding.resource_type),
                    baseline_object_id=(finding.baseline_object_id),
                    probe_object_id=(finding.probe_object_id),
                    first_seen_at=(scan.completed_at),
                    last_seen_at=(scan.completed_at),
                    updated_at=(scan.completed_at),
                    occurrence_count=1,
                    reopened_count=0,
                    last_observed_status_code=(finding.observed_status_code),
                    matching_response_fields=(finding.matching_response_fields),
                    scan_ids=[
                        scan.scan_id,
                    ],
                    source_finding_ids=[
                        finding.finding_id,
                    ],
                    resolution_note=None,
                )

                records.append(self.save(record))

                continue

            is_newer_observation = scan.completed_at >= existing.last_seen_at

            next_status = existing.status

            next_note = existing.resolution_note

            next_reopened_count = existing.reopened_count

            if existing.status == "resolved" and is_newer_observation:
                next_status = "open"
                next_note = None

                next_reopened_count += 1

            scan_ids = append_unique(
                existing.scan_ids,
                scan.scan_id,
            )

            source_finding_ids = append_unique(
                existing.source_finding_ids,
                finding.finding_id,
            )

            updated_values = {
                **existing.model_dump(mode="python"),
                "first_seen_at": min(
                    existing.first_seen_at,
                    scan.completed_at,
                ),
                "last_seen_at": max(
                    existing.last_seen_at,
                    scan.completed_at,
                ),
                "updated_at": (datetime.now(UTC)),
                "occurrence_count": len(scan_ids),
                "reopened_count": (next_reopened_count),
                "status": next_status,
                "resolution_note": (next_note),
                "scan_ids": scan_ids,
                "source_finding_ids": (source_finding_ids),
            }

            if is_newer_observation:
                updated_values.update(
                    {
                        "title": (finding.title),
                        "description": (finding.description),
                        "severity": (finding.severity),
                        "confidence": (finding.confidence),
                        "identity_name": (finding.identity_name),
                        "baseline_object_id": (finding.baseline_object_id),
                        "last_observed_status_code": (finding.observed_status_code),
                        "matching_response_fields": (finding.matching_response_fields),
                    }
                )

            record = FindingRecord.model_validate(updated_values)

            records.append(self.save(record))

        return records
