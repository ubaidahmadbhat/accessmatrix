"""Authorization report generation and persistence."""

from accessmatrix.reports.generator import (
    RenderedReport,
    build_report_snapshot,
    render_report,
)
from accessmatrix.reports.models import (
    ReportArtifactList,
    ReportArtifactMetadata,
    ReportFormat,
    ReportSnapshot,
    ReportSummary,
)
from accessmatrix.reports.storage import (
    ReportArtifactInput,
    ReportRepository,
    ReportStorageError,
)

__all__ = [
    "RenderedReport",
    "ReportArtifactInput",
    "ReportArtifactList",
    "ReportArtifactMetadata",
    "ReportFormat",
    "ReportRepository",
    "ReportSnapshot",
    "ReportStorageError",
    "ReportSummary",
    "build_report_snapshot",
    "render_report",
]