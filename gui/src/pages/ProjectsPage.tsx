import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  AlertCircle,
  CalendarDays,
  CheckCircle2,
  FileCode2,
  FolderKanban,
  FolderOpen,
  Globe2,
  LoaderCircle,
  Plus,
  RefreshCw,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import type {
  ChangeEvent,
  FormEvent,
} from "react";
import {
  useRef,
  useState,
} from "react";
import {
  useNavigate,
} from "react-router-dom";

import {
  ApiRequestError,
  createProject,
  deleteProject,
  listProjects,
  uploadOpenAPIDocument,
} from "../api/projects";
import type {
  Project,
  ProjectCreateInput,
  UploadOpenAPIInput,
} from "../api/projects";

import "./ProjectsPage.css";

const EMPTY_PROJECT_FORM: ProjectCreateInput = {
  name: "",
  description: "",
  base_url: "",
};

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

function formatDate(
  value: string,
): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat(
    undefined,
    {
      year: "numeric",
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    },
  ).format(date);
}

interface CreateProjectDialogProps {
  form: ProjectCreateInput;
  isPending: boolean;
  onChange: (
    field: keyof ProjectCreateInput,
    value: string,
  ) => void;
  onClose: () => void;
  onSubmit: (
    event: FormEvent<HTMLFormElement>,
  ) => void;
}

function CreateProjectDialog({
  form,
  isPending,
  onChange,
  onClose,
  onSubmit,
}: CreateProjectDialogProps) {
  return (
    <div className="projects-dialog-backdrop">
      <section
        aria-labelledby="create-project-title"
        aria-modal="true"
        className="projects-dialog"
        role="dialog"
      >
        <header className="projects-dialog-header">
          <div>
            <span className="projects-section-label">
              New workspace
            </span>

            <h2 id="create-project-title">
              Create project
            </h2>

            <p>
              Create a workspace for one API,
              environment, and authorization policy.
            </p>
          </div>

          <button
            aria-label="Close create project dialog"
            className="projects-icon-button"
            disabled={isPending}
            onClick={onClose}
            type="button"
          >
            <X
              aria-hidden="true"
              size={20}
            />
          </button>
        </header>

        <form
          className="projects-form"
          onSubmit={onSubmit}
        >
          <label className="projects-field">
            <span>
              Project name
              <strong aria-hidden="true">
                *
              </strong>
            </span>

            <input
              autoFocus
              maxLength={120}
              minLength={2}
              onChange={(event) => {
                onChange(
                  "name",
                  event.target.value,
                );
              }}
              placeholder="Invoice API"
              required
              type="text"
              value={form.name}
            />
          </label>

          <label className="projects-field">
            <span>
              Description
            </span>

            <textarea
              maxLength={4000}
              onChange={(event) => {
                onChange(
                  "description",
                  event.target.value,
                );
              }}
              placeholder="Authorization regression tests for the invoice service."
              rows={4}
              value={form.description ?? ""}
            />
          </label>

          <label className="projects-field">
            <span>
              Target base URL
            </span>

            <input
              maxLength={2048}
              onChange={(event) => {
                onChange(
                  "base_url",
                  event.target.value,
                );
              }}
              placeholder="http://127.0.0.1:9000"
              type="url"
              value={form.base_url ?? ""}
            />

            <small>
              This can be added or changed later.
              No requests are sent while creating
              the project.
            </small>
          </label>

          <footer className="projects-dialog-actions">
            <button
              className="projects-button projects-button-secondary"
              disabled={isPending}
              onClick={onClose}
              type="button"
            >
              Cancel
            </button>

            <button
              className="projects-button projects-button-primary"
              disabled={
                isPending ||
                form.name.trim().length < 2
              }
              type="submit"
            >
              {isPending ? (
                <>
                  <LoaderCircle
                    aria-hidden="true"
                    className="projects-spinner"
                    size={17}
                  />
                  Creating
                </>
              ) : (
                <>
                  <Plus
                    aria-hidden="true"
                    size={17}
                  />
                  Create project
                </>
              )}
            </button>
          </footer>
        </form>
      </section>
    </div>
  );
}

interface DeleteProjectDialogProps {
  project: Project;
  isPending: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}

function DeleteProjectDialog({
  project,
  isPending,
  onCancel,
  onConfirm,
}: DeleteProjectDialogProps) {
  return (
    <div className="projects-dialog-backdrop">
      <section
        aria-labelledby="delete-project-title"
        aria-modal="true"
        className="projects-dialog projects-delete-dialog"
        role="dialog"
      >
        <header className="projects-dialog-header">
          <div>
            <span className="projects-section-label projects-danger-label">
              Destructive action
            </span>

            <h2 id="delete-project-title">
              Delete project
            </h2>
          </div>

          <button
            aria-label="Close delete project dialog"
            className="projects-icon-button"
            disabled={isPending}
            onClick={onCancel}
            type="button"
          >
            <X
              aria-hidden="true"
              size={20}
            />
          </button>
        </header>

        <div className="projects-delete-message">
          <div className="projects-delete-icon">
            <Trash2
              aria-hidden="true"
              size={24}
            />
          </div>

          <div>
            <p>
              Delete{" "}
              <strong>
                {project.name}
              </strong>
              ?
            </p>

            <span>
              Its locally stored OpenAPI document
              and project records will be removed.
              This action cannot currently be undone.
            </span>
          </div>
        </div>

        <footer className="projects-dialog-actions">
          <button
            className="projects-button projects-button-secondary"
            disabled={isPending}
            onClick={onCancel}
            type="button"
          >
            Cancel
          </button>

          <button
            className="projects-button projects-button-danger"
            disabled={isPending}
            onClick={onConfirm}
            type="button"
          >
            {isPending ? (
              <>
                <LoaderCircle
                  aria-hidden="true"
                  className="projects-spinner"
                  size={17}
                />
                Deleting
              </>
            ) : (
              <>
                <Trash2
                  aria-hidden="true"
                  size={17}
                />
                Delete project
              </>
            )}
          </button>
        </footer>
      </section>
    </div>
  );
}

export function ProjectsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const fileInputRef =
    useRef<HTMLInputElement>(null);

  const [
    createDialogOpen,
    setCreateDialogOpen,
  ] = useState(false);

  const [
    projectForm,
    setProjectForm,
  ] = useState<ProjectCreateInput>(
    EMPTY_PROJECT_FORM,
  );

  const [
    deleteTarget,
    setDeleteTarget,
  ] = useState<Project | null>(null);

  const [
    uploadTargetId,
    setUploadTargetId,
  ] = useState<string | null>(null);

  const projectsQuery = useQuery({
    queryKey: ["projects"],
    queryFn: listProjects,
  });

  const createMutation = useMutation({
    mutationFn: createProject,

    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["projects"],
      });

      setProjectForm(
        EMPTY_PROJECT_FORM,
      );

      setCreateDialogOpen(false);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteProject,

    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["projects"],
      });

      setDeleteTarget(null);
    },
  });

  const uploadMutation = useMutation({
    mutationFn: (
      input: UploadOpenAPIInput,
    ) => uploadOpenAPIDocument(input),

    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["projects"],
      });
    },

    onSettled: () => {
      setUploadTargetId(null);
    },
  });

  const combinedError =
    projectsQuery.error ??
    createMutation.error ??
    deleteMutation.error ??
    uploadMutation.error;

  function openCreateDialog(): void {
    createMutation.reset();

    setProjectForm(
      EMPTY_PROJECT_FORM,
    );

    setCreateDialogOpen(true);
  }

  function closeCreateDialog(): void {
    if (createMutation.isPending) {
      return;
    }

    createMutation.reset();
    setCreateDialogOpen(false);
  }

  function updateProjectForm(
    field: keyof ProjectCreateInput,
    value: string,
  ): void {
    setProjectForm((current) => ({
      ...current,
      [field]: value,
    }));
  }

  function submitProject(
    event: FormEvent<HTMLFormElement>,
  ): void {
    event.preventDefault();

    createMutation.mutate({
      name: projectForm.name.trim(),

      description:
        projectForm.description?.trim() ||
        null,

      base_url:
        projectForm.base_url?.trim() ||
        null,
    });
  }

  function beginOpenAPIUpload(
    projectId: string,
  ): void {
    uploadMutation.reset();
    setUploadTargetId(projectId);

    fileInputRef.current?.click();
  }

  function handleFileSelection(
    event: ChangeEvent<HTMLInputElement>,
  ): void {
    const selectedFile =
      event.target.files?.[0];

    event.target.value = "";

    if (
      !selectedFile ||
      !uploadTargetId
    ) {
      setUploadTargetId(null);
      return;
    }

    uploadMutation.mutate({
      projectId: uploadTargetId,
      file: selectedFile,
    });
  }

  function confirmDelete(): void {
    if (!deleteTarget) {
      return;
    }

    deleteMutation.mutate(
      deleteTarget.id,
    );
  }

  const projects =
    projectsQuery.data ?? [];

  return (
    <div className="page projects-page">
      <input
        accept=".yaml,.yml,.json,application/json,application/yaml,text/yaml"
        aria-hidden="true"
        className="projects-hidden-input"
        onChange={handleFileSelection}
        ref={fileInputRef}
        tabIndex={-1}
        type="file"
      />

      <section className="projects-toolbar">
        <div>
          <span className="projects-section-label">
            API workspaces
          </span>

          <h2>
            Projects
          </h2>

          <p>
            Manage API specifications, target
            environments, authorization identities,
            policies, and scan history.
          </p>
        </div>

        <div className="projects-toolbar-actions">
          <button
            aria-label="Refresh projects"
            className="projects-button projects-button-secondary"
            disabled={projectsQuery.isFetching}
            onClick={() => {
              void projectsQuery.refetch();
            }}
            type="button"
          >
            <RefreshCw
              aria-hidden="true"
              className={
                projectsQuery.isFetching
                  ? "projects-spinner"
                  : undefined
              }
              size={17}
            />

            Refresh
          </button>

          <button
            className="projects-button projects-button-primary"
            onClick={openCreateDialog}
            type="button"
          >
            <Plus
              aria-hidden="true"
              size={17}
            />

            Create project
          </button>
        </div>
      </section>

      {combinedError ? (
        <section
          className="projects-alert"
          role="alert"
        >
          <AlertCircle
            aria-hidden="true"
            size={21}
          />

          <div>
            <strong>
              The operation could not be completed.
            </strong>

            <span>
              {getErrorMessage(
                combinedError,
              )}
            </span>
          </div>
        </section>
      ) : null}

      {uploadMutation.isSuccess ? (
        <section
          className="projects-success"
          role="status"
        >
          <CheckCircle2
            aria-hidden="true"
            size={21}
          />

          <div>
            <strong>
              OpenAPI document imported.
            </strong>

            <span>
              The project metadata and operation
              count have been updated.
            </span>
          </div>
        </section>
      ) : null}

      {projectsQuery.isPending ? (
        <section className="projects-loading">
          <LoaderCircle
            aria-hidden="true"
            className="projects-spinner"
            size={28}
          />

          <strong>
            Loading projects
          </strong>
        </section>
      ) : null}

      {!projectsQuery.isPending &&
      projects.length === 0 ? (
        <section className="projects-empty-state">
          <div className="projects-empty-icon">
            <FolderKanban
              aria-hidden="true"
              size={31}
            />
          </div>

          <span className="projects-section-label">
            No projects yet
          </span>

          <h3>
            Create your first API workspace
          </h3>

          <p>
            A project holds the target environment,
            imported OpenAPI specification,
            authorization policy, identities,
            scans, findings, and reports.
          </p>

          <button
            className="projects-button projects-button-primary"
            onClick={openCreateDialog}
            type="button"
          >
            <Plus
              aria-hidden="true"
              size={17}
            />

            Create first project
          </button>
        </section>
      ) : null}

      {projects.length > 0 ? (
        <section
          aria-label="AccessMatrix projects"
          className="projects-grid"
        >
          {projects.map((project) => {
            const uploadingThisProject =
              uploadMutation.isPending &&
              uploadMutation.variables
                ?.projectId === project.id;

            return (
              <article
                className="project-card"
                key={project.id}
              >
                <header className="project-card-header">
                  <div className="project-card-title">
                    <div className="project-card-icon">
                      <FolderKanban
                        aria-hidden="true"
                        size={22}
                      />
                    </div>

                    <div>
                      <h3>
                        {project.name}
                      </h3>

                      <span>
                        {project.openapi_title ??
                          "OpenAPI specification not imported"}
                      </span>
                    </div>
                  </div>

                  <span
                    className={
                      project.openapi_version
                        ? "project-status project-status-ready"
                        : "project-status project-status-draft"
                    }
                  >
                    {project.openapi_version
                      ? "Configured"
                      : "Draft"}
                  </span>
                </header>

                <p className="project-description">
                  {project.description ??
                    "No project description has been provided."}
                </p>

                <dl className="project-metadata">
                  <div>
                    <dt>
                      <Globe2
                        aria-hidden="true"
                        size={16}
                      />
                      Base URL
                    </dt>

                    <dd
                      title={
                        project.base_url ?? ""
                      }
                    >
                      {project.base_url ??
                        "Not configured"}
                    </dd>
                  </div>

                  <div>
                    <dt>
                      <FileCode2
                        aria-hidden="true"
                        size={16}
                      />
                      OpenAPI
                    </dt>

                    <dd>
                      {project.openapi_version
                        ? `${project.openapi_version} · ${project.operation_count} operations`
                        : "No document imported"}
                    </dd>
                  </div>

                  <div>
                    <dt>
                      <CalendarDays
                        aria-hidden="true"
                        size={16}
                      />
                      Updated
                    </dt>

                    <dd>
                      {formatDate(
                        project.updated_at,
                      )}
                    </dd>
                  </div>
                </dl>

                {project.spec_filename ? (
                  <div className="project-specification">
                    <FileCode2
                      aria-hidden="true"
                      size={16}
                    />

                    <div>
                      <span>
                        Imported specification
                      </span>

                      <strong
                        title={
                          project.spec_filename
                        }
                      >
                        {project.spec_filename}
                      </strong>
                    </div>
                  </div>
                ) : null}

                <footer className="project-card-actions">
                  <button
                    className="projects-button projects-button-primary"
                    disabled={
                      !project.openapi_version
                    }
                    onClick={() => {
                      navigate(
                        `/projects/${project.id}`,
                      );
                    }}
                    title={
                      project.openapi_version
                        ? "Open project workspace"
                        : "Import an OpenAPI document first"
                    }
                    type="button"
                  >
                    <FolderOpen
                      aria-hidden="true"
                      size={17}
                    />

                    Open
                  </button>

                  <button
                    className="projects-button projects-button-secondary project-upload-button"
                    disabled={uploadMutation.isPending}
                    onClick={() => {
                      beginOpenAPIUpload(
                        project.id,
                      );
                    }}
                    type="button"
                  >
                    {uploadingThisProject ? (
                      <>
                        <LoaderCircle
                          aria-hidden="true"
                          className="projects-spinner"
                          size={17}
                        />

                        Importing
                      </>
                    ) : (
                      <>
                        <Upload
                          aria-hidden="true"
                          size={17}
                        />

                        {project.openapi_version
                          ? "Replace OpenAPI"
                          : "Import OpenAPI"}
                      </>
                    )}
                  </button>

                  <button
                    aria-label={`Delete ${project.name}`}
                    className="projects-icon-button projects-delete-button"
                    disabled={
                      deleteMutation.isPending ||
                      uploadMutation.isPending
                    }
                    onClick={() => {
                      deleteMutation.reset();
                      setDeleteTarget(project);
                    }}
                    title="Delete project"
                    type="button"
                  >
                    <Trash2
                      aria-hidden="true"
                      size={18}
                    />
                  </button>
                </footer>
              </article>
            );
          })}
        </section>
      ) : null}

      {createDialogOpen ? (
        <CreateProjectDialog
          form={projectForm}
          isPending={createMutation.isPending}
          onChange={updateProjectForm}
          onClose={closeCreateDialog}
          onSubmit={submitProject}
        />
      ) : null}

      {deleteTarget ? (
        <DeleteProjectDialog
          isPending={deleteMutation.isPending}
          onCancel={() => {
            if (!deleteMutation.isPending) {
              setDeleteTarget(null);
            }
          }}
          onConfirm={confirmDelete}
          project={deleteTarget}
        />
      ) : null}
    </div>
  );
}