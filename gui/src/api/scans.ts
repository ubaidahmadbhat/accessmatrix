import {
  ApiRequestError,
} from "./projects";

export type BOLAOutcome =
  | "pass"
  | "finding"
  | "inconclusive"
  | "blocked";

export type ScanStatus =
  | "completed"
  | "partial"
  | "failed";

export type FindingSeverity =
  | "info"
  | "low"
  | "medium"
  | "high"
  | "critical";

export type FindingConfidence =
  | "low"
  | "medium"
  | "high";

export interface ResponseEvidence {
  request_url: string;
  status_code: number;
  reason_phrase: string;
  elapsed_ms: number;

  response_headers: Record<
    string,
    string
  >;

  body_excerpt:
    | string
    | null;

  body_sha256:
    | string
    | null;

  body_bytes_captured: number;
  body_truncated: boolean;

  declared_content_length:
    | number
    | null;

  redirect_blocked: boolean;
}

export interface BOLACaseResult {
  case_id: string;
  case_name: string;

  operation_key: string;

  identity_id: string;
  identity_name: string;

  resource_type: string;

  baseline_object_id:
    | string
    | null;

  probe_object_id: string;

  expected_probe_status_codes: number[];

  outcome: BOLAOutcome;
  explanation: string;

  matching_response_fields: Record<
    string,
    boolean
  >;

  issues: string[];

  baseline_evidence:
    | ResponseEvidence
    | null;

  probe_evidence:
    | ResponseEvidence
    | null;
}

export interface BOLAFinding {
  finding_id: string;
  case_id: string;

  category: "BOLA";

  title: string;
  description: string;

  severity: FindingSeverity;
  confidence: FindingConfidence;

  operation_key: string;

  identity_id: string;
  identity_name: string;

  resource_type: string;

  baseline_object_id:
    | string
    | null;

  probe_object_id: string;

  observed_status_code: number;

  matching_response_fields: Record<
    string,
    boolean
  >;
}

export interface BOLAScan {
  version: 1;

  scan_id: string;
  project_id: string;

  started_at: string;
  completed_at: string;

  status: ScanStatus;

  total_count: number;
  pass_count: number;
  finding_count: number;
  inconclusive_count: number;
  blocked_count: number;

  results: BOLACaseResult[];
  findings: BOLAFinding[];
}

export interface BOLAScanSummary {
  scan_id: string;
  project_id: string;

  started_at: string;
  completed_at: string;

  status: ScanStatus;

  total_count: number;
  pass_count: number;
  finding_count: number;
  inconclusive_count: number;
  blocked_count: number;
}

export interface BOLAScanList {
  project_id: string;
  items: BOLAScanSummary[];
}

export interface ScanDeletionResult {
  project_id: string;
  scan_id: string;
  deleted: boolean;
  retained_finding_history: boolean;
}

export interface ScanRetentionResult {
  project_id: string;
  keep_latest: number;
  before_count: number;
  after_count: number;
  deleted_count: number;
  deleted_scan_ids: string[];
  retained_finding_history: boolean;
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

function scansUrl(
  projectId: string,
): string {
  return (
    "/api/v1/projects/" +
    `${encodeURIComponent(projectId)}/` +
    "bola-scans"
  );
}

export async function listBOLAScans(
  projectId: string,
): Promise<BOLAScanList> {
  const response = await fetch(
    scansUrl(projectId),
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
  ) as BOLAScanList;
}

export async function getBOLAScan(
  projectId: string,
  scanId: string,
): Promise<BOLAScan> {
  const response = await fetch(
    `${scansUrl(projectId)}/${encodeURIComponent(scanId)}`,
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
  ) as BOLAScan;
}

export async function runBOLAScan(
  projectId: string,
  input: {
    acknowledge_authorization: boolean;
    confirmation: string;
    max_cases: number;
  },
): Promise<BOLAScan> {
  const response = await fetch(
    scansUrl(projectId),
    {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(input),
    },
  );

  if (!response.ok) {
    throw await buildApiError(
      response,
    );
  }

  return (
    await response.json()
  ) as BOLAScan;
}

export async function deleteBOLAScan(
  projectId: string,
  scanId: string,
  input: {
    acknowledge_evidence_loss: boolean;
    confirmation: string;
  },
): Promise<ScanDeletionResult> {
  const response = await fetch(
    `${scansUrl(projectId)}/${encodeURIComponent(scanId)}`,
    {
      method: "DELETE",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(input),
    },
  );

  if (!response.ok) {
    throw await buildApiError(
      response,
    );
  }

  return (
    await response.json()
  ) as ScanDeletionResult;
}

export async function pruneBOLAScans(
  projectId: string,
  input: {
    acknowledge_evidence_loss: boolean;
    confirmation: string;
    keep_latest: number;
  },
): Promise<ScanRetentionResult> {
  const response = await fetch(
    `${scansUrl(projectId)}/retention`,
    {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(input),
    },
  );

  if (!response.ok) {
    throw await buildApiError(
      response,
    );
  }

  return (
    await response.json()
  ) as ScanRetentionResult;
}