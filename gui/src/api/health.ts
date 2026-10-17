export interface HealthResponse {
  status: string;
  application: string;
  version: string;
  python_version: string;
  platform: string;
  data_directory: string;
}

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch("/api/v1/health", {
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(
      `Health request failed with HTTP ${response.status}`,
    );
  }

  return (await response.json()) as HealthResponse;
}