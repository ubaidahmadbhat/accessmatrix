import { ApiRequestError } from "./projects";

export interface OperationParameter {
  name: string;
  location: string;
  required: boolean;
  schema_type: string | null;
  description: string | null;
}

export interface OpenAPIOperation {
  key: string;
  method: string;
  path: string;
  operation_id: string;
  summary: string | null;
  description: string | null;
  tags: string[];
  deprecated: boolean;
  security_required: boolean;
  parameters: OperationParameter[];
  request_content_types: string[];
  response_codes: string[];
}

export interface ProjectOperationsResponse {
  project_id: string;
  openapi_title: string;
  openapi_version: string;
  operation_count: number;
  operations: OpenAPIOperation[];
}

interface ApiErrorPayload {
  detail?: string;
}

async function buildApiError(
  response: Response,
): Promise<ApiRequestError> {
  let message = `Request failed with HTTP ${response.status}.`;

  try {
    const payload =
      (await response.json()) as ApiErrorPayload;

    if (
      typeof payload.detail === "string" &&
      payload.detail.trim()
    ) {
      message = payload.detail;
    }
  } catch {
    const responseText = await response.text();

    if (responseText.trim()) {
      message = responseText.trim();
    }
  }

  return new ApiRequestError(
    message,
    response.status,
  );
}

export async function getProjectOperations(
  projectId: string,
): Promise<ProjectOperationsResponse> {
  const response = await fetch(
    `/api/v1/projects/${encodeURIComponent(projectId)}/operations`,
    {
      headers: {
        Accept: "application/json",
      },
    },
  );

  if (!response.ok) {
    throw await buildApiError(response);
  }

  return (await response.json()) as ProjectOperationsResponse;
}