"""Unit tests for scan deletion and retention."""

from datetime import (
    UTC,
    datetime,
    timedelta,
)
from pathlib import Path

import pytest

from accessmatrix.scanning.models import (
    BOLAScan,
)
from accessmatrix.scanning.storage import (
    BOLAScanRepository,
    ScanStorageError,
)


def build_scan(
    *,
    scan_id: str,
    completed_at: datetime,
) -> BOLAScan:
    """Create a minimal persisted scan."""

    return BOLAScan(
        scan_id=scan_id,
        project_id="project-1",
        started_at=(completed_at - timedelta(seconds=2)),
        completed_at=completed_at,
        status="completed",
        total_count=1,
        pass_count=1,
        finding_count=0,
        inconclusive_count=0,
        blocked_count=0,
        results=[],
        findings=[],
    )


def test_delete_removes_scan(
    tmp_path: Path,
) -> None:
    """Deleting a scan should remove its evidence file."""

    repository = BOLAScanRepository(tmp_path)

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
    )

    repository.save(scan)

    repository.delete(
        scan.project_id,
        scan.scan_id,
    )

    assert repository.list_summaries(scan.project_id) == []

    with pytest.raises(
        ScanStorageError,
        match="does not exist",
    ):
        repository.load(
            scan.project_id,
            scan.scan_id,
        )


def test_delete_rejects_missing_scan(
    tmp_path: Path,
) -> None:
    """Deleting an unknown scan should fail safely."""

    repository = BOLAScanRepository(tmp_path)

    with pytest.raises(
        ScanStorageError,
        match="does not exist",
    ):
        repository.delete(
            "project-1",
            "scan-missing",
        )


def test_prune_keeps_newest_scans(
    tmp_path: Path,
) -> None:
    """Retention should preserve only the newest scans."""

    repository = BOLAScanRepository(tmp_path)

    base_time = datetime(
        2026,
        8,
        1,
        10,
        0,
        tzinfo=UTC,
    )

    for index in range(5):
        repository.save(
            build_scan(
                scan_id=(f"scan-{index + 1}"),
                completed_at=(base_time + timedelta(hours=index)),
            )
        )

    deleted_scan_ids = repository.prune(
        "project-1",
        keep_latest=2,
    )

    assert deleted_scan_ids == [
        "scan-3",
        "scan-2",
        "scan-1",
    ]

    remaining = repository.list_summaries("project-1")

    assert [summary.scan_id for summary in remaining] == [
        "scan-5",
        "scan-4",
    ]


def test_prune_does_nothing_when_below_limit(
    tmp_path: Path,
) -> None:
    """Retention should not delete scans below the limit."""

    repository = BOLAScanRepository(tmp_path)

    repository.save(
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
        )
    )

    deleted_scan_ids = repository.prune(
        "project-1",
        keep_latest=5,
    )

    assert deleted_scan_ids == []

    assert len(repository.list_summaries("project-1")) == 1


def test_prune_requires_positive_retention(
    tmp_path: Path,
) -> None:
    """At least one scan must be retained."""

    repository = BOLAScanRepository(tmp_path)

    with pytest.raises(
        ValueError,
        match="At least one",
    ):
        repository.prune(
            "project-1",
            keep_latest=0,
        )
