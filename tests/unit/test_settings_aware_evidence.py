"""Regression tests for settings-aware scan and report evidence limits."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from accessmatrix.api.routes.reports import build_report_repository
from accessmatrix.api.routes.reports import (
    build_scan_repository as build_report_scan_repository,
)
from accessmatrix.api.routes.scans import (
    build_scan_repository,
)
from accessmatrix.reports.storage import (
    ReportArtifactInput,
    ReportStorageError,
)
from accessmatrix.scanning.models import (
    BOLACaseResult,
    BOLAScan,
)
from accessmatrix.scanning.storage import (
    ScanStorageError,
)
from accessmatrix.settings.models import (
    ApplicationSettings,
    EvidenceSettings,
)

ONE_MIB = 1024 * 1024

PROJECT_ID = "project-1"


def build_settings(
    *,
    keep_latest: int = 2,
) -> ApplicationSettings:
    """Create evidence settings with minimum allowed storage limits."""

    return ApplicationSettings(
        evidence=EvidenceSettings(
            max_scan_bytes=ONE_MIB,
            max_report_bytes=ONE_MIB,
            scan_retention_keep_latest=keep_latest,
        )
    )


def build_scan(
    scan_id: str,
    *,
    completed_at: datetime,
    explanation: str = "Authorization request was denied as expected.",
) -> BOLAScan:
    """Create a small valid BOLA scan."""

    result = BOLACaseResult(
        case_id=f"case-{scan_id}",
        case_name="Invoice ownership test",
        operation_key="GET /invoices/{invoice_id}",
        identity_id="alice-id",
        identity_name="Customer Alice",
        resource_type="invoice",
        baseline_object_id="INV-1001",
        probe_object_id="INV-2001",
        expected_probe_status_codes=[
            401,
            403,
            404,
        ],
        outcome="pass",
        explanation=explanation,
        matching_response_fields={},
        issues=[],
        baseline_evidence=None,
        probe_evidence=None,
    )

    return BOLAScan(
        scan_id=scan_id,
        project_id=PROJECT_ID,
        started_at=(completed_at - timedelta(seconds=1)),
        completed_at=completed_at,
        status="completed",
        total_count=1,
        pass_count=1,
        finding_count=0,
        inconclusive_count=0,
        blocked_count=0,
        results=[
            result,
        ],
        findings=[],
    )


def test_scan_repository_honors_configured_size_limit(
    tmp_path: Path,
) -> None:
    """The scan API repository must use evidence.max_scan_bytes."""

    settings = build_settings()

    repository = build_scan_repository(
        tmp_path,
        settings,
    )

    oversized_scan = build_scan(
        "scan-large",
        completed_at=datetime.now(UTC),
        explanation="x" * (ONE_MIB + 4096),
    )

    with pytest.raises(
        ScanStorageError,
        match="configured size limit",
    ):
        repository.save(oversized_scan)


def test_report_repository_honors_configured_size_limit(
    tmp_path: Path,
) -> None:
    """The report API repository must use evidence.max_report_bytes."""

    settings = build_settings()

    repository = build_report_repository(
        tmp_path,
        settings,
    )

    artifact = ReportArtifactInput(
        report_id="report-large",
        project_id=PROJECT_ID,
        project_name="Local Invoice Demo",
        title="Oversized Authorization Report",
        report_format="json",
        generated_at=datetime.now(UTC),
        finding_count=0,
        scan_count=0,
        filename="report-large.json",
        media_type="application/json",
        content=b"x" * (ONE_MIB + 1),
    )

    with pytest.raises(
        ReportStorageError,
        match="configured size limit",
    ):
        repository.save(artifact)


def test_reporting_scan_repository_honors_scan_size_limit(
    tmp_path: Path,
) -> None:
    """Report generation must read scans with the configured scan limit."""

    settings = build_settings()

    repository = build_report_scan_repository(
        tmp_path,
        settings,
    )

    oversized_scan = build_scan(
        "scan-report-large",
        completed_at=datetime.now(UTC),
        explanation="x" * (ONE_MIB + 4096),
    )

    with pytest.raises(
        ScanStorageError,
        match="configured size limit",
    ):
        repository.save(oversized_scan)


def test_configured_scan_retention_keeps_only_newest_scans(
    tmp_path: Path,
) -> None:
    """Configured retention must preserve only the newest scan evidence."""

    settings = build_settings(keep_latest=2)

    repository = build_scan_repository(
        tmp_path,
        settings,
    )

    base_time = datetime(
        2026,
        10,
        17,
        12,
        0,
        tzinfo=UTC,
    )

    scans = [
        build_scan(
            "scan-1",
            completed_at=base_time,
        ),
        build_scan(
            "scan-2",
            completed_at=(base_time + timedelta(minutes=1)),
        ),
        build_scan(
            "scan-3",
            completed_at=(base_time + timedelta(minutes=2)),
        ),
        build_scan(
            "scan-4",
            completed_at=(base_time + timedelta(minutes=3)),
        ),
    ]

    for scan in scans:
        repository.save(scan)

    deleted_scan_ids = repository.prune(
        PROJECT_ID,
        keep_latest=(settings.evidence.scan_retention_keep_latest),
    )

    remaining = repository.list_summaries(PROJECT_ID)

    assert deleted_scan_ids == [
        "scan-2",
        "scan-1",
    ]

    assert [scan.scan_id for scan in remaining] == [
        "scan-4",
        "scan-3",
    ]
