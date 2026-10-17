import {
  useMutation,
  useQueries,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  AlertCircle,
  Ban,
  CheckCircle2,
  FileWarning,
  Filter,
  FolderKanban,
  Hash,
  LoaderCircle,
  RefreshCw,
  RotateCcw,
  Save,
  Search,
  ShieldAlert,
} from "lucide-react";
import {
  useState,
} from "react";

import type {
  FindingCategory,
  FindingRecord,
  FindingSeverity,
  FindingStatus,
  UpdateProjectFindingInput,
} from "../api/findings";
import {
  listProjectFindings,
  rebuildProjectFindings,
  updateProjectFinding,
} from "../api/findings";
import type {
  Project,
} from "../api/projects";
import {
  ApiRequestError,
  listProjects,
} from "../api/projects";

import "./FindingsPage.css";

interface FindingWithProject {
  finding: FindingRecord;
  project: Project;
}

interface FindingDetailProps {
  item: FindingWithProject;
  pending: boolean;
  onSave: (
    input: UpdateProjectFindingInput,
  ) => void;
}

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

  if (
    Number.isNaN(
      date.getTime(),
    )
  ) {
    return value;
  }

  return new Intl.DateTimeFormat(
    undefined,
    {
      dateStyle: "medium",
      timeStyle: "medium",
    },
  ).format(date);
}

function statusLabel(
  status: FindingStatus,
): string {
  switch (status) {
    case "false_positive":
      return "False positive";

    case "accepted_risk":
      return "Accepted risk";

    case "resolved":
      return "Resolved";

    default:
      return "Open";
  }
}

function statusClass(
  status: FindingStatus,
): string {
  return (
    "findings-status " +
    `findings-status-${status}`
  );
}

function severityClass(
  severity: FindingSeverity,
): string {
  return (
    "findings-severity " +
    `findings-severity-${severity}`
  );
}

function FindingDetail({
  item,
  pending,
  onSave,
}: FindingDetailProps) {
  const {
    finding,
    project,
  } = item;

  const [
    selectedStatus,
    setSelectedStatus,
  ] = useState<FindingStatus>(
    finding.status,
  );

  const [
    note,
    setNote,
  ] = useState(
    finding.resolution_note ?? "",
  );

  const normalizedNote =
    note.trim();

  const originalNote =
    finding.resolution_note?.trim() ??
    "";

  const noteRequired =
    selectedStatus !== "open";

  const changed =
    selectedStatus !== finding.status ||
    normalizedNote !== originalNote;

  const canSave =
    changed &&
    !pending &&
    (
      !noteRequired ||
      normalizedNote.length > 0
    );

  const matchingFields =
    Object.entries(
      finding.matching_response_fields,
    );

  return (
    <section className="finding-detail">
      <header className="finding-detail-header">
        <div>
          <span className="findings-section-label">
            Finding detail
          </span>

          <h3>
            {finding.title}
          </h3>

          <p>
            {finding.description}
          </p>
        </div>

        <div className="finding-detail-badges">
          <span
            className={severityClass(
              finding.severity,
            )}
          >
            {finding.severity}
          </span>

          <span
            className={statusClass(
              finding.status,
            )}
          >
            {statusLabel(
              finding.status,
            )}
          </span>
        </div>
      </header>

      <section className="finding-detail-metadata">
        <article>
          <span>
            Project
          </span>

          <strong>
            {project.name}
          </strong>
        </article>

        <article>
          <span>
            Category
          </span>

          <strong>
            {finding.category}
          </strong>
        </article>

        <article>
          <span>
            Confidence
          </span>

          <strong>
            {finding.confidence}
          </strong>
        </article>

        <article>
          <span>
            Occurrences
          </span>

          <strong>
            {finding.occurrence_count}
          </strong>
        </article>

        <article>
          <span>
            Reopened
          </span>

          <strong>
            {finding.reopened_count}
          </strong>
        </article>

        <article>
          <span>
            Last HTTP status
          </span>

          <strong>
            {
              finding
                .last_observed_status_code
            }
          </strong>
        </article>
      </section>

      <section className="finding-detail-section">
        <div className="finding-detail-section-heading">
          <span className="findings-section-label">
            Authorization context
          </span>

          <h4>
            Identity and object comparison
          </h4>
        </div>

        <dl className="finding-context-grid">
          <div>
            <dt>
              Identity
            </dt>

            <dd>
              {finding.identity_name}
            </dd>
          </div>

          <div>
            <dt>
              Identity ID
            </dt>

            <dd>
              <code>
                {finding.identity_id}
              </code>
            </dd>
          </div>

          <div>
            <dt>
              Operation
            </dt>

            <dd>
              <code>
                {finding.operation_key}
              </code>
            </dd>
          </div>

          <div>
            <dt>
              Resource
            </dt>

            <dd>
              {finding.resource_type}
            </dd>
          </div>

          <div>
            <dt>
              Owned baseline
            </dt>

            <dd>
              <code>
                {finding.baseline_object_id ??
                  "Unavailable"}
              </code>
            </dd>
          </div>

          <div>
            <dt>
              Cross-owner probe
            </dt>

            <dd>
              <code>
                {finding.probe_object_id}
              </code>
            </dd>
          </div>
        </dl>
      </section>

      <section className="finding-detail-section">
        <div className="finding-detail-section-heading">
          <span className="findings-section-label">
            Evidence matching
          </span>

          <h4>
            Configured response fields
          </h4>
        </div>

        {matchingFields.length > 0 ? (
          <div className="finding-field-grid">
            {matchingFields.map(
              ([
                fieldName,
                matches,
              ]) => (
                <article
                  className={
                    matches
                      ? "finding-field finding-field-match"
                      : "finding-field finding-field-mismatch"
                  }
                  key={fieldName}
                >
                  {matches ? (
                    <CheckCircle2
                      aria-hidden="true"
                      size={17}
                    />
                  ) : (
                    <AlertCircle
                      aria-hidden="true"
                      size={17}
                    />
                  )}

                  <code>
                    {fieldName}
                  </code>

                  <strong>
                    {matches
                      ? "Matched"
                      : "Not matched"}
                  </strong>
                </article>
              ),
            )}
          </div>
        ) : (
          <div className="finding-empty-detail">
            No configured response fields were
            available for comparison.
          </div>
        )}
      </section>

      <section className="finding-detail-section">
        <div className="finding-detail-section-heading">
          <span className="findings-section-label">
            Occurrence history
          </span>

          <h4>
            Observation timeline
          </h4>
        </div>

        <dl className="finding-context-grid">
          <div>
            <dt>
              First observed
            </dt>

            <dd>
              {formatDate(
                finding.first_seen_at,
              )}
            </dd>
          </div>

          <div>
            <dt>
              Last observed
            </dt>

            <dd>
              {formatDate(
                finding.last_seen_at,
              )}
            </dd>
          </div>

          <div>
            <dt>
              Last lifecycle update
            </dt>

            <dd>
              {formatDate(
                finding.updated_at,
              )}
            </dd>
          </div>

          <div>
            <dt>
              Scan records
            </dt>

            <dd>
              {finding.scan_ids.length}
            </dd>
          </div>
        </dl>

        {finding.scan_ids.length > 0 ? (
          <div className="finding-id-list">
            {finding.scan_ids.map(
              (scanId) => (
                <code key={scanId}>
                  {scanId}
                </code>
              ),
            )}
          </div>
        ) : null}
      </section>

      <section className="finding-detail-section finding-lifecycle-section">
        <div className="finding-detail-section-heading">
          <span className="findings-section-label">
            Lifecycle management
          </span>

          <h4>
            Change finding status
          </h4>

          <p>
            Non-open statuses require a note
            explaining the decision.
          </p>
        </div>

        <label className="finding-form-field">
          <span>
            Finding status
          </span>

          <select
            onChange={(event) => {
              setSelectedStatus(
                event.target
                  .value as FindingStatus,
              );
            }}
            value={selectedStatus}
          >
            <option value="open">
              Open
            </option>

            <option value="resolved">
              Resolved
            </option>

            <option value="false_positive">
              False positive
            </option>

            <option value="accepted_risk">
              Accepted risk
            </option>
          </select>
        </label>

        <label className="finding-form-field">
          <span>
            Decision or resolution note
          </span>

          <textarea
            maxLength={4000}
            onChange={(event) => {
              setNote(
                event.target.value,
              );
            }}
            placeholder={
              selectedStatus === "open"
                ? "A note is optional while the finding is open."
                : "Explain why this lifecycle status is appropriate."
            }
            rows={6}
            value={note}
          />

          <small>
            {noteRequired
              ? "A note is required for this status."
              : "Opening a finding clears any previous resolution note when saved without a note."}
          </small>
        </label>

        <footer className="finding-lifecycle-actions">
          <span>
            Fingerprint:
            {" "}
            <code>
              {finding.fingerprint}
            </code>
          </span>

          <button
            className="findings-button findings-button-primary"
            disabled={!canSave}
            onClick={() => {
              onSave({
                projectId:
                  finding.project_id,
                fingerprint:
                  finding.fingerprint,
                status:
                  selectedStatus,
                note:
                  selectedStatus === "open"
                    ? (
                        normalizedNote ||
                        null
                      )
                    : normalizedNote,
              });
            }}
            type="button"
          >
            {pending ? (
              <LoaderCircle
                aria-hidden="true"
                className="findings-spinner"
                size={17}
              />
            ) : (
              <Save
                aria-hidden="true"
                size={17}
              />
            )}

            Save lifecycle status
          </button>
        </footer>
      </section>
    </section>
  );
}

export function FindingsPage() {
  const queryClient =
    useQueryClient();

  const [
    projectFilter,
    setProjectFilter,
  ] = useState("all");

  const [
    statusFilter,
    setStatusFilter,
  ] = useState<
    "all" | FindingStatus
  >("all");

  const [
    severityFilter,
    setSeverityFilter,
  ] = useState<
    "all" | FindingSeverity
  >("all");

  const [
    categoryFilter,
    setCategoryFilter,
  ] = useState<
    "all" | FindingCategory
  >("all");

  const [
    searchText,
    setSearchText,
  ] = useState("");

  const [
    selectedFingerprint,
    setSelectedFingerprint,
  ] = useState("");

  const projectsQuery = useQuery({
    queryKey: [
      "projects",
    ],
    queryFn: listProjects,
  });

  const projects =
    projectsQuery.data ?? [];

  const findingQueries =
    useQueries({
      queries: projects.map(
        (project) => ({
          queryKey: [
            "projects",
            project.id,
            "findings",
          ],
          queryFn: () =>
            listProjectFindings(
              project.id,
            ),
        }),
      ),
    });

  const allFindings:
    FindingWithProject[] = [];

  projects.forEach(
    (
      project,
      projectIndex,
    ) => {
      const findingList =
        findingQueries[
          projectIndex
        ]?.data;

      for (
        const finding
        of findingList?.items ?? []
      ) {
        allFindings.push({
          project,
          finding,
        });
      }
    },
  );

  allFindings.sort(
    (
      first,
      second,
    ) =>
      new Date(
        second.finding.last_seen_at,
      ).getTime() -
      new Date(
        first.finding.last_seen_at,
      ).getTime(),
  );

  const normalizedSearch =
    searchText
      .trim()
      .toLowerCase();

  const filteredFindings =
    allFindings.filter(
      ({
        finding,
        project,
      }) => {
        if (
          projectFilter !== "all" &&
          project.id !== projectFilter
        ) {
          return false;
        }

        if (
          statusFilter !== "all" &&
          finding.status !== statusFilter
        ) {
          return false;
        }

        if (
          severityFilter !== "all" &&
          finding.severity !==
            severityFilter
        ) {
          return false;
        }

        if (
          categoryFilter !== "all" &&
          finding.category !==
            categoryFilter
        ) {
          return false;
        }

        if (!normalizedSearch) {
          return true;
        }

        const searchableContent = [
          finding.title,
          finding.description,
          finding.operation_key,
          finding.identity_name,
          finding.resource_type,
          finding.probe_object_id,
          finding.baseline_object_id ??
            "",
          finding.fingerprint,
          project.name,
        ]
          .join(" ")
          .toLowerCase();

        return searchableContent.includes(
          normalizedSearch,
        );
      },
    );

  const selectedItem =
    filteredFindings.find(
      ({ finding }) =>
        finding.fingerprint ===
        selectedFingerprint,
    ) ??
    filteredFindings[0] ??
    null;

  const updateMutation =
    useMutation({
      mutationFn:
        updateProjectFinding,

      onSuccess: async (
        updatedFinding,
      ) => {
        setSelectedFingerprint(
          updatedFinding.fingerprint,
        );

        await queryClient.invalidateQueries({
          queryKey: [
            "projects",
            updatedFinding.project_id,
            "findings",
          ],
        });
      },
    });

  const rebuildMutation =
    useMutation({
      mutationFn: async () => {
        const results = [];

        for (
          const project
          of projects
        ) {
          results.push(
            await rebuildProjectFindings(
              project.id,
            ),
          );
        }

        return results;
      },

      onSuccess: async () => {
        await queryClient.invalidateQueries({
          queryKey: [
            "projects",
          ],
        });
      },
    });

  const findingQueryError =
    findingQueries.find(
      (query) =>
        query.error !== null,
    )?.error;

  const combinedError =
    projectsQuery.error ??
    findingQueryError ??
    updateMutation.error ??
    rebuildMutation.error;

  const loading =
    projectsQuery.isPending ||
    findingQueries.some(
      (query) =>
        query.isPending,
    );

  const fetching =
    projectsQuery.isFetching ||
    findingQueries.some(
      (query) =>
        query.isFetching,
    );

  const openCount =
    allFindings.filter(
      ({ finding }) =>
        finding.status === "open",
    ).length;

  const resolvedCount =
    allFindings.filter(
      ({ finding }) =>
        finding.status ===
        "resolved",
    ).length;

  const falsePositiveCount =
    allFindings.filter(
      ({ finding }) =>
        finding.status ===
        "false_positive",
    ).length;

  const acceptedRiskCount =
    allFindings.filter(
      ({ finding }) =>
        finding.status ===
        "accepted_risk",
    ).length;

  function resetFilters(): void {
    setProjectFilter("all");
    setStatusFilter("all");
    setSeverityFilter("all");
    setCategoryFilter("all");
    setSearchText("");
  }

  function refreshAll(): void {
    void projectsQuery.refetch();

    for (
      const findingQuery
      of findingQueries
    ) {
      void findingQuery.refetch();
    }
  }

  return (
    <div className="page findings-page">
      <section className="findings-header">
        <div>
          <span className="findings-section-label">
            Authorization observations
          </span>

          <h2>
            Findings
          </h2>

          <p>
            Review deduplicated authorization
            findings across all configured API
            projects and manage their lifecycle.
          </p>
        </div>

        <div className="findings-header-actions">
          <button
            className="findings-button findings-button-secondary"
            disabled={fetching}
            onClick={refreshAll}
            type="button"
          >
            <RefreshCw
              aria-hidden="true"
              className={
                fetching
                  ? "findings-spinner"
                  : undefined
              }
              size={17}
            />

            Refresh
          </button>

          <button
            className="findings-button findings-button-index"
            disabled={
              rebuildMutation.isPending ||
              projects.length === 0
            }
            onClick={() => {
              rebuildMutation.mutate();
            }}
            type="button"
          >
            {rebuildMutation.isPending ? (
              <LoaderCircle
                aria-hidden="true"
                className="findings-spinner"
                size={17}
              />
            ) : (
              <RotateCcw
                aria-hidden="true"
                size={17}
              />
            )}

            Rebuild finding index
          </button>
        </div>
      </section>

      {combinedError ? (
        <section
          className="findings-alert"
          role="alert"
        >
          <AlertCircle
            aria-hidden="true"
            size={21}
          />

          <div>
            <strong>
              Findings could not be loaded.
            </strong>

            <span>
              {getErrorMessage(
                combinedError,
              )}
            </span>
          </div>
        </section>
      ) : null}

      <section className="findings-stat-grid">
        <article>
          <Hash
            aria-hidden="true"
            size={20}
          />

          <div>
            <span>
              Total
            </span>

            <strong>
              {allFindings.length}
            </strong>
          </div>
        </article>

        <article className="findings-stat-open">
          <ShieldAlert
            aria-hidden="true"
            size={20}
          />

          <div>
            <span>
              Open
            </span>

            <strong>
              {openCount}
            </strong>
          </div>
        </article>

        <article className="findings-stat-resolved">
          <CheckCircle2
            aria-hidden="true"
            size={20}
          />

          <div>
            <span>
              Resolved
            </span>

            <strong>
              {resolvedCount}
            </strong>
          </div>
        </article>

        <article className="findings-stat-false-positive">
          <Ban
            aria-hidden="true"
            size={20}
          />

          <div>
            <span>
              False positive
            </span>

            <strong>
              {falsePositiveCount}
            </strong>
          </div>
        </article>

        <article className="findings-stat-accepted">
          <FileWarning
            aria-hidden="true"
            size={20}
          />

          <div>
            <span>
              Accepted risk
            </span>

            <strong>
              {acceptedRiskCount}
            </strong>
          </div>
        </article>
      </section>

      <section className="findings-filter-panel">
        <header>
          <div>
            <Filter
              aria-hidden="true"
              size={19}
            />

            <div>
              <strong>
                Finding filters
              </strong>

              <span>
                Showing{" "}
                {filteredFindings.length}
                {" of "}
                {allFindings.length}
              </span>
            </div>
          </div>

          <button
            className="findings-reset-button"
            onClick={resetFilters}
            type="button"
          >
            <RotateCcw
              aria-hidden="true"
              size={15}
            />

            Reset
          </button>
        </header>

        <div className="findings-filter-grid">
          <label className="findings-search-field">
            <span>
              Search
            </span>

            <div>
              <Search
                aria-hidden="true"
                size={17}
              />

              <input
                onChange={(event) => {
                  setSearchText(
                    event.target.value,
                  );
                }}
                placeholder="Title, operation, identity, object or project"
                type="search"
                value={searchText}
              />
            </div>
          </label>

          <label className="findings-filter-field">
            <span>
              Project
            </span>

            <select
              onChange={(event) => {
                setProjectFilter(
                  event.target.value,
                );
              }}
              value={projectFilter}
            >
              <option value="all">
                All projects
              </option>

              {projects.map(
                (project) => (
                  <option
                    key={project.id}
                    value={project.id}
                  >
                    {project.name}
                  </option>
                ),
              )}
            </select>
          </label>

          <label className="findings-filter-field">
            <span>
              Status
            </span>

            <select
              onChange={(event) => {
                setStatusFilter(
                  event.target.value as
                    | "all"
                    | FindingStatus,
                );
              }}
              value={statusFilter}
            >
              <option value="all">
                All statuses
              </option>

              <option value="open">
                Open
              </option>

              <option value="resolved">
                Resolved
              </option>

              <option value="false_positive">
                False positive
              </option>

              <option value="accepted_risk">
                Accepted risk
              </option>
            </select>
          </label>

          <label className="findings-filter-field">
            <span>
              Severity
            </span>

            <select
              onChange={(event) => {
                setSeverityFilter(
                  event.target.value as
                    | "all"
                    | FindingSeverity,
                );
              }}
              value={severityFilter}
            >
              <option value="all">
                All severities
              </option>

              <option value="critical">
                Critical
              </option>

              <option value="high">
                High
              </option>

              <option value="medium">
                Medium
              </option>

              <option value="low">
                Low
              </option>

              <option value="info">
                Informational
              </option>
            </select>
          </label>

          <label className="findings-filter-field">
            <span>
              Category
            </span>

            <select
              onChange={(event) => {
                setCategoryFilter(
                  event.target.value as
                    | "all"
                    | FindingCategory,
                );
              }}
              value={categoryFilter}
            >
              <option value="all">
                All categories
              </option>

              <option value="BOLA">
                BOLA
              </option>

              <option value="BFLA">
                BFLA
              </option>

              <option value="BOPLA">
                BOPLA
              </option>
            </select>
          </label>
        </div>
      </section>

      {loading ? (
        <section className="findings-loading">
          <LoaderCircle
            aria-hidden="true"
            className="findings-spinner"
            size={30}
          />

          <strong>
            Loading central findings
          </strong>
        </section>
      ) : filteredFindings.length ===
        0 ? (
        <section className="findings-empty">
          <FolderKanban
            aria-hidden="true"
            size={31}
          />

          <h3>
            No findings match the current view
          </h3>

          <p>
            Rebuild the finding index or change
            the active filters.
          </p>
        </section>
      ) : (
        <section className="findings-workspace">
          <aside className="findings-list">
            {filteredFindings.map(
              ({
                finding,
                project,
              }) => {
                const active =
                  selectedItem?.finding
                    .fingerprint ===
                  finding.fingerprint;

                return (
                  <button
                    className={
                      active
                        ? "finding-list-card finding-list-card-active"
                        : "finding-list-card"
                    }
                    key={
                      finding.fingerprint
                    }
                    onClick={() => {
                      setSelectedFingerprint(
                        finding.fingerprint,
                      );
                    }}
                    type="button"
                  >
                    <header>
                      <span
                        className={severityClass(
                          finding.severity,
                        )}
                      >
                        {finding.severity}
                      </span>

                      <span
                        className={statusClass(
                          finding.status,
                        )}
                      >
                        {statusLabel(
                          finding.status,
                        )}
                      </span>
                    </header>

                    <h3>
                      {finding.title}
                    </h3>

                    <p>
                      {project.name}
                    </p>

                    <code>
                      {finding.operation_key}
                    </code>

                    <footer>
                      <span>
                        {finding.identity_name}
                      </span>

                      <span>
                        {
                          finding
                            .occurrence_count
                        }
                        {" occurrence(s)"}
                      </span>
                    </footer>
                  </button>
                );
              },
            )}
          </aside>

          {selectedItem ? (
            <FindingDetail
              item={selectedItem}
              key={
                `${selectedItem.finding.fingerprint}:` +
                selectedItem.finding.updated_at
              }
              onSave={(input) => {
                updateMutation.mutate(
                  input,
                );
              }}
              pending={
                updateMutation.isPending
              }
            />
          ) : null}
        </section>
      )}
    </div>
  );
}