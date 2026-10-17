import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Eye,
  FileWarning,
  LoaderCircle,
  Play,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  ShieldX,
} from "lucide-react";
import {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  getBOLAScan,
  listBOLAScans,
  runBOLAScan,
} from "../api/scans";
import type {
  BOLACaseResult,
  BOLAScan,
  BOLAScanSummary,
} from "../api/scans";
import {
  ApiRequestError,
} from "../api/projects";

import "./BOLAScanPanel.css";

interface BOLAScanPanelProps {
  projectId: string;
}

const CONFIRMATION_PHRASE =
  "RUN BOLA SCAN";

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

function resultClass(
  result: BOLACaseResult,
): string {
  return (
    "bola-result-status " +
    `bola-result-status-${result.outcome}`
  );
}

function summaryLabel(
  scan: BOLAScanSummary,
): string {
  return (
    `${formatDate(scan.completed_at)} — ` +
    `${scan.finding_count} finding(s)`
  );
}

function ResultIcon({
  result,
}: {
  result: BOLACaseResult;
}) {
  if (result.outcome === "pass") {
    return (
      <ShieldCheck
        aria-hidden="true"
        size={20}
      />
    );
  }

  if (
    result.outcome === "finding"
  ) {
    return (
      <ShieldX
        aria-hidden="true"
        size={20}
      />
    );
  }

  return (
    <ShieldAlert
      aria-hidden="true"
      size={20}
    />
  );
}

function ScanDetails({
  scan,
}: {
  scan: BOLAScan;
}) {
  return (
    <section className="bola-scan-details">
      <header className="bola-details-header">
        <div>
          <span className="bola-section-label">
            Persisted scan
          </span>

          <h4>
            Scan results
          </h4>

          <p>
            Completed{" "}
            {formatDate(
              scan.completed_at,
            )}
          </p>
        </div>

        <span
          className={
            "bola-scan-status " +
            `bola-scan-status-${scan.status}`
          }
        >
          {scan.status}
        </span>
      </header>

      <section className="bola-stat-grid">
        <article>
          <Eye
            aria-hidden="true"
            size={19}
          />

          <div>
            <span>
              Total cases
            </span>

            <strong>
              {scan.total_count}
            </strong>
          </div>
        </article>

        <article className="bola-stat-pass">
          <CheckCircle2
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

        <article className="bola-stat-finding">
          <FileWarning
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

        <article className="bola-stat-inconclusive">
          <AlertCircle
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
      </section>

      {scan.findings.length > 0 ? (
        <section className="bola-findings-section">
          <div className="bola-section-heading">
            <span className="bola-section-label">
              Confirmed observations
            </span>

            <h5>
              BOLA findings
            </h5>
          </div>

          <div className="bola-findings-grid">
            {scan.findings.map(
              (finding) => (
                <article
                  className="bola-finding-card"
                  key={
                    finding.finding_id
                  }
                >
                  <header>
                    <div>
                      <span>
                        {finding.category}
                      </span>

                      <h6>
                        {finding.title}
                      </h6>
                    </div>

                    <div className="bola-finding-badges">
                      <span
                        className={
                          "bola-severity " +
                          `bola-severity-${finding.severity}`
                        }
                      >
                        {finding.severity}
                      </span>

                      <span className="bola-confidence">
                        {finding.confidence}
                        {" confidence"}
                      </span>
                    </div>
                  </header>

                  <p>
                    {finding.description}
                  </p>

                  <dl>
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
                        Baseline
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

                    <div>
                      <dt>
                        Observed status
                      </dt>

                      <dd>
                        {
                          finding.observed_status_code
                        }
                      </dd>
                    </div>
                  </dl>
                </article>
              ),
            )}
          </div>
        </section>
      ) : (
        <section className="bola-no-findings">
          <ShieldCheck
            aria-hidden="true"
            size={28}
          />

          <h5>
            No BOLA findings in this scan
          </h5>

          <p>
            All classified cross-owner probes
            were denied as expected.
          </p>
        </section>
      )}

      <section className="bola-results-section">
        <div className="bola-section-heading">
          <span className="bola-section-label">
            Case evidence
          </span>

          <h5>
            Baseline and probe comparisons
          </h5>
        </div>

        <div className="bola-results-grid">
          {scan.results.map(
            (result) => (
              <article
                className="bola-result-card"
                key={result.case_id}
              >
                <header>
                  <div className="bola-result-title">
                    <div>
                      <ResultIcon
                        result={result}
                      />
                    </div>

                    <div>
                      <span>
                        {result.resource_type}
                      </span>

                      <h6>
                        {result.case_name}
                      </h6>
                    </div>
                  </div>

                  <span
                    className={resultClass(
                      result,
                    )}
                  >
                    {result.outcome}
                  </span>
                </header>

                <p>
                  {result.explanation}
                </p>

                <dl>
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
                      Baseline HTTP
                    </dt>

                    <dd>
                      {result.baseline_evidence
                        ?.status_code ??
                        "Not executed"}
                    </dd>
                  </div>

                  <div>
                    <dt>
                      Probe HTTP
                    </dt>

                    <dd>
                      {result.probe_evidence
                        ?.status_code ??
                        "Not executed"}
                    </dd>
                  </div>
                </dl>

                {result.issues.length >
                0 ? (
                  <ul>
                    {result.issues.map(
                      (issue) => (
                        <li key={issue}>
                          {issue}
                        </li>
                      ),
                    )}
                  </ul>
                ) : null}
              </article>
            ),
          )}
        </div>
      </section>
    </section>
  );
}

export function BOLAScanPanel({
  projectId,
}: BOLAScanPanelProps) {
  const queryClient =
    useQueryClient();

  const [
    selectedScanId,
    setSelectedScanId,
  ] = useState("");

  const [
    acknowledged,
    setAcknowledged,
  ] = useState(false);

  const [
    confirmation,
    setConfirmation,
  ] = useState("");

  const scansQuery = useQuery({
    queryKey: [
      "projects",
      projectId,
      "bola-scans",
    ],
    queryFn: () =>
      listBOLAScans(
        projectId,
      ),
  });

  const scans = useMemo(
    () =>
      scansQuery.data?.items ??
      [],
    [
      scansQuery.data?.items,
    ],
  );

  useEffect(() => {
    if (
      !selectedScanId &&
      scans.length > 0
    ) {
      setSelectedScanId(
        scans[0].scan_id,
      );
    }
  }, [
    scans,
    selectedScanId,
  ]);

  const scanQuery = useQuery({
    queryKey: [
      "projects",
      projectId,
      "bola-scans",
      selectedScanId,
    ],
    queryFn: () =>
      getBOLAScan(
        projectId,
        selectedScanId,
      ),
    enabled: Boolean(
      selectedScanId,
    ),
  });

  const runMutation =
    useMutation({
      mutationFn: () =>
        runBOLAScan(
          projectId,
          {
            acknowledge_authorization:
              acknowledged,
            confirmation:
              confirmation.trim(),
            max_cases: 100,
          },
        ),

      onSuccess: async (
        scan,
      ) => {
        setSelectedScanId(
          scan.scan_id,
        );

        queryClient.setQueryData(
          [
            "projects",
            projectId,
            "bola-scans",
            scan.scan_id,
          ],
          scan,
        );

        await queryClient.invalidateQueries({
          queryKey: [
            "projects",
            projectId,
            "bola-scans",
          ],
        });
      },
    });

  const combinedError =
    scansQuery.error ??
    scanQuery.error ??
    runMutation.error;

  const canRun =
    acknowledged &&
    confirmation.trim() ===
      CONFIRMATION_PHRASE &&
    !runMutation.isPending;

  return (
    <section className="bola-panel">
      <header className="bola-header">
        <div>
          <span className="bola-section-label">
            Controlled authorization testing
          </span>

          <h3>
            Automatic BOLA scan
          </h3>

          <p>
            Execute owned-object baselines and
            cross-owner probes using the current
            validated authorization dataset.
          </p>
        </div>

        <button
          className="bola-button bola-button-secondary"
          disabled={
            scansQuery.isFetching ||
            scanQuery.isFetching
          }
          onClick={() => {
            void scansQuery.refetch();

            if (selectedScanId) {
              void scanQuery.refetch();
            }
          }}
          type="button"
        >
          <RefreshCw
            aria-hidden="true"
            className={
              scansQuery.isFetching ||
              scanQuery.isFetching
                ? "bola-spinner"
                : undefined
            }
            size={17}
          />

          Refresh
        </button>
      </header>

      {combinedError ? (
        <section
          className="bola-alert"
          role="alert"
        >
          <AlertCircle
            aria-hidden="true"
            size={20}
          />

          <div>
            <strong>
              The BOLA scan operation failed.
            </strong>

            <span>
              {getErrorMessage(
                combinedError,
              )}
            </span>
          </div>
        </section>
      ) : null}

      <section className="bola-run-section">
        <div className="bola-section-heading">
          <span className="bola-section-label">
            Execution authorization
          </span>

          <h4>
            Run current BOLA plan
          </h4>

          <p>
            Only ready GET and HEAD plan items
            are executed. Confirm that the target
            is owned by you or that you have
            explicit permission to test it.
          </p>
        </div>

        <label className="bola-acknowledgement">
          <input
            checked={acknowledged}
            onChange={(event) => {
              setAcknowledged(
                event.target.checked,
              );
            }}
            type="checkbox"
          />

          <span>
            <strong>
              I am authorized to test this target
            </strong>

            <small>
              AccessMatrix will send multiple
              authenticated requests to the
              configured exact origin.
            </small>
          </span>
        </label>

        <label className="bola-confirmation-field">
          <span>
            Exact confirmation phrase
          </span>

          <code>
            {CONFIRMATION_PHRASE}
          </code>

          <input
            autoComplete="off"
            onChange={(event) => {
              setConfirmation(
                event.target.value,
              );
            }}
            placeholder={
              CONFIRMATION_PHRASE
            }
            type="text"
            value={confirmation}
          />
        </label>

        <button
          className="bola-button bola-button-primary"
          disabled={!canRun}
          onClick={() => {
            runMutation.mutate();
          }}
          type="button"
        >
          {runMutation.isPending ? (
            <>
              <LoaderCircle
                aria-hidden="true"
                className="bola-spinner"
                size={17}
              />

              Running BOLA scan
            </>
          ) : (
            <>
              <Play
                aria-hidden="true"
                size={17}
              />

              Run BOLA scan
            </>
          )}
        </button>
      </section>

      <section className="bola-history-section">
        <div className="bola-section-heading">
          <span className="bola-section-label">
            Scan history
          </span>

          <h4>
            Persisted scans
          </h4>
        </div>

        {scansQuery.isPending ? (
          <section className="bola-loading">
            <LoaderCircle
              aria-hidden="true"
              className="bola-spinner"
              size={27}
            />

            <strong>
              Loading BOLA scans
            </strong>
          </section>
        ) : scans.length === 0 ? (
          <section className="bola-empty">
            <Clock
              aria-hidden="true"
              size={28}
            />

            <h5>
              No scans have been run
            </h5>

            <p>
              Confirm authorization and run the
              current BOLA plan.
            </p>
          </section>
        ) : (
          <label className="bola-history-select">
            <span>
              Selected scan
            </span>

            <select
              onChange={(event) => {
                setSelectedScanId(
                  event.target.value,
                );
              }}
              value={selectedScanId}
            >
              {scans.map(
                (scan) => (
                  <option
                    key={scan.scan_id}
                    value={scan.scan_id}
                  >
                    {summaryLabel(
                      scan,
                    )}
                  </option>
                ),
              )}
            </select>
          </label>
        )}
      </section>

      {scanQuery.isPending &&
      selectedScanId ? (
        <section className="bola-loading">
          <LoaderCircle
            aria-hidden="true"
            className="bola-spinner"
            size={27}
          />

          <strong>
            Loading scan evidence
          </strong>
        </section>
      ) : null}

      {scanQuery.data ? (
        <ScanDetails
          scan={scanQuery.data}
        />
      ) : null}
    </section>
  );
}