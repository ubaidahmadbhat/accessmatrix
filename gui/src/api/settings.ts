import {
  ApiRequestError,
} from "./projects";

export type NetworkAccessMode =
  | "public_only"
  | "public_and_loopback"
  | "private_networks";

export interface NetworkSafetySettings {
  access_mode: NetworkAccessMode;
  resolve_hostnames: boolean;
  dns_resolution_timeout_seconds: number;
  max_resolved_addresses: number;
  allow_link_local: boolean;
  allow_multicast: boolean;
  allow_reserved: boolean;
}

export interface ExecutionSettings {
  default_timeout_seconds: number;
  max_request_bytes: number;
  max_response_bytes: number;
  rate_limit_requests: number;
  rate_limit_window_seconds: number;
  max_parallel_requests: number;
}

export interface EvidenceSettings {
  body_excerpt_characters: number;
  store_response_headers: boolean;
  max_scan_bytes: number;
  max_report_bytes: number;
  scan_retention_keep_latest: number;
}

export interface AuditSettings {
  enabled: boolean;
  retention_days: number;
  max_events: number;
}

export interface ApplicationSettings {
  version: 1;
  network: NetworkSafetySettings;
  execution: ExecutionSettings;
  evidence: EvidenceSettings;
  audit: AuditSettings;
}

export type AddressClassification =
  | "global"
  | "loopback"
  | "private"
  | "link_local"
  | "multicast"
  | "reserved"
  | "unspecified";

export interface ResolvedTargetAddress {
  address: string;
  classification: AddressClassification;
  permitted: boolean;
}

export interface TargetValidationResult {
  original_url: string;
  normalized_url: string | null;
  scheme: string | null;
  hostname: string | null;
  port: number | null;
  valid: boolean;
  permitted: boolean;
  resolution_performed: boolean;
  dns_pin_recommended: boolean;
  addresses: ResolvedTargetAddress[];
  issues: string[];
  policy_violations: string[];
}

export type AuditOutcome =
  | "success"
  | "failure"
  | "denied";

export interface AuditEvent {
  version: 1;
  event_id: string;
  occurred_at: string;
  event_type: string;
  outcome: AuditOutcome;
  actor: string;
  message: string;
  project_id: string | null;
  resource_id: string | null;
  details: Record<
    string,
    string | number | boolean | null
  >;
}

export interface AuditEventList {
  total_count: number;
  items: AuditEvent[];
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

export async function getApplicationSettings(
): Promise<ApplicationSettings> {
  const response = await fetch(
    "/api/v1/settings",
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
  ) as ApplicationSettings;
}

export async function saveApplicationSettings(
  settings: ApplicationSettings,
): Promise<ApplicationSettings> {
  const response = await fetch(
    "/api/v1/settings",
    {
      method: "PUT",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(
        settings,
      ),
    },
  );

  if (!response.ok) {
    throw await buildApiError(
      response,
    );
  }

  return (
    await response.json()
  ) as ApplicationSettings;
}

export async function resetApplicationSettings(
  confirmation: string,
): Promise<ApplicationSettings> {
  const response = await fetch(
    "/api/v1/settings/reset",
    {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        confirmation,
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
  ) as ApplicationSettings;
}

export async function validateTarget(
  url: string,
): Promise<TargetValidationResult> {
  const response = await fetch(
    "/api/v1/settings/validate-target",
    {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        url,
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
  ) as TargetValidationResult;
}

export async function listAuditEvents(
  limit = 100,
): Promise<AuditEventList> {
  const response = await fetch(
    `/api/v1/audit-events?limit=${encodeURIComponent(String(limit))}`,
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
  ) as AuditEventList;
}