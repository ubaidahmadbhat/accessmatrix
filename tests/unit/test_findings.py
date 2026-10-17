"""Unit tests for central finding management."""

from datetime import (
    UTC,
    datetime,
    timedelta,
)
from pathlib import Path

from accessmatrix.findings.storage import (
    FindingRepository,
    build_finding_fingerprint,
)
from accessmatrix.scanning.models import (
    BOLAFinding,
    BOLAScan,
)


def build_bola_finding(
    *,
    finding_id: str,
    observed_status_code: int = 200,
) -> BOLAFinding:
    """Create a demonstration BOLA finding."""

    return BOLAFinding(
        finding_id=finding_id,
        case_id="alice-bob-invoice",
        title=("Broken object-level authorization detected"),
        description=("Customer Alice accessed Bob's invoice."),
        severity="high",
        confidence="high",
        operation_key=("GET /invoices/{invoice_id}"),
        identity_id="alice-id",
        identity_name="Customer Alice",
        resource_type="invoice",
        baseline_object_id="INV-1001",
        probe_object_id="INV-2001",
        observed_status_code=(observed_status_code),
        matching_response_fields={
            "invoice_id": True,
            "owner_id": True,
            "tenant_id": True,
        },
    )


def build_scan(
    *,
    scan_id: str,
    completed_at: datetime,
    finding_id: str,
) -> BOLAScan:
    """Create a completed scan containing one finding."""

    return BOLAScan(
        scan_id=scan_id,
        project_id="project-1",
        started_at=(completed_at - timedelta(seconds=2)),
        completed_at=completed_at,
        status="completed",
        total_count=1,
        pass_count=0,
        finding_count=1,
        inconclusive_count=0,
        blocked_count=0,
        results=[],
        findings=[build_bola_finding(finding_id=finding_id)],
    )


def test_fingerprint_is_stable() -> None:
    """Scan-specific finding identifiers must not affect deduplication."""

    first = build_bola_finding(finding_id="finding-1")

    second = build_bola_finding(
        finding_id="finding-2",
        observed_status_code=201,
    )

    assert build_finding_fingerprint(
        "project-1",
        first,
    ) == build_finding_fingerprint(
        "project-1",
        second,
    )


def test_first_scan_creates_open_finding(
    tmp_path: Path,
) -> None:
    """A newly observed issue should create an open finding."""

    repository = FindingRepository(tmp_path)

    completed_at = datetime(
        2026,
        8,
        1,
        10,
        0,
        tzinfo=UTC,
    )

    records = repository.upsert_scan(
        build_scan(
            scan_id="scan-1",
            completed_at=completed_at,
            finding_id="finding-1",
        )
    )

    assert len(records) == 1

    finding = records[0]

    assert finding.status == "open"
    assert finding.occurrence_count == 1
    assert finding.scan_ids == [
        "scan-1",
    ]

    assert finding.first_seen_at == completed_at

    assert finding.last_seen_at == completed_at


def test_same_scan_is_idempotent(
    tmp_path: Path,
) -> None:
    """Rebuilding from one scan must not duplicate occurrences."""

    repository = FindingRepository(tmp_path)

    scan = build_scan(
        scan_id="scan-1",
        completed_at=datetime(
            2026,
            8,
            1,
            10,
            0,
            tzinfo=UTC,
        ),
        finding_id="finding-1",
    )

    repository.upsert_scan(scan)

    records = repository.upsert_scan(scan)

    assert records[0].occurrence_count == 1

    assert records[0].scan_ids == [
        "scan-1",
    ]


def test_second_scan_increments_occurrence(
    tmp_path: Path,
) -> None:
    """A repeated observation should update the existing finding."""

    repository = FindingRepository(tmp_path)

    first_time = datetime(
        2026,
        8,
        1,
        10,
        0,
        tzinfo=UTC,
    )

    second_time = datetime(
        2026,
        8,
        2,
        10,
        0,
        tzinfo=UTC,
    )

    repository.upsert_scan(
        build_scan(
            scan_id="scan-1",
            completed_at=first_time,
            finding_id="finding-1",
        )
    )

    records = repository.upsert_scan(
        build_scan(
            scan_id="scan-2",
            completed_at=second_time,
            finding_id="finding-2",
        )
    )

    finding = records[0]

    assert finding.occurrence_count == 2

    assert finding.scan_ids == [
        "scan-1",
        "scan-2",
    ]

    assert finding.first_seen_at == first_time

    assert finding.last_seen_at == second_time


def test_resolved_finding_reopens(
    tmp_path: Path,
) -> None:
    """A newer observation should reopen a resolved finding."""

    repository = FindingRepository(tmp_path)

    first_time = datetime(
        2026,
        8,
        1,
        10,
        0,
        tzinfo=UTC,
    )

    first_record = repository.upsert_scan(
        build_scan(
            scan_id="scan-1",
            completed_at=first_time,
            finding_id="finding-1",
        )
    )[0]

    repository.update_status(
        project_id="project-1",
        fingerprint=(first_record.fingerprint),
        status="resolved",
        note="Authorization check fixed.",
    )

    reopened = repository.upsert_scan(
        build_scan(
            scan_id="scan-2",
            completed_at=(first_time + timedelta(days=1)),
            finding_id="finding-2",
        )
    )[0]

    assert reopened.status == "open"
    assert reopened.reopened_count == 1
    assert reopened.resolution_note is None


def test_false_positive_status_is_preserved(
    tmp_path: Path,
) -> None:
    """Repeated observations must not reopen false positives."""

    repository = FindingRepository(tmp_path)

    first_time = datetime(
        2026,
        8,
        1,
        10,
        0,
        tzinfo=UTC,
    )

    first_record = repository.upsert_scan(
        build_scan(
            scan_id="scan-1",
            completed_at=first_time,
            finding_id="finding-1",
        )
    )[0]

    repository.update_status(
        project_id="project-1",
        fingerprint=(first_record.fingerprint),
        status="false_positive",
        note=("Cross-tenant access is intentional for this identity."),
    )

    updated = repository.upsert_scan(
        build_scan(
            scan_id="scan-2",
            completed_at=(first_time + timedelta(days=1)),
            finding_id="finding-2",
        )
    )[0]

    assert updated.status == "false_positive"

    assert updated.occurrence_count == 2


def test_repository_round_trip(
    tmp_path: Path,
) -> None:
    """Persisted findings should load without data loss."""

    repository = FindingRepository(tmp_path)

    record = repository.upsert_scan(
        build_scan(
            scan_id="scan-1",
            completed_at=datetime(
                2026,
                8,
                1,
                10,
                0,
                tzinfo=UTC,
            ),
            finding_id="finding-1",
        )
    )[0]

    loaded = repository.load(
        record.project_id,
        record.fingerprint,
    )

    assert loaded == record

    findings = repository.list_all("project-1")

    assert findings == [
        record,
    ]
