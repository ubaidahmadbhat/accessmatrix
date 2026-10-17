import {
  ApiRequestError,
} from "./projects";

export type FindingCategory =
  | "BOLA"
  | "BFLA"
  | "BOPLA";

export type FindingStatus =
  | "open"
  | "resolved"
  | "false_positive"
  | "accepted_risk";

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

export interface FindingRecord {
  version: 1;

  finding_id: string;
  fingerprint: string;
  project_id: string;

  category: FindingCategory;

  title: string;
  description: string;

  severity: FindingSeverity;
  confidence: FindingConfidence;
  status: FindingStatus;

  operation_key: string;

  identity_id: string;
  identity_name: string;

  resource_type: string;

  baseline_object_id:
    | string
    | null;

  probe_object_id: string;

  first_seen_at: string;
  last_seen_at: string;
  updated_at: string;

  occurrence_count: number;
  reopened_count: number;

  last_observed_status_code: number;

  matching_response_fields: Record<
    string,
    boolean
  >;

  scan_ids: string[];
  source_finding_ids: string[];

  resolution_note:
    | string
    | null;
}

export interface FindingList {
  project_id: string;

  total_count: number;
  open_count: number;
  resolved_count: number;
  false_positive_count: number;
  accepted_risk_count: number;

  items: FindingRecord[];
}

export interface UpdateProjectFindingInput {
  projectId: string;
  fingerprint: string;
  status: FindingStatus;
  note: string | null;
}

interface ApiErrorObject {
  message?: string;
  issues?: string[];
}

interface ApiValidationError {
  msg?: string;
}

interface ApiErrorPayload {
  detail?:
    | string
    | ApiErrorObject
    | ApiValidationError[];
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

function findingsUrl(
  projectId: string,
): string {
  return (
    "/api/v1/projects/" +
    `${encodeURIComponent(projectId)}/` +
    "findings"
  );
}

export async function listProjectFindings(
  projectId: string,
): Promise<FindingList> {
  const response = await fetch(
    findingsUrl(projectId),
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
  ) as FindingList;
}

export async function getProjectFinding(
  projectId: string,
  fingerprint: string,
): Promise<FindingRecord> {
  const response = await fetch(
    `${findingsUrl(projectId)}/${encodeURIComponent(fingerprint)}`,
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
  ) as FindingRecord;
}

export async function updateProjectFinding(
  input: UpdateProjectFindingInput,
): Promise<FindingRecord> {
  const response = await fetch(
    `${findingsUrl(input.projectId)}/${encodeURIComponent(input.fingerprint)}`,
    {
      method: "PATCH",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        status: input.status,
        note: input.note,
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
  ) as FindingRecord;
}

export async function rebuildProjectFindings(
  projectId: string,
): Promise<FindingList> {
  const response = await fetch(
    `${findingsUrl(projectId)}/rebuild`,
    {
      method: "POST",
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
  ) as FindingList;
}