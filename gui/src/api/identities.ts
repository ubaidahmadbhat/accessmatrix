import { ApiRequestError } from "./projects";

export type AuthType =
  | "none"
  | "bearer"
  | "api_key"
  | "basic"
  | "cookie"
  | "custom_header";

export type SecretSource =
  | "environment"
  | "keyring";

export type AuthLocation =
  | "header"
  | "query"
  | "cookie";

export interface IdentityProfile {
  id: string;
  project_id: string;
  name: string;
  description: string | null;
  role: string;
  tenant: string | null;
  department: string | null;
  auth_type: AuthType;
  secret_source: SecretSource;
  secret_reference: string | null;
  username_reference: string | null;
  password_reference: string | null;
  auth_location: AuthLocation | null;
  auth_name: string | null;
  auth_prefix: string | null;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface IdentityInput {
  name: string;
  description: string | null;
  role: string;
  tenant: string | null;
  department: string | null;
  auth_type: AuthType;
  secret_source: SecretSource;
  secret_reference: string | null;
  username_reference: string | null;
  password_reference: string | null;
  auth_location: AuthLocation | null;
  auth_name: string | null;
  auth_prefix: string | null;
  enabled: boolean;
}

export interface CredentialReferenceStatus {
  field_name: string;
  reference: string | null;
  source: SecretSource;
  available: boolean;
}

export interface IdentityCredentialStatus {
  identity_id: string;
  identity_name: string;
  role: string;
  enabled: boolean;
  auth_type: AuthType;
  secret_source: SecretSource;
  ready: boolean;
  references: CredentialReferenceStatus[];
  message: string;
}

export interface ProjectCredentialStatuses {
  project_id: string;
  total_count: number;
  ready_count: number;
  unready_count: number;
  disabled_count: number;
  statuses: IdentityCredentialStatus[];
}

interface ApiErrorPayload {
  detail?: string;
}

async function buildApiError(
  response: Response,
): Promise<ApiRequestError> {
  let message =
    `Request failed with HTTP ${response.status}.`;

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
    const responseText =
      await response.text();

    if (responseText.trim()) {
      message = responseText.trim();
    }
  }

  return new ApiRequestError(
    message,
    response.status,
  );
}

export async function listIdentities(
  projectId: string,
): Promise<IdentityProfile[]> {
  const response = await fetch(
    `/api/v1/projects/${encodeURIComponent(projectId)}/identities`,
    {
      headers: {
        Accept: "application/json",
      },
    },
  );

  if (!response.ok) {
    throw await buildApiError(response);
  }

  return (
    await response.json()
  ) as IdentityProfile[];
}

export async function createIdentity(
  projectId: string,
  input: IdentityInput,
): Promise<IdentityProfile> {
  const response = await fetch(
    `/api/v1/projects/${encodeURIComponent(projectId)}/identities`,
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
    throw await buildApiError(response);
  }

  return (
    await response.json()
  ) as IdentityProfile;
}

export async function updateIdentity(
  projectId: string,
  identityId: string,
  input: IdentityInput,
): Promise<IdentityProfile> {
  const response = await fetch(
    `/api/v1/projects/${encodeURIComponent(projectId)}/identities/${encodeURIComponent(identityId)}`,
    {
      method: "PUT",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(input),
    },
  );

  if (!response.ok) {
    throw await buildApiError(response);
  }

  return (
    await response.json()
  ) as IdentityProfile;
}

export async function deleteIdentity(
  projectId: string,
  identityId: string,
): Promise<void> {
  const response = await fetch(
    `/api/v1/projects/${encodeURIComponent(projectId)}/identities/${encodeURIComponent(identityId)}`,
    {
      method: "DELETE",
    },
  );

  if (!response.ok) {
    throw await buildApiError(response);
  }
}

export async function getIdentityCredentialStatus(
  projectId: string,
  identityId: string,
): Promise<IdentityCredentialStatus> {
  const response = await fetch(
    `/api/v1/projects/${encodeURIComponent(projectId)}/identities/${encodeURIComponent(identityId)}/credential-status`,
    {
      headers: {
        Accept: "application/json",
      },
    },
  );

  if (!response.ok) {
    throw await buildApiError(response);
  }

  return (
    await response.json()
  ) as IdentityCredentialStatus;
}

export async function getProjectCredentialStatuses(
  projectId: string,
): Promise<ProjectCredentialStatuses> {
  const response = await fetch(
    `/api/v1/projects/${encodeURIComponent(projectId)}/identities/credential-statuses`,
    {
      headers: {
        Accept: "application/json",
      },
    },
  );

  if (!response.ok) {
    throw await buildApiError(response);
  }

  return (
    await response.json()
  ) as ProjectCredentialStatuses;
}