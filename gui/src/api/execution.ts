import { ApiRequestError } from "./projects";

export interface ExecuteOperationInput {
  operation_key: string;
  identity_id: string;
  path_parameters: Record<string, string>;
  query_parameters: Record<string, string>;
  headers: Record<string, string>;
  json_body: unknown | null;
  timeout_seconds: number;
  allow_unsafe: boolean;
  confirmation: string | null;
}

export interface ExecuteOperationResult {
  operation_key: string;
  identity_id: string;
  identity_name: string;
  method: string;
  request_url: string;
  request_header_names: string[];
  status_code: number;
  reason_phrase: string;
  elapsed_ms: number;
  response_headers: Record<string, string>;
  body_text: string | null;
  body_bytes_captured: number;
  body_truncated: boolean;
  declared_content_length: number | null;
  redirect_blocked: boolean;
  rate_limit_remaining: number;
}

interface ValidationErrorItem {
  msg?: string;
}

interface ApiErrorPayload {
  detail?:
    | string
    | ValidationErrorItem[];
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

      if (
        typeof payload.detail ===
        "string"
      ) {
        message = payload.detail;
      } else if (
        Array.isArray(
          payload.detail,
        )
      ) {
        const validationMessages =
          payload.detail
            .map((item) => item.msg)
            .filter(
              (
                item,
              ): item is string =>
                typeof item ===
                "string",
            );

        if (
          validationMessages.length > 0
        ) {
          message =
            validationMessages.join(
              " ",
            );
        }
      }
    } catch {
      message = responseText.trim();
    }
  }

  return new ApiRequestError(
    message,
    response.status,
  );
}

export async function executeOperation(
  projectId: string,
  input: ExecuteOperationInput,
): Promise<ExecuteOperationResult> {
  const response = await fetch(
    `/api/v1/projects/${encodeURIComponent(projectId)}/execute`,
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
  ) as ExecuteOperationResult;
}