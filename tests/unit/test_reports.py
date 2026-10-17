"""Unit tests for report generation and persistence."""

import json
from datetime import UTC, datetime
from pathlib import Path
from xml.etree import ElementTree

import pytest

from accessmatrix.findings.models import FindingRecord
from accessmatrix.persistence.models import Project
from accessmatrix.reports.generator import (
    build_report_snapshot,
    render_report,
)
from accessmatrix.reports.models import (
    ReportFormat,
    ReportSnapshot,
)
from accessmatrix.reports.storage import (
    ReportArtifactInput,
    ReportRepository,
)
from accessmatrix.scanning.models import BOLAScanSummary


def build_finding() -> FindingRecord:
    """Create a reportable finding."""

    observed_at = datetime(
        2026,
        8,
        1,
        10,
        0,
        tzinfo=UTC,
    )

    return FindingRecord(
        finding_id="finding-1",
        fingerprint="a" * 64,
        project_id="project-1",
        category="BOLA",
        title="Broken object-level authorization detected",
        description="Customer Alice accessed Bob's invoice.",
        severity="high",
        confidence="high",
        status="open",
        operation_key="GET /invoices/{invoice_id}",
        identity_id="alice-id",
        identity_name="Customer Alice",
        resource_type="invoice",
        baseline_object_id="INV-1001",
        probe_object_id="INV-2001",
        first_seen_at=observed_at,
        last_seen_at=observed_at,
        updated_at=observed_at,
        occurrence_count=1,
        reopened_count=0,
        last_observed_status_code=200,
        matching_response_fields={
            "invoice_id": True,
            "owner_id": True,
            "tenant_id": True,
        },
        scan_ids=[
            "scan-1",
        ],
        source_finding_ids=[
            "source-finding-1",
        ],
        resolution_note=None,
    )


def build_scan_summary() -> BOLAScanSummary:
    """Create a reportable scan summary."""

    completed_at = datetime(
        2026,
        8,
        1,
        10,
        0,
        tzinfo=UTC,
    )

    return BOLAScanSummary(
        scan_id="scan-1",
        project_id="project-1",
        started_at=completed_at,
        completed_at=completed_at,
        status="completed",
        total_count=4,
        pass_count=0,
        finding_count=4,
        inconclusive_count=0,
        blocked_count=0,
    )


def build_snapshot(
    report_format: ReportFormat,
    *,
    title: str = "Invoice Authorization Report",
) -> ReportSnapshot:
    """Create a report snapshot."""

    return build_report_snapshot(
        report_id="report-1",
        report_format=report_format,
        project=Project(
            id="project-1",
            name="Local Invoice Demo",
            description="Demonstration project.",
            base_url="http://127.0.0.1:9000",
        ),
        title=title,
        generated_at=datetime(
            2026,
            8,
            1,
            11,
            0,
            tzinfo=UTC,
        ),
        findings=[
            build_finding(),
        ],
        scans=[
            build_scan_summary(),
        ],
        include_statuses={
            "open",
        },
        include_scan_history=True,
    )


@pytest.mark.parametrize(
    (
        "report_format",
        "expected_extension",
    ),
    [
        (
            "json",
            "json",
        ),
        (
            "markdown",
            "md",
        ),
        (
            "html",
            "html",
        ),
        (
            "sarif",
            "sarif",
        ),
        (
            "junit",
            "xml",
        ),
    ],
)
def test_all_report_formats_render(
    report_format: ReportFormat,
    expected_extension: str,
) -> None:
    """Every supported report format should render."""

    rendered = render_report(build_snapshot(report_format))

    assert rendered.extension == expected_extension

    assert rendered.content


def test_json_report_is_valid() -> None:
    """JSON reports should contain the report snapshot."""

    rendered = render_report(build_snapshot("json"))

    document = json.loads(rendered.content)

    assert document["project_name"] == "Local Invoice Demo"

    assert document["summary"]["finding_count"] == 1


def test_html_report_escapes_title() -> None:
    """HTML reports must escape user-controlled report titles."""

    rendered = render_report(
        build_snapshot(
            "html",
            title="<script>alert(1)</script>",
        )
    )

    html_content = rendered.content.decode("utf-8")

    assert "<script>alert(1)</script>" not in html_content

    assert "&lt;script&gt;" in html_content


def test_sarif_report_is_valid_json() -> None:
    """SARIF reports should use the SARIF 2.1.0 structure."""

    rendered = render_report(build_snapshot("sarif"))

    document = json.loads(rendered.content)

    assert document["version"] == "2.1.0"

    assert document["runs"][0]["results"][0]["ruleId"] == "BOLA"


def test_junit_report_is_valid_xml() -> None:
    """JUnit reports should contain failing authorization cases."""

    rendered = render_report(build_snapshot("junit"))

    root = ElementTree.fromstring(rendered.content)

    assert root.tag == "testsuite"

    assert root.attrib["tests"] == "1"

    assert root.attrib["failures"] == "1"

    assert root.find("testcase/failure") is not None


def test_report_repository_round_trip(
    tmp_path: Path,
) -> None:
    """Stored report artifacts should list and preview safely."""

    snapshot = build_snapshot("markdown")

    rendered = render_report(snapshot)

    repository = ReportRepository(tmp_path)

    metadata = repository.save(
        ReportArtifactInput(
            report_id=(snapshot.report_id),
            project_id=(snapshot.project_id),
            project_name=(snapshot.project_name),
            title=(snapshot.title),
            report_format=(snapshot.report_format),
            generated_at=(snapshot.generated_at),
            finding_count=(snapshot.summary.finding_count),
            scan_count=(snapshot.summary.scan_count),
            filename=("accessmatrix-test.md"),
            media_type=(rendered.media_type),
            content=(rendered.content),
        )
    )

    loaded = repository.load_metadata(
        snapshot.project_id,
        snapshot.report_id,
    )

    assert loaded == metadata

    reports = repository.list_metadata(snapshot.project_id)

    assert reports == [
        metadata,
    ]

    preview = repository.read_preview(
        snapshot.project_id,
        snapshot.report_id,
    )

    assert "Invoice Authorization Report" in preview

    assert repository.artifact_path(
        snapshot.project_id,
        snapshot.report_id,
    ).is_file()
