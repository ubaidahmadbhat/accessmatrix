"""Authorization report API schemas."""

from pydantic import BaseModel, Field, field_validator

from accessmatrix.findings.models import FindingStatus
from accessmatrix.reports.models import ReportFormat


def default_finding_statuses() -> list[FindingStatus]:
    """Return the default report finding statuses."""

    return [
        "open",
        "resolved",
        "false_positive",
        "accepted_risk",
    ]


class GenerateReportRequest(BaseModel):
    """Generate a stored project report."""

    report_format: ReportFormat

    title: str | None = Field(
        default=None,
        max_length=200,
    )

    include_statuses: list[FindingStatus] = Field(
        default_factory=default_finding_statuses,
    )

    include_scan_history: bool = True

    @field_validator("include_statuses")
    @classmethod
    def validate_statuses(
        cls,
        value: list[FindingStatus],
    ) -> list[FindingStatus]:
        """Require at least one unique lifecycle status."""

        unique_statuses = list(dict.fromkeys(value))

        if not unique_statuses:
            raise ValueError("At least one finding status must be included.")

        return unique_statuses
