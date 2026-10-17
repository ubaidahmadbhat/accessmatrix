export interface Project {
  id: string;
  name: string;
  description: string | null;
  base_url: string | null;
  openapi_version: string | null;
  openapi_title: string | null;
  spec_filename: string | null;
  operation_count: number;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreateInput {
  name: string;
  description: string | null;
  base_url: string | null;
}

interface ApiErrorPayload {
  detail?: string;
}

export class ApiRequestError extends Error {
  readonly status: number;

  constructor(
    message: string,
    status: number,
  ) {
    super(message);

    this.name = "ApiRequestError";
    this.status = status;
  }
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

export async function listProjects(): Promise<Project[]> {
  const response = await fetch(
    "/api/v1/projects",
    {
      headers: {
        Accept: "application/json",
      },
    },
  );

  if (!response.ok) {
    throw await buildApiError(response);
  }

  return (await response.json()) as Project[];
}

export async function createProject(
  input: ProjectCreateInput,
): Promise<Project> {
  const response = await fetch(
    "/api/v1/projects",
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

  return (await response.json()) as Project;
}

export async function getProject(
  projectId: string,
): Promise<Project> {
  const response = await fetch(
    `/api/v1/projects/${encodeURIComponent(projectId)}`,
    {
      headers: {
        Accept: "application/json",
      },
    },
  );

  if (!response.ok) {
    throw await buildApiError(response);
  }

  return (await response.json()) as Project;
}

export async function deleteProject(
  projectId: string,
): Promise<void> {
  const response = await fetch(
    `/api/v1/projects/${encodeURIComponent(projectId)}`,
    {
      method: "DELETE",
    },
  );

  if (!response.ok) {
    throw await buildApiError(response);
  }
}

export interface UploadOpenAPIInput {
  projectId: string;
  file: File;
}

export async function uploadOpenAPIDocument({
  projectId,
  file,
}: UploadOpenAPIInput): Promise<Project> {
  const formData = new FormData();

  formData.append(
    "file",
    file,
    file.name,
  );

  const response = await fetch(
    `/api/v1/projects/${encodeURIComponent(projectId)}/openapi`,
    {
      method: "POST",
      headers: {
        Accept: "application/json",
      },
      body: formData,
    },
  );

  if (!response.ok) {
    throw await buildApiError(response);
  }

  return (await response.json()) as Project;
}