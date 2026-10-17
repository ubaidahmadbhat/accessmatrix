import {
  useQuery,
} from "@tanstack/react-query";
import {
  AlertCircle,
  ArrowLeft,
  Braces,
  Database,
  FileCode2,
  Fingerprint,
  Globe2,
  KeyRound,
  LoaderCircle,
  RefreshCw,
  ShieldCheck,
  Terminal,
} from "lucide-react";
import {
  useMemo,
  useState,
} from "react";
import {
  useNavigate,
  useParams,
} from "react-router-dom";

import {
  getProjectOperations,
} from "../api/operations";
import {
  ApiRequestError,
  getProject,
} from "../api/projects";
import {
  AuthorizationDatasetPanel,
} from "../components/AuthorizationDatasetPanel";
import {
  BOLAScanPanel,
} from "../components/BOLAScanPanel";
import {
  IdentityManager,
} from "../components/IdentityManager";
import {
  IdentityReadinessPanel,
} from "../components/IdentityReadinessPanel";
import {
  OperationsExplorer,
} from "../components/OperationsExplorer";
import {
  RequestConsole,
} from "../components/RequestConsole";

import "./ProjectWorkspacePage.css";
import "./WorkspaceTabs.css";

type WorkspaceTab =
  | "operations"
  | "identities"
  | "credentials"
  | "authorization"
  | "bola"
  | "console";

function getErrorMessage(
  error: unknown,
): string {
  if (error instanceof ApiRequestError) {
    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "An unexpected error occurred.";
}

export function ProjectWorkspacePage() {
  const navigate = useNavigate();

  const {
    projectId,
  } = useParams<{
    projectId: string;
  }>();

  const [
    activeTab,
    setActiveTab,
  ] = useState<WorkspaceTab>(
    "operations",
  );

  const projectQuery = useQuery({
    queryKey: [
      "projects",
      projectId,
    ],

    queryFn: () => {
      if (!projectId) {
        throw new Error(
          "Project identifier is missing.",
        );
      }

      return getProject(projectId);
    },

    enabled: Boolean(projectId),
  });

  const operationsQuery = useQuery({
    queryKey: [
      "projects",
      projectId,
      "operations",
    ],

    queryFn: () => {
      if (!projectId) {
        throw new Error(
          "Project identifier is missing.",
        );
      }

      return getProjectOperations(
        projectId,
      );
    },

    enabled: Boolean(projectId),
  });

  const operations = useMemo(
    () =>
      operationsQuery.data?.operations ??
      [],
    [
      operationsQuery.data
        ?.operations,
    ],
  );

  const securedCount = useMemo(
    () =>
      operations.filter(
        (operation) =>
          operation.security_required,
      ).length,
    [operations],
  );

  const publicCount =
    operations.length - securedCount;

  const deprecatedCount = useMemo(
    () =>
      operations.filter(
        (operation) =>
          operation.deprecated,
      ).length,
    [operations],
  );

  const combinedError =
    projectQuery.error ??
    operationsQuery.error;

  const isLoading =
    projectQuery.isPending ||
    operationsQuery.isPending;

  function refreshWorkspace(): void {
    void projectQuery.refetch();
    void operationsQuery.refetch();
  }

  if (!projectId) {
    return (
      <section className="workspace-error-state">
        <AlertCircle
          aria-hidden="true"
          size={30}
        />

        <h2>
          Project identifier missing
        </h2>

        <button
          className="workspace-button workspace-button-primary"
          onClick={() => {
            navigate("/projects");
          }}
          type="button"
        >
          Return to projects
        </button>
      </section>
    );
  }

  return (
    <div className="page project-workspace-page">
      <section className="workspace-project-header">
        <div className="workspace-project-heading">
          <button
            aria-label="Return to projects"
            className="workspace-icon-button"
            onClick={() => {
              navigate("/projects");
            }}
            type="button"
          >
            <ArrowLeft
              aria-hidden="true"
              size={20}
            />
          </button>

          <div>
            <span className="workspace-section-label">
              Project workspace
            </span>

            <h2>
              {projectQuery.data?.name ??
                "Loading project"}
            </h2>

            <p>
              {projectQuery.data
                ?.description ??
                "Review the imported API surface and prepare authorization testing."}
            </p>
          </div>
        </div>

        <button
          className="workspace-button workspace-button-secondary"
          disabled={
            projectQuery.isFetching ||
            operationsQuery.isFetching
          }
          onClick={refreshWorkspace}
          type="button"
        >
          <RefreshCw
            aria-hidden="true"
            className={
              projectQuery.isFetching ||
              operationsQuery.isFetching
                ? "workspace-spinner"
                : undefined
            }
            size={17}
          />

          Refresh
        </button>
      </section>

      {combinedError ? (
        <section
          className="workspace-alert"
          role="alert"
        >
          <AlertCircle
            aria-hidden="true"
            size={21}
          />

          <div>
            <strong>
              The workspace could not be loaded.
            </strong>

            <span>
              {getErrorMessage(
                combinedError,
              )}
            </span>
          </div>
        </section>
      ) : null}

      {isLoading ? (
        <section className="workspace-loading-state">
          <LoaderCircle
            aria-hidden="true"
            className="workspace-spinner"
            size={31}
          />

          <strong>
            Loading project workspace
          </strong>
        </section>
      ) : null}

      {!isLoading &&
      !combinedError ? (
        <>
          <section className="workspace-metadata-grid">
            <article className="workspace-metadata-card">
              <FileCode2
                aria-hidden="true"
                size={21}
              />

              <div>
                <span>
                  OpenAPI document
                </span>

                <strong>
                  {operationsQuery.data
                    ?.openapi_title ??
                    "Not available"}
                </strong>

                <small>
                  Version{" "}
                  {operationsQuery.data
                    ?.openapi_version ??
                    "unknown"}
                </small>
              </div>
            </article>

            <article className="workspace-metadata-card">
              <Globe2
                aria-hidden="true"
                size={21}
              />

              <div>
                <span>
                  Target base URL
                </span>

                <strong
                  title={
                    projectQuery.data
                      ?.base_url ?? ""
                  }
                >
                  {projectQuery.data
                    ?.base_url ??
                    "Not configured"}
                </strong>

                <small>
                  Requests are restricted to
                  this exact origin.
                </small>
              </div>
            </article>

            <article className="workspace-metadata-card">
              <Braces
                aria-hidden="true"
                size={21}
              />

              <div>
                <span>
                  Imported file
                </span>

                <strong>
                  {projectQuery.data
                    ?.spec_filename ??
                    "Not available"}
                </strong>

                <small>
                  Stored in the local workspace.
                </small>
              </div>
            </article>
          </section>

          <section className="workspace-stat-grid">
            <article className="workspace-stat-card">
              <span>
                Total operations
              </span>

              <strong>
                {operations.length}
              </strong>
            </article>

            <article className="workspace-stat-card workspace-stat-secured">
              <span>
                Secured
              </span>

              <strong>
                {securedCount}
              </strong>
            </article>

            <article className="workspace-stat-card workspace-stat-public">
              <span>
                Public
              </span>

              <strong>
                {publicCount}
              </strong>
            </article>

            <article className="workspace-stat-card workspace-stat-deprecated">
              <span>
                Deprecated
              </span>

              <strong>
                {deprecatedCount}
              </strong>
            </article>
          </section>

          <nav
            aria-label="Project workspace sections"
            className="workspace-tabs"
          >
            <button
              aria-current={
                activeTab === "operations"
                  ? "page"
                  : undefined
              }
              className={
                activeTab === "operations"
                  ? "workspace-tab workspace-tab-active"
                  : "workspace-tab"
              }
              onClick={() => {
                setActiveTab(
                  "operations",
                );
              }}
              type="button"
            >
              <Braces
                aria-hidden="true"
                size={17}
              />

              Operations

              <span className="workspace-tab-count">
                {operations.length}
              </span>
            </button>

            <button
              aria-current={
                activeTab === "identities"
                  ? "page"
                  : undefined
              }
              className={
                activeTab === "identities"
                  ? "workspace-tab workspace-tab-active"
                  : "workspace-tab"
              }
              onClick={() => {
                setActiveTab(
                  "identities",
                );
              }}
              type="button"
            >
              <Fingerprint
                aria-hidden="true"
                size={17}
              />

              Identities
            </button>

            <button
              aria-current={
                activeTab === "credentials"
                  ? "page"
                  : undefined
              }
              className={
                activeTab === "credentials"
                  ? "workspace-tab workspace-tab-active"
                  : "workspace-tab"
              }
              onClick={() => {
                setActiveTab(
                  "credentials",
                );
              }}
              type="button"
            >
              <KeyRound
                aria-hidden="true"
                size={17}
              />

              Credential readiness
            </button>

            <button
              aria-current={
                activeTab === "authorization"
                  ? "page"
                  : undefined
              }
              className={
                activeTab === "authorization"
                  ? "workspace-tab workspace-tab-active"
                  : "workspace-tab"
              }
              onClick={() => {
                setActiveTab(
                  "authorization",
                );
              }}
              type="button"
            >
              <Database
                aria-hidden="true"
                size={17}
              />

              Authorization dataset
            </button>

            <button
              aria-current={
                activeTab === "bola"
                  ? "page"
                  : undefined
              }
              className={
                activeTab === "bola"
                  ? "workspace-tab workspace-tab-active"
                  : "workspace-tab"
              }
              onClick={() => {
                setActiveTab(
                  "bola",
                );
              }}
              type="button"
            >
              <ShieldCheck
                aria-hidden="true"
                size={17}
              />

              BOLA scans
            </button>

            <button
              aria-current={
                activeTab === "console"
                  ? "page"
                  : undefined
              }
              className={
                activeTab === "console"
                  ? "workspace-tab workspace-tab-active"
                  : "workspace-tab"
              }
              onClick={() => {
                setActiveTab(
                  "console",
                );
              }}
              type="button"
            >
              <Terminal
                aria-hidden="true"
                size={17}
              />

              Request console
            </button>
          </nav>

          <div className="workspace-tab-content">
            {activeTab === "operations" ? (
              <OperationsExplorer
                operations={operations}
              />
            ) : activeTab ===
              "identities" ? (
              <IdentityManager
                projectId={projectId}
              />
            ) : activeTab ===
              "credentials" ? (
              <IdentityReadinessPanel
                projectId={projectId}
              />
            ) : activeTab ===
              "authorization" ? (
              <AuthorizationDatasetPanel
                projectId={projectId}
              />
            ) : activeTab ===
              "bola" ? (
              <BOLAScanPanel
                projectId={projectId}
              />
            ) : (
              <RequestConsole
                operations={operations}
                projectId={projectId}
              />
            )}
          </div>
        </>
      ) : null}
    </div>
  );
}