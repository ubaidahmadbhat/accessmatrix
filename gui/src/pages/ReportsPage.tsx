import {
  useMutation,
  useQueries,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  AlertCircle,
  Braces,
  CheckCircle2,
  Code2,
  Download,
  FileCode2,
  FileJson2,
  FileText,
  FolderKanban,
  LoaderCircle,
  RefreshCw,
  Search,
  ShieldCheck,
} from "lucide-react";
import {
  useEffect,
  useMemo,
  useState,
} from "react";

import type {
  GenerateReportInput,
  ReportArtifactMetadata,
  ReportFindingStatus,
  ReportFormat,
} from "../api/reports";
import {
  generateReport,
  getReportPreview,
  listReports,
  reportDownloadUrl,
} from "../api/reports";
import {
  ApiRequestError,
  listProjects,
} from "../api/projects";
import type {
  Project,
} from "../api/projects";

import "./ReportsPage.css";

interface ReportWithProject {
  key: string;
  project: Project;
  report: ReportArtifactMetadata;
}

type ReportScope =
  | "all"
  | ReportFindingStatus;

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

function formatBytes(
  value: number,
): string {
  if (value < 1024) {
    return `${value} B`;
  }

  if (
    value <
    1024 * 1024
  ) {
    return (
      `${(
        value / 1024
      ).toFixed(1)} KB`
    );
  }

  return (
    `${(
      value /
      (1024 * 1024)
    ).toFixed(1)} MB`
  );
}

function reportKey(
  projectId: string,
  reportId: string,
): string {
  return (
    `${projectId}:` +
    reportId
  );
}

function formatLabel(
  format: ReportFormat,
): string {
  switch (format) {
    case "markdown":
      return "Markdown";

    case "html":
      return "HTML";

    case "sarif":
      return "SARIF";

    case "junit":
      return "JUnit XML";

    default:
      return "JSON";
  }
}

function FormatIcon({
  format,
}: {
  format: ReportFormat;
}) {
  if (format === "json") {
    return (
      <FileJson2
        aria-hidden="true"
        size={19}
      />
    );
  }

  if (format === "markdown") {
    return (
      <FileText
        aria-hidden="true"
        size={19}
      />
    );
  }

  if (format === "html") {
    return (
      <Code2
        aria-hidden="true"
        size={19}
      />
    );
  }

  if (format === "sarif") {
    return (
      <ShieldCheck
        aria-hidden="true"
        size={19}
      />
    );
  }

  return (
    <Braces
      aria-hidden="true"
      size={19}
    />
  );
}

export function ReportsPage() {
  const queryClient =
    useQueryClient();

  const [
    generationProjectId,
    setGenerationProjectId,
  ] = useState("");

  const [
    generationFormat,
    setGenerationFormat,
  ] = useState<ReportFormat>(
    "html",
  );

  const [
    generationTitle,
    setGenerationTitle,
  ] = useState("");

  const [
    generationScope,
    setGenerationScope,
  ] = useState<ReportScope>(
    "all",
  );

  const [
    includeScanHistory,
    setIncludeScanHistory,
  ] = useState(true);

  const [
    projectFilter,
    setProjectFilter,
  ] = useState("all");

  const [
    formatFilter,
    setFormatFilter,
  ] = useState<
    "all" | ReportFormat
  >("all");

  const [
    searchText,
    setSearchText,
  ] = useState("");

  const [
    selectedKey,
    setSelectedKey,
  ] = useState("");

  const projectsQuery = useQuery({
    queryKey: [
      "projects",
    ],
    queryFn: listProjects,
  });

  const projects = useMemo(
    () =>
      projectsQuery.data ?? [],
    [
      projectsQuery.data,
    ],
  );

  useEffect(() => {
    if (
      !generationProjectId &&
      projects.length > 0
    ) {
      setGenerationProjectId(
        projects[0].id,
      );
    }
  }, [
    generationProjectId,
    projects,
  ]);

  const reportQueries =
    useQueries({
      queries: projects.map(
        (project) => ({
          queryKey: [
            "projects",
            project.id,
            "reports",
          ],
          queryFn: () =>
            listReports(
              project.id,
            ),
        }),
      ),
    });

  const allReports:
    ReportWithProject[] = [];

  projects.forEach(
    (
      project,
      projectIndex,
    ) => {
      const reportList =
        reportQueries[
          projectIndex
        ]?.data;

      for (
        const report
        of reportList?.items ?? []
      ) {
        allReports.push({
          key: reportKey(
            project.id,
            report.report_id,
          ),
          project,
          report,
        });
      }
    },
  );

  allReports.sort(
    (
      first,
      second,
    ) =>
      new Date(
        second.report.generated_at,
      ).getTime() -
      new Date(
        first.report.generated_at,
      ).getTime(),
  );

  const normalizedSearch =
    searchText
      .trim()
      .toLowerCase();

  const filteredReports =
    allReports.filter(
      ({
        project,
        report,
      }) => {
        if (
          projectFilter !== "all" &&
          project.id !== projectFilter
        ) {
          return false;
        }

        if (
          formatFilter !== "all" &&
          report.report_format !==
            formatFilter
        ) {
          return false;
        }

        if (!normalizedSearch) {
          return true;
        }

        return [
          project.name,
          report.title,
          report.filename,
          report.report_id,
          report.report_format,
        ]
          .join(" ")
          .toLowerCase()
          .includes(
            normalizedSearch,
          );
      },
    );

  const selectedItem =
    filteredReports.find(
      (item) =>
        item.key === selectedKey,
    ) ??
    filteredReports[0] ??
    null;

  const previewQuery = useQuery({
    queryKey: [
      "projects",
      selectedItem?.project.id,
      "reports",
      selectedItem?.report.report_id,
      "preview",
    ],

    queryFn: () => {
      if (!selectedItem) {
        throw new Error(
          "No report is selected.",
        );
      }

      return getReportPreview(
        selectedItem.project.id,
        selectedItem.report.report_id,
      );
    },

    enabled: Boolean(
      selectedItem,
    ),
  });

  const generateMutation =
    useMutation({
      mutationFn: (
        input: GenerateReportInput,
      ) =>
        generateReport(
          input,
        ),

      onSuccess: async (
        report,
      ) => {
        setSelectedKey(
          reportKey(
            report.project_id,
            report.report_id,
          ),
        );

        await queryClient.invalidateQueries({
          queryKey: [
            "projects",
            report.project_id,
            "reports",
          ],
        });
      },
    });

  const queryError =
    reportQueries.find(
      (query) =>
        query.error !== null,
    )?.error;

  const combinedError =
    projectsQuery.error ??
    queryError ??
    previewQuery.error ??
    generateMutation.error;

  const loading =
    projectsQuery.isPending ||
    reportQueries.some(
      (query) =>
        query.isPending,
    );

  const fetching =
    projectsQuery.isFetching ||
    reportQueries.some(
      (query) =>
        query.isFetching,
    ) ||
    previewQuery.isFetching;

  const htmlCount =
    allReports.filter(
      ({ report }) =>
        report.report_format ===
        "html",
    ).length;

  const machineReadableCount =
    allReports.filter(
      ({ report }) =>
        [
          "json",
          "sarif",
          "junit",
        ].includes(
          report.report_format,
        ),
    ).length;

  const totalBytes =
    allReports.reduce(
      (
        count,
        {
          report,
        },
      ) =>
        count +
        report.size_bytes,
      0,
    );

  const includeStatuses:
    ReportFindingStatus[] =
    generationScope === "all"
      ? [
          "open",
          "resolved",
          "false_positive",
          "accepted_risk",
        ]
      : [
          generationScope,
        ];

  const canGenerate =
    Boolean(
      generationProjectId,
    ) &&
    !generateMutation.isPending;

  function refreshAll(): void {
    void projectsQuery.refetch();

    for (
      const reportQuery
      of reportQueries
    ) {
      void reportQuery.refetch();
    }

    if (selectedItem) {
      void previewQuery.refetch();
    }
  }

  function submitReport(): void {
    if (!canGenerate) {
      return;
    }

    generateMutation.mutate({
      projectId:
        generationProjectId,
      report_format:
        generationFormat,
      title:
        generationTitle.trim() ||
        null,
      include_statuses:
        includeStatuses,
      include_scan_history:
        includeScanHistory,
    });
  }

  return (
    <div className="page reports-page">
      <section className="reports-header">
        <div>
          <span className="reports-section-label">
            Export and integration
          </span>

          <h2>
            Reports
          </h2>

          <p>
            Generate local authorization reports
            for human review, CI systems, security
            tooling, and audit evidence.
          </p>
        </div>

        <button
          className="reports-button reports-button-secondary"
          disabled={fetching}
          onClick={refreshAll}
          type="button"
        >
          <RefreshCw
            aria-hidden="true"
            className={
              fetching
                ? "reports-spinner"
                : undefined
            }
            size={17}
          />

          Refresh
        </button>
      </section>

      {combinedError ? (
        <section
          className="reports-alert"
          role="alert"
        >
          <AlertCircle
            aria-hidden="true"
            size={21}
          />

          <div>
            <strong>
              The report operation failed.
            </strong>

            <span>
              {getErrorMessage(
                combinedError,
              )}
            </span>
          </div>
        </section>
      ) : null}

      {generateMutation.isSuccess ? (
        <section
          className="reports-success"
          role="status"
        >
          <CheckCircle2
            aria-hidden="true"
            size={20}
          />

          <div>
            <strong>
              Report generated successfully.
            </strong>

            <span>
              The artifact is stored locally
              and ready for preview or download.
            </span>
          </div>
        </section>
      ) : null}

      <section className="reports-stat-grid">
        <article>
          <FileCode2
            aria-hidden="true"
            size={20}
          />

          <div>
            <span>
              Stored reports
            </span>

            <strong>
              {allReports.length}
            </strong>
          </div>
        </article>

        <article>
          <Code2
            aria-hidden="true"
            size={20}
          />

          <div>
            <span>
              HTML reports
            </span>

            <strong>
              {htmlCount}
            </strong>
          </div>
        </article>

        <article>
          <Braces
            aria-hidden="true"
            size={20}
          />

          <div>
            <span>
              Machine-readable
            </span>

            <strong>
              {machineReadableCount}
            </strong>
          </div>
        </article>

        <article>
          <Download
            aria-hidden="true"
            size={20}
          />

          <div>
            <span>
              Local storage
            </span>

            <strong>
              {formatBytes(
                totalBytes,
              )}
            </strong>
          </div>
        </article>
      </section>

      <section className="report-generator">
        <header>
          <div>
            <span className="reports-section-label">
              Report generation
            </span>

            <h3>
              Create a project report
            </h3>

            <p>
              Select the report format and finding
              lifecycle scope. HTML previews are
              displayed as source text and are not
              executed inside AccessMatrix.
            </p>
          </div>
        </header>

        <div className="report-generator-grid">
          <label className="report-field">
            <span>
              Project
            </span>

            <select
              onChange={(event) => {
                setGenerationProjectId(
                  event.target.value,
                );
              }}
              value={
                generationProjectId
              }
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

          <label className="report-field">
            <span>
              Report format
            </span>

            <select
              onChange={(event) => {
                setGenerationFormat(
                  event.target
                    .value as ReportFormat,
                );
              }}
              value={
                generationFormat
              }
            >
              <option value="html">
                HTML
              </option>

              <option value="markdown">
                Markdown
              </option>

              <option value="json">
                JSON
              </option>

              <option value="sarif">
                SARIF 2.1.0
              </option>

              <option value="junit">
                JUnit XML
              </option>
            </select>
          </label>

          <label className="report-field">
            <span>
              Finding scope
            </span>

            <select
              onChange={(event) => {
                setGenerationScope(
                  event.target
                    .value as ReportScope,
                );
              }}
              value={
                generationScope
              }
            >
              <option value="all">
                All lifecycle statuses
              </option>

              <option value="open">
                Open only
              </option>

              <option value="resolved">
                Resolved only
              </option>

              <option value="false_positive">
                False positives only
              </option>

              <option value="accepted_risk">
                Accepted risks only
              </option>
            </select>
          </label>

          <label className="report-field report-title-field">
            <span>
              Custom report title
            </span>

            <input
              maxLength={200}
              onChange={(event) => {
                setGenerationTitle(
                  event.target.value,
                );
              }}
              placeholder="Leave empty for the standard project title"
              type="text"
              value={
                generationTitle
              }
            />
          </label>
        </div>

        <label className="report-check-field">
          <input
            checked={
              includeScanHistory
            }
            onChange={(event) => {
              setIncludeScanHistory(
                event.target.checked,
              );
            }}
            type="checkbox"
          />

          <span>
            <strong>
              Include scan history
            </strong>

            <small>
              Adds persisted scan summaries
              without embedding raw response bodies.
            </small>
          </span>
        </label>

        <button
          className="reports-button reports-button-primary"
          disabled={!canGenerate}
          onClick={submitReport}
          type="button"
        >
          {generateMutation.isPending ? (
            <>
              <LoaderCircle
                aria-hidden="true"
                className="reports-spinner"
                size={17}
              />

              Generating report
            </>
          ) : (
            <>
              <FileCode2
                aria-hidden="true"
                size={17}
              />

              Generate report
            </>
          )}
        </button>
      </section>

      <section className="reports-filter-panel">
        <label className="reports-search-field">
          <span>
            Search reports
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
              placeholder="Title, project, filename or report ID"
              type="search"
              value={searchText}
            />
          </div>
        </label>

        <label className="report-field">
          <span>
            Project filter
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

        <label className="report-field">
          <span>
            Format filter
          </span>

          <select
            onChange={(event) => {
              setFormatFilter(
                event.target.value as
                  | "all"
                  | ReportFormat,
              );
            }}
            value={formatFilter}
          >
            <option value="all">
              All formats
            </option>

            <option value="html">
              HTML
            </option>

            <option value="markdown">
              Markdown
            </option>

            <option value="json">
              JSON
            </option>

            <option value="sarif">
              SARIF
            </option>

            <option value="junit">
              JUnit XML
            </option>
          </select>
        </label>
      </section>

      {loading ? (
        <section className="reports-loading">
          <LoaderCircle
            aria-hidden="true"
            className="reports-spinner"
            size={30}
          />

          <strong>
            Loading generated reports
          </strong>
        </section>
      ) : filteredReports.length ===
        0 ? (
        <section className="reports-empty">
          <FolderKanban
            aria-hidden="true"
            size={31}
          />

          <h3>
            No reports match the current view
          </h3>

          <p>
            Generate a report or change the
            active filters.
          </p>
        </section>
      ) : (
        <section className="reports-workspace">
          <aside className="reports-list">
            {filteredReports.map(
              (item) => {
                const active =
                  selectedItem?.key ===
                  item.key;

                return (
                  <button
                    className={
                      active
                        ? "report-list-card report-list-card-active"
                        : "report-list-card"
                    }
                    key={item.key}
                    onClick={() => {
                      setSelectedKey(
                        item.key,
                      );
                    }}
                    type="button"
                  >
                    <header>
                      <div className="report-format-icon">
                        <FormatIcon
                          format={
                            item.report
                              .report_format
                          }
                        />
                      </div>

                      <span className="report-format-badge">
                        {formatLabel(
                          item.report
                            .report_format,
                        )}
                      </span>
                    </header>

                    <h3>
                      {item.report.title}
                    </h3>

                    <p>
                      {item.project.name}
                    </p>

                    <code>
                      {item.report.filename}
                    </code>

                    <footer>
                      <span>
                        {
                          item.report
                            .finding_count
                        }
                        {" finding(s)"}
                      </span>

                      <span>
                        {formatBytes(
                          item.report
                            .size_bytes,
                        )}
                      </span>
                    </footer>
                  </button>
                );
              },
            )}
          </aside>

          {selectedItem ? (
            <section className="report-detail">
              <header className="report-detail-header">
                <div>
                  <span className="reports-section-label">
                    Stored artifact
                  </span>

                  <h3>
                    {
                      selectedItem
                        .report.title
                    }
                  </h3>

                  <p>
                    Generated{" "}
                    {formatDate(
                      selectedItem
                        .report
                        .generated_at,
                    )}
                  </p>
                </div>

                <a
                  className="reports-button reports-button-download"
                  href={reportDownloadUrl(
                    selectedItem
                      .project.id,
                    selectedItem
                      .report
                      .report_id,
                  )}
                >
                  <Download
                    aria-hidden="true"
                    size={17}
                  />

                  Download
                </a>
              </header>

              <section className="report-detail-grid">
                <article>
                  <span>
                    Format
                  </span>

                  <strong>
                    {formatLabel(
                      selectedItem
                        .report
                        .report_format,
                    )}
                  </strong>
                </article>

                <article>
                  <span>
                    Findings
                  </span>

                  <strong>
                    {
                      selectedItem
                        .report
                        .finding_count
                    }
                  </strong>
                </article>

                <article>
                  <span>
                    Scans
                  </span>

                  <strong>
                    {
                      selectedItem
                        .report
                        .scan_count
                    }
                  </strong>
                </article>

                <article>
                  <span>
                    File size
                  </span>

                  <strong>
                    {formatBytes(
                      selectedItem
                        .report
                        .size_bytes,
                    )}
                  </strong>
                </article>
              </section>

              <section className="report-integrity">
                <span>
                  SHA-256
                </span>

                <code>
                  {
                    selectedItem
                      .report.sha256
                  }
                </code>
              </section>

              <section className="report-preview">
                <header>
                  <div>
                    <span className="reports-section-label">
                      Safe source preview
                    </span>

                    <h4>
                      Report contents
                    </h4>
                  </div>

                  {previewQuery.isFetching ? (
                    <LoaderCircle
                      aria-hidden="true"
                      className="reports-spinner"
                      size={19}
                    />
                  ) : null}
                </header>

                {previewQuery.isPending ? (
                  <div className="report-preview-loading">
                    Loading report preview
                  </div>
                ) : (
                  <pre>
                    {previewQuery.data ??
                      "Preview unavailable."}
                  </pre>
                )}
              </section>
            </section>
          ) : null}
        </section>
      )}
    </div>
  );
}