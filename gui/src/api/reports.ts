import {
  ApiRequestError,
} from "./projects";

export type ReportFormat =
  | "json"
  | "markdown"
  | "html"
  | "sarif"
  | "junit";

export type ReportFindingStatus =
  | "open"
  | "resolved"
  | "false_positive"
  | "accepted_risk";

export interface ReportArtifactMetadata {
  version: 1;

  report_id: string;
  project_id: string;
  project_name: string;

  title: string;
  report_format: ReportFormat;

  generated_at: string;

  finding_count: number;
  scan_count: number;

  filename: string;
  media_type: string;

  size_bytes: number;
  sha256: string;
}

export interface ReportArtifactList {
  project_id: string;
  items: ReportArtifactMetadata[];
}

export interface GenerateReportInput {
  projectId: string;
  report_format: ReportFormat;
  title: string | null;
  include_statuses: ReportFindingStatus[];
  include_scan_history: boolean;
}

interface ApiErrorPayload {
  detail?:
    | string
    | {
        message?: string;
        issues?: string[];
      }
    | Array<{
        msg?: string;
      }>;
}

function describeDetail(
  detail: ApiErrorPayload["detail"],
): string | null {
  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => item.msg)
      .filter(
        (
          message,
        ): message is string =>
          typeof message === "string",
      );

    return messages.length > 0
      ? messages.join(" ")
      : null;
  }

  if (
    typeof detail === "object" &&
    detail !== null
  ) {
    const sections: string[] = [];

    if (
      typeof detail.message === "string"
    ) {
      sections.push(
        detail.message,
      );
    }

    if (
      Array.isArray(
        detail.issues,
      )
    ) {
      sections.push(
        detail.issues.join(" "),
      );
    }

    return sections.length > 0
      ? sections.join(" ")
      : null;
  }

  return null;
}

async function buildApiError(
  response: Response,
): Promise<ApiRequestError> {
  const responseText =
    await response.text();

  let message =
    `Request failed with HTTP ${response.status}.`;

  if (responseText.trim()) {
    try {
      const payload =
        JSON.parse(
          responseText,
        ) as ApiErrorPayload;

      message =
        describeDetail(
          payload.detail,
        ) ?? message;
    } catch {
      message = responseText.trim();
    }
  }

  return new ApiRequestError(
    message,
    response.status,
  );
}

function reportsUrl(
  projectId: string,
): string {
  return (
    "/api/v1/projects/" +
    `${encodeURIComponent(projectId)}/` +
    "reports"
  );
}

export function reportPreviewUrl(
  projectId: string,
  reportId: string,
): string {
  return (
    `${reportsUrl(projectId)}/` +
    `${encodeURIComponent(reportId)}/preview`
  );
}

export function reportDownloadUrl(
  projectId: string,
  reportId: string,
): string {
  return (
    `${reportsUrl(projectId)}/` +
    `${encodeURIComponent(reportId)}/download`
  );
}

export async function listReports(
  projectId: string,
): Promise<ReportArtifactList> {
  const response = await fetch(
    reportsUrl(projectId),
    {
      headers: {
        Accept: "application/json",
      },
    },
  );

  if (!response.ok) {
    throw await buildApiError(
      response,
    );
  }

  return (
    await response.json()
  ) as ReportArtifactList;
}

export async function generateReport(
  input: GenerateReportInput,
): Promise<ReportArtifactMetadata> {
  const response = await fetch(
    reportsUrl(
      input.projectId,
    ),
    {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        report_format:
          input.report_format,
        title: input.title,
        include_statuses:
          input.include_statuses,
        include_scan_history:
          input.include_scan_history,
      }),
    },
  );

  if (!response.ok) {
    throw await buildApiError(
      response,
    );
  }

  return (
    await response.json()
  ) as ReportArtifactMetadata;
}

export async function getReportPreview(
  projectId: string,
  reportId: string,
): Promise<string> {
  const response = await fetch(
    reportPreviewUrl(
      projectId,
      reportId,
    ),
    {
      headers: {
        Accept: "text/plain",
      },
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw await buildApiError(
      response,
    );
  }

  return response.text();
}