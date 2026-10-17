import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  Clock,
  Database,
  Globe2,
  History,
  KeyRound,
  LoaderCircle,
  RefreshCw,
  RotateCcw,
  Save,
  Search,
  Server,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";
import {
  useEffect,
  useMemo,
  useState,
} from "react";

import type {
  ApplicationSettings,
  AuditEvent,
  NetworkAccessMode,
} from "../api/settings";
import {
  getApplicationSettings,
  listAuditEvents,
  resetApplicationSettings,
  saveApplicationSettings,
  validateTarget,
} from "../api/settings";
import {
  ApiRequestError,
} from "../api/projects";

import "./SettingsPage.css";

const RESET_CONFIRMATION =
  "RESET APPLICATION SETTINGS";

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

function cloneSettings(
  settings: ApplicationSettings,
): ApplicationSettings {
  return JSON.parse(
    JSON.stringify(
      settings,
    ),
  ) as ApplicationSettings;
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

function auditOutcomeClass(
  event: AuditEvent,
): string {
  return (
    "settings-audit-outcome " +
    `settings-audit-outcome-${event.outcome}`
  );
}

export function SettingsPage() {
  const queryClient =
    useQueryClient();

  const [
    draft,
    setDraft,
  ] = useState<
    ApplicationSettings | null
  >(null);

  const [
    targetUrl,
    setTargetUrl,
  ] = useState(
    "http://127.0.0.1:9000",
  );

  const [
    resetConfirmation,
    setResetConfirmation,
  ] = useState("");

  const settingsQuery = useQuery({
    queryKey: [
      "application-settings",
    ],
    queryFn:
      getApplicationSettings,
  });

  const auditQuery = useQuery({
    queryKey: [
      "audit-events",
    ],
    queryFn: () =>
      listAuditEvents(
        100,
      ),
  });

  useEffect(() => {
    if (settingsQuery.data) {
      setDraft(
        cloneSettings(
          settingsQuery.data,
        ),
      );
    }
  }, [
    settingsQuery.data,
  ]);

  const auditEvents = useMemo(
    () =>
      auditQuery.data?.items ?? [],
    [
      auditQuery.data?.items,
    ],
  );

  const saveMutation =
    useMutation({
      mutationFn:
        saveApplicationSettings,

      onSuccess: async (
        settings,
      ) => {
        setDraft(
          cloneSettings(
            settings,
          ),
        );

        queryClient.setQueryData(
          [
            "application-settings",
          ],
          settings,
        );

        await queryClient.invalidateQueries({
          queryKey: [
            "audit-events",
          ],
        });
      },
    });

  const resetMutation =
    useMutation({
      mutationFn: () =>
        resetApplicationSettings(
          resetConfirmation.trim(),
        ),

      onSuccess: async (
        settings,
      ) => {
        setDraft(
          cloneSettings(
            settings,
          ),
        );

        setResetConfirmation("");

        queryClient.setQueryData(
          [
            "application-settings",
          ],
          settings,
        );

        await queryClient.invalidateQueries({
          queryKey: [
            "audit-events",
          ],
        });
      },
    });

  const targetMutation =
    useMutation({
      mutationFn: () =>
        validateTarget(
          targetUrl.trim(),
        ),

      onSuccess: async () => {
        await queryClient.invalidateQueries({
          queryKey: [
            "audit-events",
          ],
        });
      },
    });

  const combinedError =
    settingsQuery.error ??
    auditQuery.error ??
    saveMutation.error ??
    resetMutation.error ??
    targetMutation.error;

  const loading =
    settingsQuery.isPending ||
    !draft;

  const dirty =
    Boolean(
      draft &&
      settingsQuery.data &&
      JSON.stringify(
        draft,
      ) !==
        JSON.stringify(
          settingsQuery.data,
        ),
    );

  const busy =
    saveMutation.isPending ||
    resetMutation.isPending ||
    targetMutation.isPending;

  const canReset =
    resetConfirmation.trim() ===
      RESET_CONFIRMATION &&
    !resetMutation.isPending;

  function refreshAll(): void {
    void settingsQuery.refetch();
    void auditQuery.refetch();
  }

  if (loading) {
    return (
      <div className="page settings-page">
        <section className="settings-loading">
          <LoaderCircle
            aria-hidden="true"
            className="settings-spinner"
            size={30}
          />

          <strong>
            Loading application settings
          </strong>
        </section>
      </div>
    );
  }

  return (
    <div className="page settings-page">
      <section className="settings-header">
        <div>
          <span className="settings-section-label">
            Local security configuration
          </span>

          <h2>
            Settings
          </h2>

          <p>
            Configure network target policies,
            controlled execution limits, evidence
            retention, and local audit logging.
          </p>
        </div>

        <button
          className="settings-button settings-button-secondary"
          disabled={
            settingsQuery.isFetching ||
            auditQuery.isFetching
          }
          onClick={refreshAll}
          type="button"
        >
          <RefreshCw
            aria-hidden="true"
            className={
              settingsQuery.isFetching ||
              auditQuery.isFetching
                ? "settings-spinner"
                : undefined
            }
            size={17}
          />

          Refresh
        </button>
      </section>

      {combinedError ? (
        <section
          className="settings-alert"
          role="alert"
        >
          <AlertCircle
            aria-hidden="true"
            size={21}
          />

          <div>
            <strong>
              The settings operation failed.
            </strong>

            <span>
              {getErrorMessage(
                combinedError,
              )}
            </span>
          </div>
        </section>
      ) : null}

      {saveMutation.isSuccess ? (
        <section
          className="settings-success"
          role="status"
        >
          <CheckCircle2
            aria-hidden="true"
            size={20}
          />

          <div>
            <strong>
              Settings saved.
            </strong>

            <span>
              The persistent application
              configuration has been updated.
            </span>
          </div>
        </section>
      ) : null}

      <section className="settings-stat-grid">
        <article>
          <Globe2
            aria-hidden="true"
            size={20}
          />

          <div>
            <span>
              Network mode
            </span>

            <strong>
              {draft.network.access_mode
                .replaceAll(
                  "_",
                  " ",
                )}
            </strong>
          </div>
        </article>

        <article>
          <Clock
            aria-hidden="true"
            size={20}
          />

          <div>
            <span>
              Default timeout
            </span>

            <strong>
              {
                draft.execution
                  .default_timeout_seconds
              }
              {" seconds"}
            </strong>
          </div>
        </article>

        <article>
          <Activity
            aria-hidden="true"
            size={20}
          />

          <div>
            <span>
              Rate limit
            </span>

            <strong>
              {
                draft.execution
                  .rate_limit_requests
              }
              {" requests"}
            </strong>
          </div>
        </article>

        <article>
          <History
            aria-hidden="true"
            size={20}
          />

          <div>
            <span>
              Audit events
            </span>

            <strong>
              {auditEvents.length}
            </strong>
          </div>
        </article>
      </section>

      <section className="settings-card">
        <header>
          <Globe2
            aria-hidden="true"
            size={21}
          />

          <div>
            <span className="settings-section-label">
              Network safety
            </span>

            <h3>
              Target network policy
            </h3>

            <p>
              Mixed DNS responses are rejected
              when any resolved address violates
              the selected policy.
            </p>
          </div>
        </header>

        <div className="settings-field-grid">
          <label className="settings-field">
            <span>
              Network access mode
            </span>

            <select
              onChange={(event) => {
                setDraft({
                  ...draft,
                  network: {
                    ...draft.network,
                    access_mode:
                      event.target
                        .value as NetworkAccessMode,
                  },
                });
              }}
              value={
                draft.network.access_mode
              }
            >
              <option value="public_only">
                Public addresses only
              </option>

              <option value="public_and_loopback">
                Public and loopback
              </option>

              <option value="private_networks">
                Public, loopback and private networks
              </option>
            </select>
          </label>

          <label className="settings-field">
            <span>
              DNS timeout in seconds
            </span>

            <input
              max={15}
              min={0.5}
              onChange={(event) => {
                setDraft({
                  ...draft,
                  network: {
                    ...draft.network,
                    dns_resolution_timeout_seconds:
                      Number(
                        event.target.value,
                      ),
                  },
                });
              }}
              step={0.5}
              type="number"
              value={
                draft.network
                  .dns_resolution_timeout_seconds
              }
            />
          </label>

          <label className="settings-field">
            <span>
              Maximum resolved addresses
            </span>

            <input
              max={128}
              min={1}
              onChange={(event) => {
                setDraft({
                  ...draft,
                  network: {
                    ...draft.network,
                    max_resolved_addresses:
                      Number(
                        event.target.value,
                      ),
                  },
                });
              }}
              type="number"
              value={
                draft.network
                  .max_resolved_addresses
              }
            />
          </label>
        </div>

        <div className="settings-check-grid">
          <label>
            <input
              checked={
                draft.network
                  .resolve_hostnames
              }
              onChange={(event) => {
                setDraft({
                  ...draft,
                  network: {
                    ...draft.network,
                    resolve_hostnames:
                      event.target.checked,
                  },
                });
              }}
              type="checkbox"
            />

            <span>
              Resolve hostnames before policy evaluation
            </span>
          </label>

          <label>
            <input
              checked={
                draft.network
                  .allow_link_local
              }
              onChange={(event) => {
                setDraft({
                  ...draft,
                  network: {
                    ...draft.network,
                    allow_link_local:
                      event.target.checked,
                  },
                });
              }}
              type="checkbox"
            />

            <span>
              Permit link-local addresses
            </span>
          </label>

          <label>
            <input
              checked={
                draft.network
                  .allow_multicast
              }
              onChange={(event) => {
                setDraft({
                  ...draft,
                  network: {
                    ...draft.network,
                    allow_multicast:
                      event.target.checked,
                  },
                });
              }}
              type="checkbox"
            />

            <span>
              Permit multicast addresses
            </span>
          </label>

          <label>
            <input
              checked={
                draft.network
                  .allow_reserved
              }
              onChange={(event) => {
                setDraft({
                  ...draft,
                  network: {
                    ...draft.network,
                    allow_reserved:
                      event.target.checked,
                  },
                });
              }}
              type="checkbox"
            />

            <span>
              Permit reserved address ranges
            </span>
          </label>
        </div>
      </section>

      <section className="settings-card">
        <header>
          <Server
            aria-hidden="true"
            size={21}
          />

          <div>
            <span className="settings-section-label">
              Controlled execution
            </span>

            <h3>
              Request limits
            </h3>
          </div>
        </header>

        <div className="settings-field-grid">
          <label className="settings-field">
            <span>
              Default timeout seconds
            </span>

            <input
              max={30}
              min={1}
              onChange={(event) => {
                setDraft({
                  ...draft,
                  execution: {
                    ...draft.execution,
                    default_timeout_seconds:
                      Number(
                        event.target.value,
                      ),
                  },
                });
              }}
              step={0.5}
              type="number"
              value={
                draft.execution
                  .default_timeout_seconds
              }
            />
          </label>

          <label className="settings-field">
            <span>
              Maximum request bytes
            </span>

            <input
              min={1024}
              onChange={(event) => {
                setDraft({
                  ...draft,
                  execution: {
                    ...draft.execution,
                    max_request_bytes:
                      Number(
                        event.target.value,
                      ),
                  },
                });
              }}
              type="number"
              value={
                draft.execution
                  .max_request_bytes
              }
            />
          </label>

          <label className="settings-field">
            <span>
              Maximum response bytes
            </span>

            <input
              min={1024}
              onChange={(event) => {
                setDraft({
                  ...draft,
                  execution: {
                    ...draft.execution,
                    max_response_bytes:
                      Number(
                        event.target.value,
                      ),
                  },
                });
              }}
              type="number"
              value={
                draft.execution
                  .max_response_bytes
              }
            />
          </label>

          <label className="settings-field">
            <span>
              Requests per window
            </span>

            <input
              min={1}
              onChange={(event) => {
                setDraft({
                  ...draft,
                  execution: {
                    ...draft.execution,
                    rate_limit_requests:
                      Number(
                        event.target.value,
                      ),
                  },
                });
              }}
              type="number"
              value={
                draft.execution
                  .rate_limit_requests
              }
            />
          </label>

          <label className="settings-field">
            <span>
              Rate-limit window seconds
            </span>

            <input
              min={1}
              onChange={(event) => {
                setDraft({
                  ...draft,
                  execution: {
                    ...draft.execution,
                    rate_limit_window_seconds:
                      Number(
                        event.target.value,
                      ),
                  },
                });
              }}
              step={1}
              type="number"
              value={
                draft.execution
                  .rate_limit_window_seconds
              }
            />
          </label>

          <label className="settings-field">
            <span>
              Maximum parallel requests
            </span>

            <input
              max={32}
              min={1}
              onChange={(event) => {
                setDraft({
                  ...draft,
                  execution: {
                    ...draft.execution,
                    max_parallel_requests:
                      Number(
                        event.target.value,
                      ),
                  },
                });
              }}
              type="number"
              value={
                draft.execution
                  .max_parallel_requests
              }
            />
          </label>
        </div>
      </section>

      <section className="settings-card">
        <header>
          <Database
            aria-hidden="true"
            size={21}
          />

          <div>
            <span className="settings-section-label">
              Evidence and retention
            </span>

            <h3>
              Local evidence limits
            </h3>
          </div>
        </header>

        <div className="settings-field-grid">
          <label className="settings-field">
            <span>
              Body excerpt characters
            </span>

            <input
              min={0}
              onChange={(event) => {
                setDraft({
                  ...draft,
                  evidence: {
                    ...draft.evidence,
                    body_excerpt_characters:
                      Number(
                        event.target.value,
                      ),
                  },
                });
              }}
              type="number"
              value={
                draft.evidence
                  .body_excerpt_characters
              }
            />
          </label>

          <label className="settings-field">
            <span>
              Maximum scan bytes
            </span>

            <input
              min={1048576}
              onChange={(event) => {
                setDraft({
                  ...draft,
                  evidence: {
                    ...draft.evidence,
                    max_scan_bytes:
                      Number(
                        event.target.value,
                      ),
                  },
                });
              }}
              type="number"
              value={
                draft.evidence
                  .max_scan_bytes
              }
            />
          </label>

          <label className="settings-field">
            <span>
              Maximum report bytes
            </span>

            <input
              min={1048576}
              onChange={(event) => {
                setDraft({
                  ...draft,
                  evidence: {
                    ...draft.evidence,
                    max_report_bytes:
                      Number(
                        event.target.value,
                      ),
                  },
                });
              }}
              type="number"
              value={
                draft.evidence
                  .max_report_bytes
              }
            />
          </label>

          <label className="settings-field">
            <span>
              Default scan retention
            </span>

            <input
              min={1}
              onChange={(event) => {
                setDraft({
                  ...draft,
                  evidence: {
                    ...draft.evidence,
                    scan_retention_keep_latest:
                      Number(
                        event.target.value,
                      ),
                  },
                });
              }}
              type="number"
              value={
                draft.evidence
                  .scan_retention_keep_latest
              }
            />
          </label>
        </div>

        <div className="settings-check-grid">
          <label>
            <input
              checked={
                draft.evidence
                  .store_response_headers
              }
              onChange={(event) => {
                setDraft({
                  ...draft,
                  evidence: {
                    ...draft.evidence,
                    store_response_headers:
                      event.target.checked,
                  },
                });
              }}
              type="checkbox"
            />

            <span>
              Store redacted response headers
            </span>
          </label>
        </div>
      </section>

      <section className="settings-card">
        <header>
          <KeyRound
            aria-hidden="true"
            size={21}
          />

          <div>
            <span className="settings-section-label">
              Audit logging
            </span>

            <h3>
              Audit retention
            </h3>
          </div>
        </header>

        <div className="settings-field-grid">
          <label className="settings-field">
            <span>
              Retention days
            </span>

            <input
              min={1}
              onChange={(event) => {
                setDraft({
                  ...draft,
                  audit: {
                    ...draft.audit,
                    retention_days:
                      Number(
                        event.target.value,
                      ),
                  },
                });
              }}
              type="number"
              value={
                draft.audit
                  .retention_days
              }
            />
          </label>

          <label className="settings-field">
            <span>
              Maximum audit events
            </span>

            <input
              min={100}
              onChange={(event) => {
                setDraft({
                  ...draft,
                  audit: {
                    ...draft.audit,
                    max_events:
                      Number(
                        event.target.value,
                      ),
                  },
                });
              }}
              type="number"
              value={
                draft.audit
                  .max_events
              }
            />
          </label>
        </div>

        <div className="settings-check-grid">
          <label>
            <input
              checked={
                draft.audit.enabled
              }
              onChange={(event) => {
                setDraft({
                  ...draft,
                  audit: {
                    ...draft.audit,
                    enabled:
                      event.target.checked,
                  },
                });
              }}
              type="checkbox"
            />

            <span>
              Enable local audit logging
            </span>
          </label>
        </div>
      </section>

      <section className="settings-save-bar">
        <span>
          {dirty
            ? "Unsaved application settings"
            : "Settings match the persisted configuration"}
        </span>

        <button
          className="settings-button settings-button-primary"
          disabled={
            !dirty ||
            busy
          }
          onClick={() => {
            saveMutation.mutate(
              draft,
            );
          }}
          type="button"
        >
          {saveMutation.isPending ? (
            <LoaderCircle
              aria-hidden="true"
              className="settings-spinner"
              size={17}
            />
          ) : (
            <Save
              aria-hidden="true"
              size={17}
            />
          )}

          Save settings
        </button>
      </section>

      <section className="settings-card">
        <header>
          <Search
            aria-hidden="true"
            size={21}
          />

          <div>
            <span className="settings-section-label">
              Target inspector
            </span>

            <h3>
              Resolve and classify a target
            </h3>

            <p>
              This inspection does not send an
              HTTP request to the target.
            </p>
          </div>
        </header>

        <label className="settings-target-field">
          <span>
            Target URL
          </span>

          <div>
            <input
              onChange={(event) => {
                setTargetUrl(
                  event.target.value,
                );
              }}
              type="url"
              value={targetUrl}
            />

            <button
              className="settings-button settings-button-secondary"
              disabled={
                !targetUrl.trim() ||
                targetMutation.isPending
              }
              onClick={() => {
                targetMutation.mutate();
              }}
              type="button"
            >
              {targetMutation.isPending ? (
                <LoaderCircle
                  aria-hidden="true"
                  className="settings-spinner"
                  size={17}
                />
              ) : (
                <Search
                  aria-hidden="true"
                  size={17}
                />
              )}

              Inspect target
            </button>
          </div>
        </label>

        {targetMutation.data ? (
          <section
            className={
              targetMutation.data.permitted
                ? "settings-target-result settings-target-result-allowed"
                : "settings-target-result settings-target-result-denied"
            }
          >
            <header>
              {targetMutation.data.permitted ? (
                <ShieldCheck
                  aria-hidden="true"
                  size={23}
                />
              ) : (
                <ShieldAlert
                  aria-hidden="true"
                  size={23}
                />
              )}

              <div>
                <strong>
                  {targetMutation.data.permitted
                    ? "Target is permitted"
                    : "Target is not permitted"}
                </strong>

                <span>
                  {targetMutation.data.hostname}
                  {":"}
                  {targetMutation.data.port}
                </span>
              </div>
            </header>

            <div className="settings-address-grid">
              {targetMutation.data.addresses.map(
                (address) => (
                  <article
                    key={
                      address.address
                    }
                  >
                    <code>
                      {address.address}
                    </code>

                    <span>
                      {address.classification
                        .replaceAll(
                          "_",
                          " ",
                        )}
                    </span>

                    <strong>
                      {address.permitted
                        ? "Allowed"
                        : "Blocked"}
                    </strong>
                  </article>
                ),
              )}
            </div>

            {[
              ...targetMutation.data.issues,
              ...targetMutation.data
                .policy_violations,
            ].length > 0 ? (
              <ul>
                {[
                  ...targetMutation.data.issues,
                  ...targetMutation.data
                    .policy_violations,
                ].map(
                  (issue) => (
                    <li key={issue}>
                      {issue}
                    </li>
                  ),
                )}
              </ul>
            ) : null}
          </section>
        ) : null}
      </section>

      <section className="settings-card settings-audit-card">
        <header>
          <History
            aria-hidden="true"
            size={21}
          />

          <div>
            <span className="settings-section-label">
              Recent local activity
            </span>

            <h3>
              Audit events
            </h3>
          </div>
        </header>

        {auditEvents.length === 0 ? (
          <section className="settings-empty">
            No audit events have been recorded.
          </section>
        ) : (
          <div className="settings-audit-list">
            {auditEvents.map(
              (event) => (
                <article
                  key={event.event_id}
                >
                  <header>
                    <div>
                      <code>
                        {event.event_type}
                      </code>

                      <strong>
                        {event.message}
                      </strong>
                    </div>

                    <span
                      className={auditOutcomeClass(
                        event,
                      )}
                    >
                      {event.outcome}
                    </span>
                  </header>

                  <footer>
                    <span>
                      {formatDate(
                        event.occurred_at,
                      )}
                    </span>

                    <span>
                      {event.actor}
                    </span>
                  </footer>
                </article>
              ),
            )}
          </div>
        )}
      </section>

      <section className="settings-reset-card">
        <header>
          <RotateCcw
            aria-hidden="true"
            size={21}
          />

          <div>
            <span className="settings-section-label">
              Destructive configuration action
            </span>

            <h3>
              Reset application settings
            </h3>

            <p>
              This replaces the persistent
              configuration with secure defaults.
              Projects, scans, findings, and
              reports are not deleted.
            </p>
          </div>
        </header>

        <label className="settings-reset-field">
          <span>
            Exact confirmation phrase
          </span>

          <code>
            {RESET_CONFIRMATION}
          </code>

          <input
            autoComplete="off"
            onChange={(event) => {
              setResetConfirmation(
                event.target.value,
              );
            }}
            type="text"
            value={
              resetConfirmation
            }
          />
        </label>

        <button
          className="settings-button settings-button-danger"
          disabled={!canReset}
          onClick={() => {
            resetMutation.mutate();
          }}
          type="button"
        >
          {resetMutation.isPending ? (
            <LoaderCircle
              aria-hidden="true"
              className="settings-spinner"
              size={17}
            />
          ) : (
            <RotateCcw
              aria-hidden="true"
              size={17}
            />
          )}

          Reset settings
        </button>
      </section>
    </div>
  );
}