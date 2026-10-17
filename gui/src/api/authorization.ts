import {
  ApiRequestError,
} from "./projects";

export type AccessExpectation =
  | "allow"
  | "deny";

export interface ResourceDefinition {
  name: string;
  display_name: string;
  description: string | null;
}

export interface ObjectRecord {
  resource_type: string;
  object_id: string;
  display_name: string | null;
  owner_identity_id: string | null;
  tenant: string | null;
  attributes: Record<string, string>;
}

export interface OperationObjectBinding {
  operation_key: string;
  resource_type: string;
  path_parameter: string;
  response_id_field: string | null;
  response_owner_field: string | null;
  response_tenant_field: string | null;
}

export interface AuthorizationCase {
  case_id: string;
  name: string;
  operation_key: string;
  identity_id: string;
  resource_type: string;
  object_id: string;
  expectation: AccessExpectation;
  expected_status_codes: number[];
  enabled: boolean;
}

export interface AuthorizationDataset {
  version: 1;
  resources: ResourceDefinition[];
  objects: ObjectRecord[];
  bindings: OperationObjectBinding[];
  cases: AuthorizationCase[];
}

export interface AuthorizationDatasetValidation {
  valid: boolean;
  issue_count: number;
  issues: string[];
}

export interface BOLATestPlanItem {
  case_id: string;
  case_name: string;
  operation_key: string;
  identity_id: string;
  identity_name: string;
  resource_type: string;
  path_parameter: string | null;
  baseline_object_id: string | null;
  probe_object_id: string;
  probe_owner_identity_id: string | null;
  probe_owner_identity_name: string | null;
  baseline_path_parameters: Record<
    string,
    string
  >;
  probe_path_parameters: Record<
    string,
    string
  >;
  expected_probe_status_codes: number[];
  ready: boolean;
  issues: string[];
}

export interface BOLATestPlan {
  project_id: string;
  total_count: number;
  ready_count: number;
  blocked_count: number;
  items: BOLATestPlanItem[];
}

interface ApiErrorDetailObject {
  message?: string;
  issues?: string[];
}

interface ApiErrorPayload {
  detail?:
    | string
    | ApiErrorDetailObject
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
      sections.push(detail.message);
    }

    if (
      Array.isArray(detail.issues)
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

function datasetUrl(
  projectId: string,
): string {
  return (
    `/api/v1/projects/` +
    `${encodeURIComponent(projectId)}/` +
    "authorization-dataset"
  );
}

export async function getAuthorizationDataset(
  projectId: string,
): Promise<AuthorizationDataset> {
  const response = await fetch(
    datasetUrl(projectId),
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
  ) as AuthorizationDataset;
}

export async function validateAuthorizationDataset(
  projectId: string,
  dataset: AuthorizationDataset,
): Promise<AuthorizationDatasetValidation> {
  const response = await fetch(
    `${datasetUrl(projectId)}/validate`,
    {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(dataset),
    },
  );

  if (!response.ok) {
    throw await buildApiError(
      response,
    );
  }

  return (
    await response.json()
  ) as AuthorizationDatasetValidation;
}

export async function saveAuthorizationDataset(
  projectId: string,
  dataset: AuthorizationDataset,
): Promise<AuthorizationDataset> {
  const response = await fetch(
    datasetUrl(projectId),
    {
      method: "PUT",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(dataset),
    },
  );

  if (!response.ok) {
    throw await buildApiError(
      response,
    );
  }

  return (
    await response.json()
  ) as AuthorizationDataset;
}

export async function seedDemoAuthorizationDataset(
  projectId: string,
): Promise<AuthorizationDataset> {
  const response = await fetch(
    `${datasetUrl(projectId)}/demo-seed`,
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
  ) as AuthorizationDataset;
}

export async function getBOLATestPlan(
  projectId: string,
): Promise<BOLATestPlan> {
  const response = await fetch(
    `${datasetUrl(projectId)}/bola-plan`,
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
  ) as BOLATestPlan;
}