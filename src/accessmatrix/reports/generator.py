"""Authorization report rendering."""

import json
from dataclasses import dataclass
from html import escape
from typing import Any
from xml.etree import ElementTree

from accessmatrix.findings.models import (
    FindingRecord,
    FindingStatus,
)
from accessmatrix.persistence.models import (
    Project,
)
from accessmatrix.reports.models import (
    ReportFormat,
    ReportSnapshot,
    ReportSummary,
)
from accessmatrix.scanning.models import (
    BOLAScanSummary,
)

SARIF_SCHEMA = (
    "https://json.schemastore.org/"
    "sarif-2.1.0.json"
)


@dataclass(
    frozen=True,
    slots=True,
)
class RenderedReport:
    """Rendered report bytes and delivery metadata."""

    extension: str
    media_type: str
    content: bytes


def build_report_snapshot(
    *,
    report_id: str,
    report_format: ReportFormat,
    project: Project,
    title: str,
    generated_at: Any,
    findings: list[FindingRecord],
    scans: list[BOLAScanSummary],
    include_statuses: set[FindingStatus],
    include_scan_history: bool,
) -> ReportSnapshot:
    """Build a filtered immutable report snapshot."""

    included_findings = [
        finding
        for finding in findings
        if finding.status
        in include_statuses
    ]

    included_scans = (
        scans
        if include_scan_history
        else []
    )

    summary = ReportSummary(
        finding_count=len(
            included_findings
        ),
        open_count=sum(
            finding.status
            == "open"
            for finding
            in included_findings
        ),
        resolved_count=sum(
            finding.status
            == "resolved"
            for finding
            in included_findings
        ),
        false_positive_count=sum(
            finding.status
            == "false_positive"
            for finding
            in included_findings
        ),
        accepted_risk_count=sum(
            finding.status
            == "accepted_risk"
            for finding
            in included_findings
        ),
        scan_count=len(
            included_scans
        ),
        scan_case_count=sum(
            scan.total_count
            for scan
            in included_scans
        ),
        scan_pass_count=sum(
            scan.pass_count
            for scan
            in included_scans
        ),
        scan_finding_count=sum(
            scan.finding_count
            for scan
            in included_scans
        ),
        scan_inconclusive_count=sum(
            scan.inconclusive_count
            for scan
            in included_scans
        ),
        scan_blocked_count=sum(
            scan.blocked_count
            for scan
            in included_scans
        ),
    )

    return ReportSnapshot(
        report_id=report_id,
        report_format=report_format,
        project_id=project.id,
        project_name=project.name,
        project_description=(
            project.description
        ),
        target_base_url=(
            project.base_url
        ),
        title=title,
        generated_at=generated_at,
        summary=summary,
        findings=(
            included_findings
        ),
        scans=included_scans,
    )


def markdown_escape(
    value: str,
) -> str:
    """Escape table-sensitive Markdown characters."""

    return (
        value.replace(
            "\\",
            "\\\\",
        )
        .replace(
            "|",
            "\\|",
        )
        .replace(
            "\r",
            " ",
        )
        .replace(
            "\n",
            " ",
        )
    )


def render_json(
    snapshot: ReportSnapshot,
) -> RenderedReport:
    """Render a native AccessMatrix JSON report."""

    content = (
        snapshot.model_dump_json(
            indent=2,
        ).encode(
            "utf-8"
        )
    )

    return RenderedReport(
        extension="json",
        media_type=(
            "application/json"
        ),
        content=content,
    )


def render_markdown(
    snapshot: ReportSnapshot,
) -> RenderedReport:
    """Render a Markdown authorization report."""

    summary = snapshot.summary

    lines = [
        f"# {snapshot.title}",
        "",
        "## Report metadata",
        "",
        f"- Report ID: `{snapshot.report_id}`",
        f"- Project: **{snapshot.project_name}**",
        (
            "- Generated: "
            f"`{snapshot.generated_at.isoformat()}`"
        ),
        (
            "- Target base URL: "
            f"`{snapshot.target_base_url or 'Not configured'}`"
        ),
        "",
        "## Executive summary",
        "",
        (
            f"- Included findings: "
            f"**{summary.finding_count}**"
        ),
        f"- Open: **{summary.open_count}**",
        (
            f"- Resolved: "
            f"**{summary.resolved_count}**"
        ),
        (
            "- False positive: "
            f"**{summary.false_positive_count}**"
        ),
        (
            "- Accepted risk: "
            f"**{summary.accepted_risk_count}**"
        ),
        (
            f"- Included scans: "
            f"**{summary.scan_count}**"
        ),
        "",
        "## Findings",
        "",
    ]

    if snapshot.findings:
        lines.extend(
            [
                (
                    "| Severity | Status | Category | "
                    "Operation | Identity | Probe object | "
                    "Occurrences |"
                ),
                (
                    "|---|---|---|---|---|---|---:|"
                ),
            ]
        )

        for finding in snapshot.findings:
            lines.append(
                "| "
                + " | ".join(
                    [
                        markdown_escape(
                            finding.severity.upper()
                        ),
                        markdown_escape(
                            finding.status
                        ),
                        markdown_escape(
                            finding.category
                        ),
                        (
                            "`"
                            + markdown_escape(
                                finding.operation_key
                            )
                            + "`"
                        ),
                        markdown_escape(
                            finding.identity_name
                        ),
                        (
                            "`"
                            + markdown_escape(
                                finding.probe_object_id
                            )
                            + "`"
                        ),
                        str(
                            finding
                            .occurrence_count
                        ),
                    ]
                )
                + " |"
            )

        for finding in snapshot.findings:
            lines.extend(
                [
                    "",
                    (
                        "### "
                        f"{finding.severity.upper()} — "
                        f"{finding.title}"
                    ),
                    "",
                    finding.description,
                    "",
                    (
                        "- Fingerprint: "
                        f"`{finding.fingerprint}`"
                    ),
                    (
                        "- Status: "
                        f"`{finding.status}`"
                    ),
                    (
                        "- Confidence: "
                        f"`{finding.confidence}`"
                    ),
                    (
                        "- Operation: "
                        f"`{finding.operation_key}`"
                    ),
                    (
                        "- Identity: "
                        f"{finding.identity_name}"
                    ),
                    (
                        "- Owned baseline: "
                        f"`{finding.baseline_object_id or 'Unavailable'}`"
                    ),
                    (
                        "- Cross-owner probe: "
                        f"`{finding.probe_object_id}`"
                    ),
                    (
                        "- Last observed HTTP status: "
                        f"`{finding.last_observed_status_code}`"
                    ),
                    (
                        "- First observed: "
                        f"`{finding.first_seen_at.isoformat()}`"
                    ),
                    (
                        "- Last observed: "
                        f"`{finding.last_seen_at.isoformat()}`"
                    ),
                    (
                        "- Occurrences: "
                        f"`{finding.occurrence_count}`"
                    ),
                ]
            )

            if finding.resolution_note:
                lines.extend(
                    [
                        (
                            "- Lifecycle note: "
                            f"{finding.resolution_note}"
                        ),
                    ]
                )

    else:
        lines.append(
            "No findings matched the selected report scope."
        )

    lines.extend(
        [
            "",
            "## Scan history",
            "",
        ]
    )

    if snapshot.scans:
        lines.extend(
            [
                (
                    "| Completed | Status | Cases | Passed | "
                    "Findings | Inconclusive | Blocked |"
                ),
                (
                    "|---|---|---:|---:|---:|---:|---:|"
                ),
            ]
        )

        for scan in snapshot.scans:
            lines.append(
                "| "
                + " | ".join(
                    [
                        scan.completed_at.isoformat(),
                        scan.status,
                        str(scan.total_count),
                        str(scan.pass_count),
                        str(scan.finding_count),
                        str(
                            scan
                            .inconclusive_count
                        ),
                        str(
                            scan.blocked_count
                        ),
                    ]
                )
                + " |"
            )

    else:
        lines.append(
            "Scan history was not included."
        )

    lines.extend(
        [
            "",
            "---",
            "",
            (
                "Generated locally by AccessMatrix. "
                "Credential secrets are not included."
            ),
            "",
        ]
    )

    return RenderedReport(
        extension="md",
        media_type=(
            "text/markdown; charset=utf-8"
        ),
        content=(
            "\n".join(
                lines
            ).encode(
                "utf-8"
            )
        ),
    )


def finding_status_class(
    status: FindingStatus,
) -> str:
    """Return a safe HTML class suffix."""

    return status.replace(
        "_",
        "-",
    )


def render_html(
    snapshot: ReportSnapshot,
) -> RenderedReport:
    """Render a standalone HTML authorization report."""

    summary = snapshot.summary

    finding_rows: list[str] = []

    for finding in snapshot.findings:
        finding_rows.append(
            """
            <tr>
              <td>
                <span class="severity severity-{severity}">
                  {severity_label}
                </span>
              </td>
              <td>
                <span class="status status-{status_class}">
                  {status}
                </span>
              </td>
              <td>{category}</td>
              <td><code>{operation}</code></td>
              <td>{identity}</td>
              <td><code>{probe}</code></td>
              <td>{occurrences}</td>
            </tr>
            """.format(
                severity=escape(
                    finding.severity
                ),
                severity_label=escape(
                    finding.severity.upper()
                ),
                status_class=escape(
                    finding_status_class(
                        finding.status
                    )
                ),
                status=escape(
                    finding.status.replace(
                        "_",
                        " ",
                    ).title()
                ),
                category=escape(
                    finding.category
                ),
                operation=escape(
                    finding.operation_key
                ),
                identity=escape(
                    finding.identity_name
                ),
                probe=escape(
                    finding.probe_object_id
                ),
                occurrences=(
                    finding.occurrence_count
                ),
            )
        )

    finding_details: list[str] = []

    for finding in snapshot.findings:
        lifecycle_note = (
            escape(
                finding.resolution_note
            )
            if finding.resolution_note
            else "None"
        )

        finding_details.append(
            """
            <article class="finding-card">
              <header>
                <div>
                  <span class="eyebrow">{category}</span>
                  <h3>{title}</h3>
                </div>
                <span class="severity severity-{severity}">
                  {severity_label}
                </span>
              </header>

              <p>{description}</p>

              <dl>
                <div>
                  <dt>Status</dt>
                  <dd>{status}</dd>
                </div>
                <div>
                  <dt>Confidence</dt>
                  <dd>{confidence}</dd>
                </div>
                <div>
                  <dt>Operation</dt>
                  <dd><code>{operation}</code></dd>
                </div>
                <div>
                  <dt>Identity</dt>
                  <dd>{identity}</dd>
                </div>
                <div>
                  <dt>Owned baseline</dt>
                  <dd><code>{baseline}</code></dd>
                </div>
                <div>
                  <dt>Cross-owner probe</dt>
                  <dd><code>{probe}</code></dd>
                </div>
                <div>
                  <dt>Last HTTP status</dt>
                  <dd>{http_status}</dd>
                </div>
                <div>
                  <dt>Occurrences</dt>
                  <dd>{occurrences}</dd>
                </div>
              </dl>

              <p class="note">
                <strong>Lifecycle note:</strong>
                {lifecycle_note}
              </p>

              <small>
                Fingerprint:
                <code>{fingerprint}</code>
              </small>
            </article>
            """.format(
                category=escape(
                    finding.category
                ),
                title=escape(
                    finding.title
                ),
                severity=escape(
                    finding.severity
                ),
                severity_label=escape(
                    finding.severity.upper()
                ),
                description=escape(
                    finding.description
                ),
                status=escape(
                    finding.status.replace(
                        "_",
                        " ",
                    ).title()
                ),
                confidence=escape(
                    finding.confidence.title()
                ),
                operation=escape(
                    finding.operation_key
                ),
                identity=escape(
                    finding.identity_name
                ),
                baseline=escape(
                    finding.baseline_object_id
                    or "Unavailable"
                ),
                probe=escape(
                    finding.probe_object_id
                ),
                http_status=(
                    finding
                    .last_observed_status_code
                ),
                occurrences=(
                    finding.occurrence_count
                ),
                lifecycle_note=(
                    lifecycle_note
                ),
                fingerprint=escape(
                    finding.fingerprint
                ),
            )
        )

    scan_rows: list[str] = []

    for scan in snapshot.scans:
        scan_rows.append(
            """
            <tr>
              <td>{completed}</td>
              <td>{status}</td>
              <td>{total}</td>
              <td>{passed}</td>
              <td>{findings}</td>
              <td>{inconclusive}</td>
              <td>{blocked}</td>
            </tr>
            """.format(
                completed=escape(
                    scan.completed_at.isoformat()
                ),
                status=escape(
                    scan.status
                ),
                total=scan.total_count,
                passed=scan.pass_count,
                findings=(
                    scan.finding_count
                ),
                inconclusive=(
                    scan
                    .inconclusive_count
                ),
                blocked=(
                    scan.blocked_count
                ),
            )
        )

    finding_table_body = (
        "\n".join(
            finding_rows
        )
        if finding_rows
        else (
            '<tr><td colspan="7">'
            "No findings matched the report scope."
            "</td></tr>"
        )
    )

    finding_detail_body = (
        "\n".join(
            finding_details
        )
        if finding_details
        else (
            '<div class="empty">'
            "No detailed findings are available."
            "</div>"
        )
    )

    scan_table_body = (
        "\n".join(
            scan_rows
        )
        if scan_rows
        else (
            '<tr><td colspan="7">'
            "Scan history was not included."
            "</td></tr>"
        )
    )

    html_content = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta
    name="viewport"
    content="width=device-width, initial-scale=1"
  >
  <title>{title}</title>

  <style>
    :root {{
      color-scheme: dark;
      font-family:
        Inter,
        ui-sans-serif,
        system-ui,
        sans-serif;
      background: #07111c;
      color: #dce8f2;
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      padding: 34px;
      background:
        linear-gradient(
          145deg,
          #07111c,
          #0a1c2a
        );
    }}

    main {{
      max-width: 1400px;
      margin: 0 auto;
    }}

    h1,
    h2,
    h3,
    p {{
      margin-top: 0;
    }}

    h1 {{
      margin-bottom: 8px;
    }}

    h2 {{
      margin-top: 32px;
      font-size: 20px;
    }}

    .subtitle {{
      color: #8398aa;
    }}

    .metadata,
    .summary-grid,
    .finding-card dl {{
      display: grid;
      grid-template-columns:
        repeat(
          auto-fit,
          minmax(160px, 1fr)
        );
      gap: 12px;
    }}

    .metadata article,
    .summary-grid article,
    .finding-card,
    .empty {{
      border: 1px solid #1d3a50;
      border-radius: 12px;
      background: #0a1927;
    }}

    .metadata article,
    .summary-grid article {{
      padding: 15px;
    }}

    .metadata span,
    .summary-grid span,
    dt,
    .eyebrow {{
      display: block;
      color: #71889d;
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
    }}

    .metadata strong,
    .summary-grid strong {{
      display: block;
      margin-top: 6px;
      overflow-wrap: anywhere;
      font-size: 18px;
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      overflow: hidden;
      border: 1px solid #1d3a50;
      border-radius: 12px;
      background: #0a1927;
    }}

    th,
    td {{
      padding: 11px;
      border-bottom: 1px solid #183247;
      text-align: left;
      vertical-align: top;
      font-size: 12px;
    }}

    th {{
      color: #8ba2b6;
      background: #0e2233;
    }}

    code {{
      overflow-wrap: anywhere;
      color: #8ed3ed;
    }}

    .finding-grid {{
      display: grid;
      grid-template-columns:
        repeat(
          auto-fit,
          minmax(330px, 1fr)
        );
      gap: 14px;
    }}

    .finding-card {{
      padding: 18px;
    }}

    .finding-card header {{
      display: flex;
      justify-content: space-between;
      gap: 14px;
    }}

    .finding-card h3 {{
      margin-top: 5px;
      font-size: 16px;
    }}

    .finding-card p {{
      color: #99adbd;
      line-height: 1.6;
    }}

    .finding-card dl {{
      margin: 15px 0;
    }}

    .finding-card dl div {{
      padding: 10px;
      border: 1px solid #183247;
      border-radius: 8px;
      background: #071521;
    }}

    dd {{
      margin: 6px 0 0;
      overflow-wrap: anywhere;
      font-size: 12px;
    }}

    .severity,
    .status {{
      display: inline-flex;
      padding: 5px 8px;
      border-radius: 999px;
      font-size: 10px;
      font-weight: 800;
      text-transform: uppercase;
    }}

    .severity-critical,
    .severity-high,
    .status-open {{
      border: 1px solid #83424d;
      color: #ff9aa6;
      background: #351d24;
    }}

    .severity-medium,
    .status-accepted-risk {{
      border: 1px solid #735c2f;
      color: #e6c177;
      background: #332a17;
    }}

    .severity-low,
    .severity-info {{
      border: 1px solid #31566f;
      color: #8ed2ec;
      background: #102638;
    }}

    .status-resolved {{
      border: 1px solid #275e46;
      color: #72d8a5;
      background: #102d22;
    }}

    .status-false-positive {{
      border: 1px solid #4b5563;
      color: #b5c0ca;
      background: #202730;
    }}

    .note {{
      padding: 10px;
      border-left: 3px solid #4b7893;
      background: #0d2131;
    }}

    .empty {{
      padding: 18px;
      color: #8398aa;
    }}

    footer {{
      margin-top: 34px;
      padding-top: 18px;
      border-top: 1px solid #1d3a50;
      color: #71889d;
      font-size: 11px;
    }}

    @media print {{
      :root {{
        color-scheme: light;
      }}

      body {{
        padding: 0;
        color: #111827;
        background: white;
      }}

      .metadata article,
      .summary-grid article,
      .finding-card,
      table {{
        border-color: #cbd5e1;
        color: #111827;
        background: white;
      }}
    }}
  </style>
</head>

<body>
  <main>
    <header>
      <span class="eyebrow">
        AccessMatrix authorization report
      </span>

      <h1>{title}</h1>

      <p class="subtitle">
        Generated locally from persisted findings
        and scan records.
      </p>
    </header>

    <section class="metadata">
      <article>
        <span>Project</span>
        <strong>{project_name}</strong>
      </article>

      <article>
        <span>Report ID</span>
        <strong>{report_id}</strong>
      </article>

      <article>
        <span>Generated</span>
        <strong>{generated_at}</strong>
      </article>

      <article>
        <span>Target base URL</span>
        <strong>{target_base_url}</strong>
      </article>
    </section>

    <h2>Executive summary</h2>

    <section class="summary-grid">
      <article>
        <span>Included findings</span>
        <strong>{finding_count}</strong>
      </article>

      <article>
        <span>Open</span>
        <strong>{open_count}</strong>
      </article>

      <article>
        <span>Resolved</span>
        <strong>{resolved_count}</strong>
      </article>

      <article>
        <span>False positive</span>
        <strong>{false_positive_count}</strong>
      </article>

      <article>
        <span>Accepted risk</span>
        <strong>{accepted_risk_count}</strong>
      </article>

      <article>
        <span>Included scans</span>
        <strong>{scan_count}</strong>
      </article>
    </section>

    <h2>Finding overview</h2>

    <table>
      <thead>
        <tr>
          <th>Severity</th>
          <th>Status</th>
          <th>Category</th>
          <th>Operation</th>
          <th>Identity</th>
          <th>Probe object</th>
          <th>Occurrences</th>
        </tr>
      </thead>

      <tbody>
        {finding_table_body}
      </tbody>
    </table>

    <h2>Finding details</h2>

    <section class="finding-grid">
      {finding_detail_body}
    </section>

    <h2>Scan history</h2>

    <table>
      <thead>
        <tr>
          <th>Completed</th>
          <th>Status</th>
          <th>Cases</th>
          <th>Passed</th>
          <th>Findings</th>
          <th>Inconclusive</th>
          <th>Blocked</th>
        </tr>
      </thead>

      <tbody>
        {scan_table_body}
      </tbody>
    </table>

    <footer>
      Generated by AccessMatrix. Credential
      secrets are not included in this artifact.
    </footer>
  </main>
</body>
</html>
""".format(
        title=escape(
            snapshot.title
        ),
        project_name=escape(
            snapshot.project_name
        ),
        report_id=escape(
            snapshot.report_id
        ),
        generated_at=escape(
            snapshot
            .generated_at
            .isoformat()
        ),
        target_base_url=escape(
            snapshot.target_base_url
            or "Not configured"
        ),
        finding_count=(
            summary.finding_count
        ),
        open_count=(
            summary.open_count
        ),
        resolved_count=(
            summary.resolved_count
        ),
        false_positive_count=(
            summary.false_positive_count
        ),
        accepted_risk_count=(
            summary.accepted_risk_count
        ),
        scan_count=(
            summary.scan_count
        ),
        finding_table_body=(
            finding_table_body
        ),
        finding_detail_body=(
            finding_detail_body
        ),
        scan_table_body=(
            scan_table_body
        ),
    )

    return RenderedReport(
        extension="html",
        media_type=(
            "text/html; charset=utf-8"
        ),
        content=(
            html_content.encode(
                "utf-8"
            )
        ),
    )


def sarif_level(
    severity: str,
) -> str:
    """Map AccessMatrix severity to SARIF level."""

    if severity in {
        "critical",
        "high",
    }:
        return "error"

    if severity == "medium":
        return "warning"

    return "note"


def render_sarif(
    snapshot: ReportSnapshot,
) -> RenderedReport:
    """Render a SARIF 2.1.0 report."""

    categories = sorted(
        {
            finding.category
            for finding
            in snapshot.findings
        }
    )

    rules = [
        {
            "id": category,
            "name": category,
            "shortDescription": {
                "text": (
                    f"{category} authorization finding"
                )
            },
            "fullDescription": {
                "text": (
                    "Authorization behavior detected "
                    "by AccessMatrix comparative testing."
                )
            },
            "helpUri": (
                "https://owasp.org/API-Security/"
            ),
        }
        for category
        in categories
    ]

    results: list[
        dict[str, Any]
    ] = []

    for finding in snapshot.findings:
        result: dict[str, Any] = {
            "ruleId": finding.category,
            "level": sarif_level(
                finding.severity
            ),
            "message": {
                "text": finding.description
            },
            "partialFingerprints": {
                "accessmatrixFingerprint/v1": (
                    finding.fingerprint
                )
            },
            "properties": {
                "accessMatrixFindingId": (
                    finding.finding_id
                ),
                "projectId": (
                    finding.project_id
                ),
                "status": finding.status,
                "severity": (
                    finding.severity
                ),
                "confidence": (
                    finding.confidence
                ),
                "operationKey": (
                    finding.operation_key
                ),
                "identityId": (
                    finding.identity_id
                ),
                "identityName": (
                    finding.identity_name
                ),
                "resourceType": (
                    finding.resource_type
                ),
                "baselineObjectId": (
                    finding.baseline_object_id
                ),
                "probeObjectId": (
                    finding.probe_object_id
                ),
                "occurrenceCount": (
                    finding.occurrence_count
                ),
                "lastObservedStatusCode": (
                    finding
                    .last_observed_status_code
                ),
            },
        }

        if finding.status in {
            "false_positive",
            "accepted_risk",
        }:
            result["suppressions"] = [
                {
                    "kind": "external",
                    "status": "accepted",
                    "justification": (
                        finding.resolution_note
                        or finding.status
                    ),
                }
            ]

        results.append(
            result
        )

    sarif_document = {
        "$schema": SARIF_SCHEMA,
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "AccessMatrix",
                        "informationUri": (
                            "https://github.com/"
                        ),
                        "rules": rules,
                    }
                },
                "automationDetails": {
                    "id": snapshot.report_id
                },
                "properties": {
                    "projectId": (
                        snapshot.project_id
                    ),
                    "projectName": (
                        snapshot.project_name
                    ),
                    "generatedAt": (
                        snapshot
                        .generated_at
                        .isoformat()
                    ),
                },
                "results": results,
            }
        ],
    }

    return RenderedReport(
        extension="sarif",
        media_type=(
            "application/sarif+json"
        ),
        content=(
            json.dumps(
                sarif_document,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ).encode(
                "utf-8"
            )
        ),
    )


def render_junit(
    snapshot: ReportSnapshot,
) -> RenderedReport:
    """Render findings as a JUnit XML test suite."""

    active_findings = [
        finding
        for finding
        in snapshot.findings
        if finding.status
        in {
            "open",
            "accepted_risk",
        }
    ]

    skipped_findings = [
        finding
        for finding
        in snapshot.findings
        if finding.status
        in {
            "resolved",
            "false_positive",
        }
    ]

    root = ElementTree.Element(
        "testsuite",
        {
            "name": (
                f"AccessMatrix "
                f"{snapshot.project_name}"
            ),
            "tests": str(
                len(
                    snapshot.findings
                )
            ),
            "failures": str(
                len(
                    active_findings
                )
            ),
            "errors": "0",
            "skipped": str(
                len(
                    skipped_findings
                )
            ),
            "timestamp": (
                snapshot
                .generated_at
                .isoformat()
            ),
        },
    )

    properties = ElementTree.SubElement(
        root,
        "properties",
    )

    for (
        property_name,
        property_value,
    ) in {
        "report_id": (
            snapshot.report_id
        ),
        "project_id": (
            snapshot.project_id
        ),
        "project_name": (
            snapshot.project_name
        ),
        "target_base_url": (
            snapshot.target_base_url
            or ""
        ),
    }.items():
        ElementTree.SubElement(
            properties,
            "property",
            {
                "name": property_name,
                "value": property_value,
            },
        )

    for finding in snapshot.findings:
        test_case = (
            ElementTree.SubElement(
                root,
                "testcase",
                {
                    "classname": (
                        "AccessMatrix."
                        f"{finding.category}"
                    ),
                    "name": (
                        f"{finding.operation_key} "
                        f"{finding.identity_name} "
                        f"{finding.probe_object_id}"
                    ),
                },
            )
        )

        if finding.status in {
            "open",
            "accepted_risk",
        }:
            failure = (
                ElementTree.SubElement(
                    test_case,
                    "failure",
                    {
                        "type": (
                            finding.category
                        ),
                        "message": (
                            finding.title
                        ),
                    },
                )
            )

            failure.text = (
                finding.description
            )

        elif finding.status in {
            "resolved",
            "false_positive",
        }:
            ElementTree.SubElement(
                test_case,
                "skipped",
                {
                    "message": (
                        finding
                        .resolution_note
                        or finding.status
                    )
                },
            )

        output = ElementTree.SubElement(
            test_case,
            "system-out",
        )

        output.text = json.dumps(
            {
                "fingerprint": (
                    finding.fingerprint
                ),
                "status": (
                    finding.status
                ),
                "severity": (
                    finding.severity
                ),
                "confidence": (
                    finding.confidence
                ),
                "identity": (
                    finding.identity_name
                ),
                "baseline_object_id": (
                    finding
                    .baseline_object_id
                ),
                "probe_object_id": (
                    finding.probe_object_id
                ),
                "last_observed_status_code": (
                    finding
                    .last_observed_status_code
                ),
                "occurrence_count": (
                    finding.occurrence_count
                ),
            },
            ensure_ascii=False,
            sort_keys=True,
        )

    xml_content = (
        ElementTree.tostring(
            root,
            encoding="utf-8",
            xml_declaration=True,
        )
    )

    return RenderedReport(
        extension="xml",
        media_type=(
            "application/xml"
        ),
        content=xml_content,
    )


def render_report(
    snapshot: ReportSnapshot,
) -> RenderedReport:
    """Render a report using its requested format."""

    if snapshot.report_format == "json":
        return render_json(
            snapshot
        )

    if snapshot.report_format == "markdown":
        return render_markdown(
            snapshot
        )

    if snapshot.report_format == "html":
        return render_html(
            snapshot
        )

    if snapshot.report_format == "sarif":
        return render_sarif(
            snapshot
        )

    if snapshot.report_format == "junit":
        return render_junit(
            snapshot
        )

    raise ValueError(
        "The report format is unsupported."
    )