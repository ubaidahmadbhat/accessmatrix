import {
  useQuery,
} from "@tanstack/react-query";
import {
  AlertCircle,
  CheckCircle2,
  EyeOff,
  KeyRound,
  LoaderCircle,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  ShieldOff,
} from "lucide-react";

import type {
  AuthType,
  IdentityCredentialStatus,
} from "../api/identities";
import {
  getProjectCredentialStatuses,
} from "../api/identities";
import {
  ApiRequestError,
} from "../api/projects";

import "./IdentityReadinessPanel.css";

interface IdentityReadinessPanelProps {
  projectId: string;
}

const AUTH_TYPE_LABELS: Record<
  AuthType,
  string
> = {
  none: "No authentication",
  bearer: "Bearer token",
  api_key: "API key",
  basic: "HTTP Basic",
  cookie: "Cookie",
  custom_header: "Custom header",
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

function getStatusClass(
  credentialStatus: IdentityCredentialStatus,
): string {
  if (!credentialStatus.enabled) {
    return (
      "readiness-status "
      + "readiness-status-disabled"
    );
  }

  if (credentialStatus.ready) {
    return (
      "readiness-status "
      + "readiness-status-ready"
    );
  }

  return (
    "readiness-status "
    + "readiness-status-unavailable"
  );
}

function getCardClass(
  credentialStatus: IdentityCredentialStatus,
): string {
  if (!credentialStatus.enabled) {
    return (
      "readiness-card "
      + "readiness-card-disabled"
    );
  }

  if (credentialStatus.ready) {
    return (
      "readiness-card "
      + "readiness-card-ready"
    );
  }

  return (
    "readiness-card "
    + "readiness-card-unavailable"
  );
}

function StatusIcon({
  credentialStatus,
}: {
  credentialStatus: IdentityCredentialStatus;
}) {
  if (!credentialStatus.enabled) {
    return (
      <ShieldOff
        aria-hidden="true"
        size={21}
      />
    );
  }

  if (credentialStatus.ready) {
    return (
      <ShieldCheck
        aria-hidden="true"
        size={21}
      />
    );
  }

  return (
    <ShieldAlert
      aria-hidden="true"
      size={21}
    />
  );
}

function getStatusLabel(
  credentialStatus: IdentityCredentialStatus,
): string {
  if (!credentialStatus.enabled) {
    return "Disabled";
  }

  if (credentialStatus.ready) {
    return "Ready";
  }

  return "Unavailable";
}

export function IdentityReadinessPanel({
  projectId,
}: IdentityReadinessPanelProps) {
  const readinessQuery = useQuery({
    queryKey: [
      "projects",
      projectId,
      "credential-statuses",
    ],

    queryFn: () =>
      getProjectCredentialStatuses(
        projectId,
      ),
  });

  const readiness =
    readinessQuery.data;

  const statuses =
    readiness?.statuses ?? [];

  return (
    <section className="readiness-panel">
      <header className="readiness-header">
        <div>
          <span className="readiness-section-label">
            Secret resolution
          </span>

          <h3>
            Credential readiness
          </h3>

          <p>
            Verify that identity credential
            references can be resolved before
            executing authorization tests.
            Resolved secret values are never
            returned by this endpoint.
          </p>
        </div>

        <button
          className="readiness-button"
          disabled={
            readinessQuery.isFetching
          }
          onClick={() => {
            void readinessQuery.refetch();
          }}
          type="button"
        >
          <RefreshCw
            aria-hidden="true"
            className={
              readinessQuery.isFetching
                ? "readiness-spinner"
                : undefined
            }
            size={17}
          />

          Recheck credentials
        </button>
      </header>

      {readinessQuery.error ? (
        <section
          className="readiness-alert"
          role="alert"
        >
          <AlertCircle
            aria-hidden="true"
            size={21}
          />

          <div>
            <strong>
              Credential readiness could not
              be checked.
            </strong>

            <span>
              {getErrorMessage(
                readinessQuery.error,
              )}
            </span>
          </div>
        </section>
      ) : null}

      {readinessQuery.isPending ? (
        <section className="readiness-loading">
          <LoaderCircle
            aria-hidden="true"
            className="readiness-spinner"
            size={29}
          />

          <strong>
            Checking credential references
          </strong>
        </section>
      ) : null}

      {!readinessQuery.isPending &&
      !readinessQuery.error ? (
        <>
          <section className="readiness-stat-grid">
            <article>
              <KeyRound
                aria-hidden="true"
                size={20}
              />

              <div>
                <span>
                  Total identities
                </span>

                <strong>
                  {readiness?.total_count ?? 0}
                </strong>
              </div>
            </article>

            <article className="readiness-stat-ready">
              <CheckCircle2
                aria-hidden="true"
                size={20}
              />

              <div>
                <span>
                  Ready
                </span>

                <strong>
                  {readiness?.ready_count ?? 0}
                </strong>
              </div>
            </article>

            <article className="readiness-stat-unavailable">
              <ShieldAlert
                aria-hidden="true"
                size={20}
              />

              <div>
                <span>
                  Not ready
                </span>

                <strong>
                  {readiness?.unready_count ?? 0}
                </strong>
              </div>
            </article>

            <article className="readiness-stat-disabled">
              <EyeOff
                aria-hidden="true"
                size={20}
              />

              <div>
                <span>
                  Disabled
                </span>

                <strong>
                  {readiness?.disabled_count ?? 0}
                </strong>
              </div>
            </article>
          </section>

          {statuses.length === 0 ? (
            <section className="readiness-empty">
              <KeyRound
                aria-hidden="true"
                size={30}
              />

              <h4>
                No identities configured
              </h4>

              <p>
                Create identities before
                checking credential readiness.
              </p>
            </section>
          ) : (
            <section className="readiness-grid">
              {statuses.map(
                (credentialStatus) => (
                  <article
                    className={getCardClass(
                      credentialStatus,
                    )}
                    key={
                      credentialStatus.identity_id
                    }
                  >
                    <header className="readiness-card-header">
                      <div className="readiness-card-title">
                        <div className="readiness-card-icon">
                          <StatusIcon
                            credentialStatus={
                              credentialStatus
                            }
                          />
                        </div>

                        <div>
                          <h4>
                            {
                              credentialStatus
                                .identity_name
                            }
                          </h4>

                          <span>
                            {
                              credentialStatus
                                .role
                            }
                          </span>
                        </div>
                      </div>

                      <span
                        className={getStatusClass(
                          credentialStatus,
                        )}
                      >
                        {getStatusLabel(
                          credentialStatus,
                        )}
                      </span>
                    </header>

                    <dl className="readiness-metadata">
                      <div>
                        <dt>
                          Authentication
                        </dt>

                        <dd>
                          {
                            AUTH_TYPE_LABELS[
                              credentialStatus
                                .auth_type
                            ]
                          }
                        </dd>
                      </div>

                      <div>
                        <dt>
                          Secret source
                        </dt>

                        <dd>
                          {credentialStatus
                            .auth_type ===
                          "none"
                            ? "Not applicable"
                            : credentialStatus
                                .secret_source}
                        </dd>
                      </div>
                    </dl>

                    <div className="readiness-message">
                      {credentialStatus.message}
                    </div>

                    {credentialStatus.references
                      .length > 0 ? (
                      <div className="readiness-references">
                        {credentialStatus.references.map(
                          (reference) => (
                            <div
                              className="readiness-reference"
                              key={
                                reference.field_name
                              }
                            >
                              <div>
                                <span>
                                  {
                                    reference.field_name
                                  }
                                </span>

                                <code>
                                  {reference.reference ??
                                    "Not configured"}
                                </code>
                              </div>

                              <span
                                className={
                                  reference.available
                                    ? "readiness-reference-available"
                                    : "readiness-reference-missing"
                                }
                              >
                                {reference.available
                                  ? "Available"
                                  : "Missing"}
                              </span>
                            </div>
                          ),
                        )}
                      </div>
                    ) : (
                      <div className="readiness-no-reference">
                        No credential reference
                        is required.
                      </div>
                    )}
                  </article>
                ),
              )}
            </section>
          )}
        </>
      ) : null}
    </section>
  );
}