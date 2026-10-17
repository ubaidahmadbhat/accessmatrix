import {
  useMutation,
  useQueries,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  Activity,
  AlertCircle,
  ArrowLeftRight,
  CheckCircle2,
  Clock,
  FileWarning,
  Filter,
  FolderKanban,
  LoaderCircle,
  RefreshCw,
  Search,
  ShieldAlert,
  ShieldCheck,
  ShieldX,
  Trash2,
} from "lucide-react";
import {
  useEffect,
  useState,
} from "react";

import type {
  BOLACaseResult,
  BOLAScan,
  BOLAScanSummary,
  ResponseEvidence,
  ScanStatus,
} from "../api/scans";
import {
  deleteBOLAScan,
  getBOLAScan,
  listBOLAScans,
  pruneBOLAScans,
} from "../api/scans";
import type {
  Project,
} from "../api/projects";
import {
  ApiRequestError,
  listProjects,
} from "../api/projects";

import "./ScansPage.css";

interface ScanWithProject {
  key: string;
  project: Project;
  scan: BOLAScanSummary;
}

interface EvidenceCardProps {
  label: string;
  evidence: ResponseEvidence | null;
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

function scanKey(
  projectId: string,
  scanId: string,
): string {
  return (
    `${projectId}:` +
    scanId
  );
}

function statusClass(
  status: ScanStatus,
): string {
  return (
    "scans-status " +
    `scans-status-${status}`
  );
}

function outcomeClass(
  outcome: BOLACaseResult["outcome"],
): string {
  return (
    "scans-outcome " +
    `scans-outcome-${outcome}`
  );
}

function signedDelta(
  current: number,
  previous: number,
): string {
  const difference =
    current - previous;

  if (difference > 0) {
    return `+${difference}`;
  }

  return String(
    difference
  );
}

function EvidenceCard({
  label,
  evidence,
}: EvidenceCardProps) {
  if (!evidence) {
    return (
      <article className="scan-evidence-card scan-evidence-empty">
        <span>
          {label}
        </span>

        <strong>
          Not executed
        </strong>
      </article>
    );
  }

  return (
    <article className="scan-evidence-card">
      <header>
        <div>
          <span>
            {label}
          </span>

          <strong>
            HTTP {evidence.status_code}
            {" "}
            {evidence.reason_phrase}
          </strong>
        </div>

        <small>
          {evidence.elapsed_ms.toFixed(
            2,
          )}
          {" ms"}
        </small>
      </header>

      <dl>
        <div>
          <dt>
            Request URL
          </dt>

          <dd>
            <code>
              {evidence.request_url}
            </code>
          </dd>
        </div>

        <div>
          <dt>
            Captured bytes
          </dt>

          <dd>
            {
              evidence
                .body_bytes_captured
            }
          </dd>
        </div>

        <div>
          <dt>
            Truncated
          </dt>

          <dd>
            {evidence.body_truncated
              ? "Yes"
              : "No"}
          </dd>
        </div>

        <div>
          <dt>
            Redirect blocked
          </dt>

          <dd>
            {evidence.redirect_blocked
              ? "Yes"
              : "No"}
          </dd>
        </div>

        <div>
          <dt>
            Body SHA-256
          </dt>

          <dd>
            <code>
              {evidence.body_sha256 ??
                "Unavailable"}
            </code>
          </dd>
        </div>
      </dl>

      {evidence.body_excerpt ? (
        <details className="scan-evidence-body">
          <summary>
            Redacted response excerpt
          </summary>

          <pre>
            {evidence.body_excerpt}
          </pre>
        </details>
      ) : null}
    </article>
  );
}

function ScanCaseCard({
  result,
}: {
  result: BOLACaseResult;
}) {
  return (
    <article className="scan-case-card">
      <header>
        <div>
          <span>
            {result.resource_type}
          </span>

          <h5>
            {result.case_name}
          </h5>
        </div>

        <span
          className={outcomeClass(
            result.outcome,
          )}
        >
          {result.outcome}
        </span>
      </header>

      <p>
        {result.explanation}
      </p>

      <dl className="scan-case-context">
        <div>
          <dt>
            Identity
          </dt>

          <dd>
            {result.identity_name}
          </dd>
        </div>

        <div>
          <dt>
            Operation
          </dt>

          <dd>
            <code>
              {result.operation_key}
            </code>
          </dd>
        </div>

        <div>
          <dt>
            Baseline object
          </dt>

          <dd>
            <code>
              {result.baseline_object_id ??
                "Unavailable"}
            </code>
          </dd>
        </div>

        <div>
          <dt>
            Probe object
          </dt>

          <dd>
            <code>
              {result.probe_object_id}
            </code>
          </dd>
        </div>

        <div>
          <dt>
            Expected denial
          </dt>

          <dd>
            {result
              .expected_probe_status_codes
              .join(", ")}
          </dd>
        </div>
      </dl>

      {result.issues.length > 0 ? (
        <ul className="scan-case-issues">
          {result.issues.map(
            (issue) => (
              <li key={issue}>
                {issue}
              </li>
            ),
          )}
        </ul>
      ) : null}

      <div className="scan-evidence-grid">
        <EvidenceCard
          evidence={
            result.baseline_evidence
          }
          label="Owned-object baseline"
        />

        <EvidenceCard
          evidence={
            result.probe_evidence
          }
          label="Cross-owner probe"
        />
      </div>
    </article>
  );
}

function ScanComparison({
  current,
  comparison,
}: {
  current: BOLAScan;
  comparison: BOLAScan;
}) {
  return (
    <section className="scan-comparison">
      <header>
        <ArrowLeftRight
          aria-hidden="true"
          size={20}
        />

        <div>
          <span className="scans-section-label">
            Scan comparison
          </span>

          <h4>
            Current versus comparison scan
          </h4>
        </div>
      </header>

      <div className="scan-comparison-grid">
        <article>
          <span>
            Total cases
          </span>

          <strong>
            {current.total_count}
          </strong>

          <small>
            {signedDelta(
              current.total_count,
              comparison.total_count,
            )}
          </small>
        </article>

        <article className="scan-comparison-pass">
          <span>
            Passed
          </span>

          <strong>
            {current.pass_count}
          </strong>

          <small>
            {signedDelta(
              current.pass_count,
              comparison.pass_count,
            )}
          </small>
        </article>

        <article className="scan-comparison-finding">
          <span>
            Findings
          </span>

          <strong>
            {current.finding_count}
          </strong>

          <small>
            {signedDelta(
              current.finding_count,
              comparison.finding_count,
            )}
          </small>
        </article>

        <article className="scan-comparison-inconclusive">
          <span>
            Inconclusive
          </span>

          <strong>
            {current.inconclusive_count}
          </strong>

          <small>
            {signedDelta(
              current.inconclusive_count,
              comparison.inconclusive_count,
            )}
          </small>
        </article>

        <article>
          <span>
            Blocked
          </span>

          <strong>
            {current.blocked_count}
          </strong>

          <small>
            {signedDelta(
              current.blocked_count,
              comparison.blocked_count,
            )}
          </small>
        </article>
      </div>

      <p>
        Delta values compare the selected scan
        against the chosen historical scan.
        Positive finding deltas represent a worse
        authorization result.
      </p>
    </section>
  );
}

function ScanDetails({
  project,
  scan,
}: {
  project: Project;
  scan: BOLAScan;
}) {
  return (
    <section className="scan-details">
      <header className="scan-details-header">
        <div>
          <span className="scans-section-label">
            Persisted scan evidence
          </span>

          <h3>
            {project.name}
          </h3>

          <p>
            Completed{" "}
            {formatDate(
              scan.completed_at,
            )}
          </p>
        </div>

        <span
          className={statusClass(
            scan.status,
          )}
        >
          {scan.status}
        </span>
      </header>

      <section className="scan-detail-stat-grid">
        <article>
          <Activity
            aria-hidden="true"
            size={19}
          />

          <div>
            <span>
              Total
            </span>

            <strong>
              {scan.total_count}
            </strong>
          </div>
        </article>

        <article className="scan-detail-pass">
          <ShieldCheck
            aria-hidden="true"
            size={19}
          />

          <div>
            <span>
              Passed
            </span>

            <strong>
              {scan.pass_count}
            </strong>
          </div>
        </article>

        <article className="scan-detail-finding">
          <ShieldX
            aria-hidden="true"
            size={19}
          />

          <div>
            <span>
              Findings
            </span>

            <strong>
              {scan.finding_count}
            </strong>
          </div>
        </article>

        <article className="scan-detail-inconclusive">
          <ShieldAlert
            aria-hidden="true"
            size={19}
          />

          <div>
            <span>
              Inconclusive
            </span>

            <strong>
              {scan.inconclusive_count}
            </strong>
          </div>
        </article>

        <article>
          <AlertCircle
            aria-hidden="true"
            size={19}
          />

          <div>
            <span>
              Blocked
            </span>

            <strong>
              {scan.blocked_count}
            </strong>
          </div>
        </article>
      </section>

      {scan.findings.length > 0 ? (
        <section className="scan-finding-summary">
          <div>
            <FileWarning
              aria-hidden="true"
              size={21}
            />

            <div>
              <strong>
                {scan.findings.length}
                {" BOLA finding(s)"}
              </strong>

              <span>
                These observations are also
                indexed in the central Findings
                interface.
              </span>
            </div>
          </div>

          <div className="scan-finding-list">
            {scan.findings.map(
              (finding) => (
                <article
                  key={
                    finding.finding_id
                  }
                >
                  <header>
                    <strong>
                      {finding.title}
                    </strong>

                    <span>
                      {finding.severity}
                    </span>
                  </header>

                  <p>
                    {finding.description}
                  </p>

                  <code>
                    {finding.operation_key}
                  </code>
                </article>
              ),
            )}
          </div>
        </section>
      ) : (
        <section className="scan-no-findings">
          <CheckCircle2
            aria-hidden="true"
            size={27}
          />

          <div>
            <strong>
              No BOLA findings
            </strong>

            <span>
              Classified cross-owner probes were
              rejected as expected.
            </span>
          </div>
        </section>
      )}

      <section className="scan-case-section">
        <header>
          <span className="scans-section-label">
            Request evidence
          </span>

          <h4>
            Baseline and probe cases
          </h4>
        </header>

        <div className="scan-case-grid">
          {scan.results.map(
            (result) => (
              <ScanCaseCard
                key={result.case_id}
                result={result}
              />
            ),
          )}
        </div>
      </section>
    </section>
  );
}

export function ScansPage() {
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
    "all" | ScanStatus
  >("all");

  const [
    searchText,
    setSearchText,
  ] = useState("");

  const [
    selectedKey,
    setSelectedKey,
  ] = useState("");

  const [
    comparisonKey,
    setComparisonKey,
  ] = useState("");

  const [
    deleteAcknowledged,
    setDeleteAcknowledged,
  ] = useState(false);

  const [
    deleteConfirmation,
    setDeleteConfirmation,
  ] = useState("");

  const [
    retentionProjectId,
    setRetentionProjectId,
  ] = useState("");

  const [
    keepLatestText,
    setKeepLatestText,
  ] = useState("10");

  const [
    retentionAcknowledged,
    setRetentionAcknowledged,
  ] = useState(false);

  const [
    retentionConfirmation,
    setRetentionConfirmation,
  ] = useState("");

  const projectsQuery = useQuery({
    queryKey: [
      "projects",
    ],
    queryFn: listProjects,
  });

  const projects =
    projectsQuery.data ?? [];

  useEffect(() => {
    const firstProject =
      projectsQuery.data?.[0];

    if (
      !retentionProjectId &&
      firstProject
    ) {
      setRetentionProjectId(
        firstProject.id,
      );
    }
  }, [
    projectsQuery.data,
    retentionProjectId,
  ]);

  const scanListQueries =
    useQueries({
      queries: projects.map(
        (project) => ({
          queryKey: [
            "projects",
            project.id,
            "bola-scans",
          ],
          queryFn: () =>
            listBOLAScans(
              project.id,
            ),
        }),
      ),
    });

  const allScans:
    ScanWithProject[] = [];

  projects.forEach(
    (
      project,
      projectIndex,
    ) => {
      const scanList =
        scanListQueries[
          projectIndex
        ]?.data;

      for (
        const scan
        of scanList?.items ?? []
      ) {
        allScans.push({
          key: scanKey(
            project.id,
            scan.scan_id,
          ),
          project,
          scan,
        });
      }
    },
  );

  allScans.sort(
    (
      first,
      second,
    ) =>
      new Date(
        second.scan.completed_at,
      ).getTime() -
      new Date(
        first.scan.completed_at,
      ).getTime(),
  );

  const normalizedSearch =
    searchText
      .trim()
      .toLowerCase();

  const filteredScans =
    allScans.filter(
      ({
        project,
        scan,
      }) => {
        if (
          projectFilter !== "all" &&
          project.id !== projectFilter
        ) {
          return false;
        }

        if (
          statusFilter !== "all" &&
          scan.status !== statusFilter
        ) {
          return false;
        }

        if (!normalizedSearch) {
          return true;
        }

        return [
          project.name,
          project.description ?? "",
          scan.scan_id,
          scan.status,
          String(
            scan.finding_count,
          ),
        ]
          .join(" ")
          .toLowerCase()
          .includes(
            normalizedSearch,
          );
      },
    );

  const selectedItem =
    filteredScans.find(
      (item) =>
        item.key === selectedKey,
    ) ??
    filteredScans[0] ??
    null;

  const comparisonItem =
    allScans.find(
      (item) =>
        item.key === comparisonKey &&
        item.key !==
          selectedItem?.key,
    ) ??
    null;

  const selectedScanQuery = useQuery({
    queryKey: [
      "projects",
      selectedItem?.project.id,
      "bola-scans",
      selectedItem?.scan.scan_id,
    ],
    queryFn: () => {
      if (!selectedItem) {
        throw new Error(
          "No scan is selected.",
        );
      }

      return getBOLAScan(
        selectedItem.project.id,
        selectedItem.scan.scan_id,
      );
    },
    enabled: Boolean(
      selectedItem,
    ),
  });

  const comparisonScanQuery = useQuery({
    queryKey: [
      "projects",
      comparisonItem?.project.id,
      "bola-scans",
      comparisonItem?.scan.scan_id,
    ],
    queryFn: () => {
      if (!comparisonItem) {
        throw new Error(
          "No comparison scan is selected.",
        );
      }

      return getBOLAScan(
        comparisonItem.project.id,
        comparisonItem.scan.scan_id,
      );
    },
    enabled: Boolean(
      comparisonItem,
    ),
  });

  const deleteMutation =
    useMutation({
      mutationFn: async () => {
        if (!selectedItem) {
          throw new Error(
            "No scan is selected."
          );
        }

        return deleteBOLAScan(
          selectedItem.project.id,
          selectedItem.scan.scan_id,
          {
            acknowledge_evidence_loss:
              deleteAcknowledged,
            confirmation:
              deleteConfirmation.trim(),
          },
        );
      },

      onSuccess: async (
        result,
      ) => {
        setSelectedKey("");
        setComparisonKey("");
        setDeleteAcknowledged(false);
        setDeleteConfirmation("");

        queryClient.removeQueries({
          queryKey: [
            "projects",
            result.project_id,
            "bola-scans",
            result.scan_id,
          ],
        });

        await queryClient.invalidateQueries({
          queryKey: [
            "projects",
            result.project_id,
            "bola-scans",
          ],
        });
      },
    });

  const retentionMutation =
    useMutation({
      mutationFn: async () => {
        const keepLatest =
          Number.parseInt(
            keepLatestText,
            10,
          );

        if (
          !Number.isInteger(
            keepLatest,
          ) ||
          keepLatest < 1
        ) {
          throw new Error(
            "Retention must keep at least one scan."
          );
        }

        if (!retentionProjectId) {
          throw new Error(
            "Select a project for retention."
          );
        }

        return pruneBOLAScans(
          retentionProjectId,
          {
            acknowledge_evidence_loss:
              retentionAcknowledged,
            confirmation:
              retentionConfirmation
                .trim(),
            keep_latest:
              keepLatest,
          },
        );
      },

      onSuccess: async (
        result,
      ) => {
        setSelectedKey("");
        setComparisonKey("");
        setRetentionAcknowledged(false);
        setRetentionConfirmation("");

        await queryClient.invalidateQueries({
          queryKey: [
            "projects",
            result.project_id,
            "bola-scans",
          ],
        });
      },
    });

  const scanListError =
    scanListQueries.find(
      (query) =>
        query.error !== null,
    )?.error;

  const combinedError =
    projectsQuery.error ??
    scanListError ??
    selectedScanQuery.error ??
    comparisonScanQuery.error ??
    deleteMutation.error ??
    retentionMutation.error;

  const loading =
    projectsQuery.isPending ||
    scanListQueries.some(
      (query) =>
        query.isPending,
    );

  const fetching =
    projectsQuery.isFetching ||
    scanListQueries.some(
      (query) =>
        query.isFetching,
    ) ||
    selectedScanQuery.isFetching ||
    comparisonScanQuery.isFetching;

  const completedCount =
    allScans.filter(
      ({ scan }) =>
        scan.status === "completed",
    ).length;

  const partialCount =
    allScans.filter(
      ({ scan }) =>
        scan.status === "partial",
    ).length;

  const failedCount =
    allScans.filter(
      ({ scan }) =>
        scan.status === "failed",
    ).length;

  const totalFindingCount =
    allScans.reduce(
      (
        count,
        {
          scan,
        },
      ) =>
        count +
        scan.finding_count,
      0,
    );

  const requiredDeletePhrase =
    selectedItem
      ? (
          "DELETE BOLA SCAN " +
          selectedItem.scan.scan_id
        )
      : "";

  const requiredRetentionPhrase =
    retentionProjectId
      ? (
          "PRUNE BOLA SCANS " +
          retentionProjectId
        )
      : "";

  const canDelete =
    Boolean(
      selectedItem,
    ) &&
    deleteAcknowledged &&
    deleteConfirmation.trim() ===
      requiredDeletePhrase &&
    !deleteMutation.isPending;

  const keepLatest =
    Number.parseInt(
      keepLatestText,
      10,
    );

  const canApplyRetention =
    Boolean(
      retentionProjectId,
    ) &&
    Number.isInteger(
      keepLatest,
    ) &&
    keepLatest >= 1 &&
    retentionAcknowledged &&
    retentionConfirmation.trim() ===
      requiredRetentionPhrase &&
    !retentionMutation.isPending;

  function refreshAll(): void {
    void projectsQuery.refetch();

    for (
      const scanQuery
      of scanListQueries
    ) {
      void scanQuery.refetch();
    }

    if (selectedItem) {
      void selectedScanQuery.refetch();
    }

    if (comparisonItem) {
      void comparisonScanQuery.refetch();
    }
  }

  function resetFilters(): void {
    setProjectFilter("all");
    setStatusFilter("all");
    setSearchText("");
  }

  return (
    <div className="page scans-page">
      <section className="scans-header">
        <div>
          <span className="scans-section-label">
            Authorization execution history
          </span>

          <h2>
            Scans
          </h2>

          <p>
            Review persisted BOLA scans across
            every project, compare results, inspect
            redacted evidence, and manage local
            evidence retention.
          </p>
        </div>

        <button
          className="scans-button scans-button-secondary"
          disabled={fetching}
          onClick={refreshAll}
          type="button"
        >
          <RefreshCw
            aria-hidden="true"
            className={
              fetching
                ? "scans-spinner"
                : undefined
            }
            size={17}
          />

          Refresh
        </button>
      </section>

      {combinedError ? (
        <section
          className="scans-alert"
          role="alert"
        >
          <AlertCircle
            aria-hidden="true"
            size={21}
          />

          <div>
            <strong>
              Scan information could not be loaded.
            </strong>

            <span>
              {getErrorMessage(
                combinedError,
              )}
            </span>
          </div>
        </section>
      ) : null}

      <section className="scans-stat-grid">
        <article>
          <Activity
            aria-hidden="true"
            size={20}
          />

          <div>
            <span>
              Total scans
            </span>

            <strong>
              {allScans.length}
            </strong>
          </div>
        </article>

        <article className="scans-stat-completed">
          <CheckCircle2
            aria-hidden="true"
            size={20}
          />

          <div>
            <span>
              Completed
            </span>

            <strong>
              {completedCount}
            </strong>
          </div>
        </article>

        <article className="scans-stat-partial">
          <ShieldAlert
            aria-hidden="true"
            size={20}
          />

          <div>
            <span>
              Partial
            </span>

            <strong>
              {partialCount}
            </strong>
          </div>
        </article>

        <article className="scans-stat-failed">
          <ShieldX
            aria-hidden="true"
            size={20}
          />

          <div>
            <span>
              Failed
            </span>

            <strong>
              {failedCount}
            </strong>
          </div>
        </article>

        <article className="scans-stat-findings">
          <FileWarning
            aria-hidden="true"
            size={20}
          />

          <div>
            <span>
              Finding occurrences
            </span>

            <strong>
              {totalFindingCount}
            </strong>
          </div>
        </article>
      </section>

      <section className="scans-filter-panel">
        <header>
          <div>
            <Filter
              aria-hidden="true"
              size={19}
            />

            <div>
              <strong>
                Scan filters
              </strong>

              <span>
                Showing{" "}
                {filteredScans.length}
                {" of "}
                {allScans.length}
              </span>
            </div>
          </div>

          <button
            className="scans-reset-button"
            onClick={resetFilters}
            type="button"
          >
            Reset
          </button>
        </header>

        <div className="scans-filter-grid">
          <label className="scans-search-field">
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
                placeholder="Project, scan identifier or status"
                type="search"
                value={searchText}
              />
            </div>
          </label>

          <label className="scans-filter-field">
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

          <label className="scans-filter-field">
            <span>
              Status
            </span>

            <select
              onChange={(event) => {
                setStatusFilter(
                  event.target.value as
                    | "all"
                    | ScanStatus,
                );
              }}
              value={statusFilter}
            >
              <option value="all">
                All statuses
              </option>

              <option value="completed">
                Completed
              </option>

              <option value="partial">
                Partial
              </option>

              <option value="failed">
                Failed
              </option>
            </select>
          </label>

          <label className="scans-filter-field">
            <span>
              Compare selected scan
            </span>

            <select
              onChange={(event) => {
                setComparisonKey(
                  event.target.value,
                );
              }}
              value={comparisonKey}
            >
              <option value="">
                No comparison
              </option>

              {allScans
                .filter(
                  (item) =>
                    item.key !==
                    selectedItem?.key,
                )
                .map(
                  (item) => (
                    <option
                      key={item.key}
                      value={item.key}
                    >
                      {item.project.name}
                      {" — "}
                      {formatDate(
                        item.scan
                          .completed_at,
                      )}
                    </option>
                  ),
                )}
            </select>
          </label>
        </div>
      </section>

      {loading ? (
        <section className="scans-loading">
          <LoaderCircle
            aria-hidden="true"
            className="scans-spinner"
            size={30}
          />

          <strong>
            Loading scan history
          </strong>
        </section>
      ) : filteredScans.length ===
        0 ? (
        <section className="scans-empty">
          <FolderKanban
            aria-hidden="true"
            size={31}
          />

          <h3>
            No scans match the current view
          </h3>

          <p>
            Run a BOLA scan or change the active
            filters.
          </p>
        </section>
      ) : (
        <section className="scans-workspace">
          <aside className="scans-list">
            {filteredScans.map(
              (item) => {
                const active =
                  selectedItem?.key ===
                  item.key;

                return (
                  <button
                    className={
                      active
                        ? "scan-list-card scan-list-card-active"
                        : "scan-list-card"
                    }
                    key={item.key}
                    onClick={() => {
                      setSelectedKey(
                        item.key,
                      );

                      setDeleteAcknowledged(
                        false,
                      );

                      setDeleteConfirmation(
                        "",
                      );
                    }}
                    type="button"
                  >
                    <header>
                      <span
                        className={statusClass(
                          item.scan.status,
                        )}
                      >
                        {item.scan.status}
                      </span>

                      <span>
                        {formatDate(
                          item.scan
                            .completed_at,
                        )}
                      </span>
                    </header>

                    <h3>
                      {item.project.name}
                    </h3>

                    <code>
                      {item.scan.scan_id}
                    </code>

                    <footer>
                      <span>
                        {
                          item.scan
                            .total_count
                        }
                        {" case(s)"}
                      </span>

                      <span>
                        {
                          item.scan
                            .finding_count
                        }
                        {" finding(s)"}
                      </span>
                    </footer>
                  </button>
                );
              },
            )}
          </aside>

          <div className="scans-detail-column">
            {selectedScanQuery.isPending ? (
              <section className="scans-loading scans-detail-loading">
                <LoaderCircle
                  aria-hidden="true"
                  className="scans-spinner"
                  size={28}
                />

                <strong>
                  Loading scan evidence
                </strong>
              </section>
            ) : null}

            {selectedItem &&
            selectedScanQuery.data ? (
              <ScanDetails
                project={
                  selectedItem.project
                }
                scan={
                  selectedScanQuery.data
                }
              />
            ) : null}

            {selectedScanQuery.data &&
            comparisonScanQuery.data ? (
              <ScanComparison
                comparison={
                  comparisonScanQuery.data
                }
                current={
                  selectedScanQuery.data
                }
              />
            ) : null}

            {selectedItem ? (
              <section className="scan-delete-section">
                <header>
                  <Trash2
                    aria-hidden="true"
                    size={21}
                  />

                  <div>
                    <span className="scans-section-label">
                      Destructive evidence action
                    </span>

                    <h4>
                      Delete selected scan evidence
                    </h4>

                    <p>
                      The raw scan and response evidence
                      will be deleted. Deduplicated
                      finding history remains available.
                    </p>
                  </div>
                </header>

                <label className="scan-danger-check">
                  <input
                    checked={
                      deleteAcknowledged
                    }
                    onChange={(event) => {
                      setDeleteAcknowledged(
                        event.target.checked,
                      );
                    }}
                    type="checkbox"
                  />

                  <span>
                    I understand that this scan
                    evidence cannot be recovered.
                  </span>
                </label>

                <label className="scan-danger-field">
                  <span>
                    Exact confirmation phrase
                  </span>

                  <code>
                    {requiredDeletePhrase}
                  </code>

                  <input
                    autoComplete="off"
                    onChange={(event) => {
                      setDeleteConfirmation(
                        event.target.value,
                      );
                    }}
                    type="text"
                    value={
                      deleteConfirmation
                    }
                  />
                </label>

                <button
                  className="scans-button scans-button-danger"
                  disabled={!canDelete}
                  onClick={() => {
                    deleteMutation.mutate();
                  }}
                  type="button"
                >
                  {deleteMutation.isPending ? (
                    <LoaderCircle
                      aria-hidden="true"
                      className="scans-spinner"
                      size={17}
                    />
                  ) : (
                    <Trash2
                      aria-hidden="true"
                      size={17}
                    />
                  )}

                  Delete scan evidence
                </button>
              </section>
            ) : null}
          </div>
        </section>
      )}

      <section className="scan-retention-section">
        <header>
          <Clock
            aria-hidden="true"
            size={21}
          />

          <div>
            <span className="scans-section-label">
              Local evidence retention
            </span>

            <h3>
              Retain newest project scans
            </h3>

            <p>
              Older raw scan files are deleted.
              Central finding records and lifecycle
              decisions remain intact.
            </p>
          </div>
        </header>

        <div className="scan-retention-grid">
          <label className="scans-filter-field">
            <span>
              Project
            </span>

            <select
              onChange={(event) => {
                setRetentionProjectId(
                  event.target.value,
                );

                setRetentionAcknowledged(
                  false,
                );

                setRetentionConfirmation(
                  "",
                );
              }}
              value={retentionProjectId}
            >
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

          <label className="scans-filter-field">
            <span>
              Keep newest scans
            </span>

            <input
              min={1}
              onChange={(event) => {
                setKeepLatestText(
                  event.target.value,
                );
              }}
              type="number"
              value={keepLatestText}
            />
          </label>
        </div>

        <label className="scan-danger-check">
          <input
            checked={
              retentionAcknowledged
            }
            onChange={(event) => {
              setRetentionAcknowledged(
                event.target.checked,
              );
            }}
            type="checkbox"
          />

          <span>
            I understand that older scan evidence
            exceeding the retention count will be
            permanently deleted.
          </span>
        </label>

        <label className="scan-danger-field">
          <span>
            Exact confirmation phrase
          </span>

          <code>
            {requiredRetentionPhrase}
          </code>

          <input
            autoComplete="off"
            onChange={(event) => {
              setRetentionConfirmation(
                event.target.value,
              );
            }}
            type="text"
            value={
              retentionConfirmation
            }
          />
        </label>

        <button
          className="scans-button scans-button-danger"
          disabled={
            !canApplyRetention
          }
          onClick={() => {
            retentionMutation.mutate();
          }}
          type="button"
        >
          {retentionMutation.isPending ? (
            <LoaderCircle
              aria-hidden="true"
              className="scans-spinner"
              size={17}
            />
          ) : (
            <Trash2
              aria-hidden="true"
              size={17}
            />
          )}

          Apply scan retention
        </button>

        {retentionMutation.data ? (
          <section className="scan-retention-result">
            <CheckCircle2
              aria-hidden="true"
              size={20}
            />

            <div>
              <strong>
                Retention applied
              </strong>

              <span>
                Deleted{" "}
                {
                  retentionMutation
                    .data.deleted_count
                }
                {" scan(s). "}
                {
                  retentionMutation
                    .data.after_count
                }
                {" remain."}
              </span>
            </div>
          </section>
        ) : null}
      </section>
    </div>
  );
}