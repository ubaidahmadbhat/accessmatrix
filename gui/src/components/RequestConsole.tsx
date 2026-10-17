import {
  useMutation,
  useQuery,
} from "@tanstack/react-query";
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  FileJson,
  Gauge,
  LoaderCircle,
  Play,
  RotateCcw,
  ShieldAlert,
  Terminal,
} from "lucide-react";
import type {
  FormEvent,
} from "react";
import {
  useMemo,
  useState,
} from "react";

import {
  executeOperation,
} from "../api/execution";
import type {
  ExecuteOperationInput,
  ExecuteOperationResult,
} from "../api/execution";
import {
  listIdentities,
} from "../api/identities";
import type {
  OpenAPIOperation,
  OperationParameter,
} from "../api/operations";
import {
  ApiRequestError,
} from "../api/projects";

import "./RequestConsole.css";

interface RequestConsoleProps {
  projectId: string;
  operations: OpenAPIOperation[];
}

const UNSAFE_METHODS = new Set([
  "POST",
  "PUT",
  "PATCH",
  "DELETE",
]);

const BLOCKED_METHODS = new Set([
  "TRACE",
]);

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

function parameterKey(
  parameter: OperationParameter,
): string {
  return [
    parameter.location,
    parameter.name,
  ].join(":");
}

function parseStringMap(
  value: string,
  label: string,
): Record<string, string> {
  const normalized = value.trim();

  if (!normalized) {
    return {};
  }

  let parsed: unknown;

  try {
    parsed = JSON.parse(
      normalized,
    );
  } catch {
    throw new Error(
      `${label} must contain valid JSON.`,
    );
  }

  if (
    typeof parsed !== "object" ||
    parsed === null ||
    Array.isArray(parsed)
  ) {
    throw new Error(
      `${label} must be a JSON object.`,
    );
  }

  const result: Record<
    string,
    string
  > = {};

  for (
    const [key, item]
    of Object.entries(parsed)
  ) {
    if (typeof item !== "string") {
      throw new Error(
        `${label} values must all be strings.`,
      );
    }

    result[key] = item;
  }

  return result;
}

function parseRequestBody(
  value: string,
): unknown | null {
  const normalized = value.trim();

  if (!normalized) {
    return null;
  }

  try {
    return JSON.parse(
      normalized,
    ) as unknown;
  } catch {
    throw new Error(
      "The request body must contain valid JSON.",
    );
  }
}

function formatResponseBody(
  bodyText: string | null,
): string {
  if (bodyText === null) {
    return (
      "The response does not contain "
      + "a displayable text body."
    );
  }

  try {
    const parsed =
      JSON.parse(
        bodyText,
      ) as unknown;

    return JSON.stringify(
      parsed,
      null,
      2,
    );
  } catch {
    return bodyText;
  }
}

function getStatusClass(
  statusCode: number,
): string {
  if (
    statusCode >= 200 &&
    statusCode < 300
  ) {
    return (
      "console-status "
      + "console-status-success"
    );
  }

  if (
    statusCode >= 300 &&
    statusCode < 400
  ) {
    return (
      "console-status "
      + "console-status-redirect"
    );
  }

  return (
    "console-status "
    + "console-status-error"
  );
}

function operationLabel(
  operation: OpenAPIOperation,
): string {
  return [
    operation.method,
    operation.path,
    "—",
    operation.summary ??
      operation.operation_id,
  ].join(" ");
}

interface ParameterFieldsProps {
  parameters: OperationParameter[];
  values: Record<string, string>;
  onChange: (
    parameter: OperationParameter,
    value: string,
  ) => void;
}

function ParameterFields({
  parameters,
  values,
  onChange,
}: ParameterFieldsProps) {
  if (parameters.length === 0) {
    return null;
  }

  return (
    <div className="console-parameter-grid">
      {parameters.map(
        (parameter) => (
          <label
            className="console-field"
            key={parameterKey(
              parameter,
            )}
          >
            <span>
              {parameter.name}

              {parameter.required ? (
                <strong
                  aria-label="required"
                >
                  *
                </strong>
              ) : null}
            </span>

            <small>
              {parameter.location}
              {" · "}
              {parameter.schema_type ??
                "unknown type"}
            </small>

            <input
              onChange={(event) => {
                onChange(
                  parameter,
                  event.target.value,
                );
              }}
              placeholder={
                parameter.description ??
                `Enter ${parameter.name}`
              }
              required={
                parameter.required
              }
              type="text"
              value={
                values[
                  parameterKey(
                    parameter,
                  )
                ] ?? ""
              }
            />
          </label>
        ),
      )}
    </div>
  );
}

interface ExecutionResultPanelProps {
  result: ExecuteOperationResult;
}

function ExecutionResultPanel({
  result,
}: ExecutionResultPanelProps) {
  const responseHeaderEntries =
    Object.entries(
      result.response_headers,
    );

  return (
    <section className="console-result">
      <header className="console-result-header">
        <div>
          <span className="console-section-label">
            Execution result
          </span>

          <h3>
            {result.method} request completed
          </h3>
        </div>

        <span
          className={getStatusClass(
            result.status_code,
          )}
        >
          {result.status_code}

          {result.reason_phrase
            ? ` ${result.reason_phrase}`
            : ""}
        </span>
      </header>

      <section className="console-result-stats">
        <article>
          <Clock
            aria-hidden="true"
            size={18}
          />

          <div>
            <span>
              Duration
            </span>

            <strong>
              {result.elapsed_ms} ms
            </strong>
          </div>
        </article>

        <article>
          <FileJson
            aria-hidden="true"
            size={18}
          />

          <div>
            <span>
              Captured
            </span>

            <strong>
              {result.body_bytes_captured}
              {" bytes"}
            </strong>
          </div>
        </article>

        <article>
          <Gauge
            aria-hidden="true"
            size={18}
          />

          <div>
            <span>
              Rate slots left
            </span>

            <strong>
              {
                result.rate_limit_remaining
              }
            </strong>
          </div>
        </article>
      </section>

      <section className="console-result-target">
        <span>
          Request target
        </span>

        <code>
          {result.request_url}
        </code>
      </section>

      <section className="console-result-target">
        <span>
          Request header names
        </span>

        <code>
          {result.request_header_names
            .length > 0
            ? result.request_header_names.join(
                ", ",
              )
            : "None"}
        </code>
      </section>

      {result.redirect_blocked ? (
        <section className="console-warning">
          <ShieldAlert
            aria-hidden="true"
            size={19}
          />

          <div>
            <strong>
              Redirect blocked
            </strong>

            <span>
              AccessMatrix returned the redirect
              response without following its
              target.
            </span>
          </div>
        </section>
      ) : null}

      {result.body_truncated ? (
        <section className="console-warning">
          <ShieldAlert
            aria-hidden="true"
            size={19}
          />

          <div>
            <strong>
              Response truncated
            </strong>

            <span>
              The response exceeded the configured
              capture limit.
            </span>
          </div>
        </section>
      ) : null}

      <section className="console-response-section">
        <div className="console-response-heading">
          <span className="console-section-label">
            Response metadata
          </span>

          <h4>
            Headers
          </h4>
        </div>

        {responseHeaderEntries.length ===
        0 ? (
          <div className="console-empty-detail">
            No response headers were captured.
          </div>
        ) : (
          <div className="console-header-table-wrapper">
            <table className="console-header-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Value</th>
                </tr>
              </thead>

              <tbody>
                {responseHeaderEntries.map(
                  ([
                    headerName,
                    headerValue,
                  ]) => (
                    <tr key={headerName}>
                      <td>
                        <code>
                          {headerName}
                        </code>
                      </td>

                      <td>
                        <code>
                          {headerValue}
                        </code>
                      </td>
                    </tr>
                  ),
                )}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="console-response-section">
        <div className="console-response-heading">
          <span className="console-section-label">
            Safe response capture
          </span>

          <h4>
            Body
          </h4>
        </div>

        <pre className="console-response-body">
          {formatResponseBody(
            result.body_text,
          )}
        </pre>
      </section>
    </section>
  );
}

export function RequestConsole({
  projectId,
  operations,
}: RequestConsoleProps) {
  const [
    selectedOperationKey,
    setSelectedOperationKey,
  ] = useState("");

  const [
    selectedIdentityId,
    setSelectedIdentityId,
  ] = useState("");

  const [
    parameterValues,
    setParameterValues,
  ] = useState<
    Record<string, string>
  >({});

  const [
    extraHeadersText,
    setExtraHeadersText,
  ] = useState("{}");

  const [
    requestBodyText,
    setRequestBodyText,
  ] = useState("");

  const [
    timeoutSeconds,
    setTimeoutSeconds,
  ] = useState(10);

  const [
    allowUnsafe,
    setAllowUnsafe,
  ] = useState(false);

  const [
    confirmation,
    setConfirmation,
  ] = useState("");

  const [
    formError,
    setFormError,
  ] = useState<string | null>(
    null,
  );

  const identitiesQuery = useQuery({
    queryKey: [
      "projects",
      projectId,
      "identities",
    ],
    queryFn: () =>
      listIdentities(projectId),
  });

  const executionMutation =
    useMutation({
      mutationFn: (
        input: ExecuteOperationInput,
      ) =>
        executeOperation(
          projectId,
          input,
        ),
    });

  const selectedOperation =
    useMemo(() => {
      return (
        operations.find(
          (operation) =>
            operation.key ===
            selectedOperationKey,
        ) ??
        operations[0] ??
        null
      );
    }, [
      operations,
      selectedOperationKey,
    ]);

  const identities =
    identitiesQuery.data ?? [];

  const selectedIdentity =
    identities.find(
      (identity) =>
        identity.id ===
        selectedIdentityId &&
        identity.enabled,
    ) ??
    identities.find(
      (identity) =>
        identity.enabled,
    ) ??
    null;

  const pathParameters =
    selectedOperation?.parameters.filter(
      (parameter) =>
        parameter.location === "path",
    ) ?? [];

  const queryParameters =
    selectedOperation?.parameters.filter(
      (parameter) =>
        parameter.location === "query",
    ) ?? [];

  const headerParameters =
    selectedOperation?.parameters.filter(
      (parameter) =>
        parameter.location === "header",
    ) ?? [];

  const cookieParameters =
    selectedOperation?.parameters.filter(
      (parameter) =>
        parameter.location === "cookie",
    ) ?? [];

  const method =
    selectedOperation?.method ?? "";

  const unsafeMethod =
    UNSAFE_METHODS.has(method);

  const blockedMethod =
    BLOCKED_METHODS.has(method);

  const supportsBody = [
    "POST",
    "PUT",
    "PATCH",
  ].includes(method);

  const expectedConfirmation =
    selectedOperation
      ? [
          "EXECUTE",
          selectedOperation.method,
          selectedOperation.path,
        ].join(" ")
      : "";

  const requiredParametersReady =
    selectedOperation
      ? selectedOperation.parameters
          .filter(
            (parameter) =>
              parameter.required &&
              [
                "path",
                "query",
                "header",
              ].includes(
                parameter.location,
              ),
          )
          .every((parameter) =>
            Boolean(
              parameterValues[
                parameterKey(
                  parameter,
                )
              ]?.trim(),
            ),
          )
      : false;

  const confirmationReady =
    !unsafeMethod ||
    (
      allowUnsafe &&
      confirmation.trim() ===
        expectedConfirmation
    );

  const canExecute =
    selectedOperation !== null &&
    selectedIdentity !== null &&
    requiredParametersReady &&
    confirmationReady &&
    !blockedMethod &&
    !executionMutation.isPending;

  function changeOperation(
    operationKeyValue: string,
  ): void {
    setSelectedOperationKey(
      operationKeyValue,
    );

    setParameterValues({});
    setRequestBodyText("");
    setAllowUnsafe(false);
    setConfirmation("");
    setFormError(null);
    executionMutation.reset();
  }

  function changeParameter(
    parameter: OperationParameter,
    value: string,
  ): void {
    setParameterValues(
      (current) => ({
        ...current,
        [
          parameterKey(parameter)
        ]: value,
      }),
    );
  }

  function resetConsole(): void {
    setSelectedOperationKey("");
    setSelectedIdentityId("");
    setParameterValues({});
    setExtraHeadersText("{}");
    setRequestBodyText("");
    setTimeoutSeconds(10);
    setAllowUnsafe(false);
    setConfirmation("");
    setFormError(null);
    executionMutation.reset();
  }

  function submitExecution(
    event: FormEvent<HTMLFormElement>,
  ): void {
    event.preventDefault();

    setFormError(null);

    if (
      selectedOperation === null ||
      selectedIdentity === null
    ) {
      setFormError(
        "Select an operation and an enabled identity.",
      );

      return;
    }

    try {
      const resolvedPathParameters:
        Record<string, string> = {};

      const resolvedQueryParameters:
        Record<string, string> = {};

      const resolvedHeaders:
        Record<string, string> =
          parseStringMap(
            extraHeadersText,
            "Additional headers",
          );

      for (
        const parameter
        of selectedOperation.parameters
      ) {
        const value =
          parameterValues[
            parameterKey(parameter)
          ]?.trim() ?? "";

        if (
          parameter.required &&
          [
            "path",
            "query",
            "header",
          ].includes(
            parameter.location,
          ) &&
          !value
        ) {
          throw new Error(
            `Parameter ${parameter.name} is required.`,
          );
        }

        if (!value) {
          continue;
        }

        if (
          parameter.location === "path"
        ) {
          resolvedPathParameters[
            parameter.name
          ] = value;
        } else if (
          parameter.location === "query"
        ) {
          resolvedQueryParameters[
            parameter.name
          ] = value;
        } else if (
          parameter.location === "header"
        ) {
          if (
            parameter.name
            in resolvedHeaders
          ) {
            throw new Error(
              `Header ${parameter.name} is configured more than once.`,
            );
          }

          resolvedHeaders[
            parameter.name
          ] = value;
        }
      }

      const jsonBody =
        parseRequestBody(
          requestBodyText,
        );

      executionMutation.mutate({
        operation_key:
          selectedOperation.key,
        identity_id:
          selectedIdentity.id,
        path_parameters:
          resolvedPathParameters,
        query_parameters:
          resolvedQueryParameters,
        headers: resolvedHeaders,
        json_body: jsonBody,
        timeout_seconds:
          timeoutSeconds,
        allow_unsafe:
          unsafeMethod
            ? allowUnsafe
            : false,
        confirmation:
          unsafeMethod
            ? confirmation.trim()
            : null,
      });
    } catch (error) {
      setFormError(
        getErrorMessage(error),
      );
    }
  }

  if (operations.length === 0) {
    return (
      <section className="console-panel">
        <section className="console-empty-state">
          <Terminal
            aria-hidden="true"
            size={31}
          />

          <h3>
            No operations available
          </h3>

          <p>
            Import an OpenAPI document before
            using the request console.
          </p>
        </section>
      </section>
    );
  }

  return (
    <section className="console-panel">
      <header className="console-header">
        <div>
          <span className="console-section-label">
            Controlled execution
          </span>

          <h3>
            Request console
          </h3>

          <p>
            Execute imported OpenAPI operations
            through AccessMatrix safety controls.
            Credential values remain server-side.
          </p>
        </div>

        <button
          className="console-button console-button-secondary"
          onClick={resetConsole}
          type="button"
        >
          <RotateCcw
            aria-hidden="true"
            size={17}
          />

          Reset console
        </button>
      </header>

      {identitiesQuery.error ? (
        <section
          className="console-alert"
          role="alert"
        >
          <AlertCircle
            aria-hidden="true"
            size={20}
          />

          <div>
            <strong>
              Identities could not be loaded.
            </strong>

            <span>
              {getErrorMessage(
                identitiesQuery.error,
              )}
            </span>
          </div>
        </section>
      ) : null}

      {formError ? (
        <section
          className="console-alert"
          role="alert"
        >
          <AlertCircle
            aria-hidden="true"
            size={20}
          />

          <div>
            <strong>
              Request configuration is invalid.
            </strong>

            <span>
              {formError}
            </span>
          </div>
        </section>
      ) : null}

      {executionMutation.error ? (
        <section
          className="console-alert"
          role="alert"
        >
          <AlertCircle
            aria-hidden="true"
            size={20}
          />

          <div>
            <strong>
              Request execution failed.
            </strong>

            <span>
              {getErrorMessage(
                executionMutation.error,
              )}
            </span>
          </div>
        </section>
      ) : null}

      <form
        className="console-form"
        onSubmit={submitExecution}
      >
        <section className="console-form-section">
          <div className="console-form-heading">
            <span className="console-section-label">
              Selection
            </span>

            <h4>
              Operation and identity
            </h4>
          </div>

          <div className="console-two-column-grid">
            <label className="console-field">
              <span>
                OpenAPI operation
              </span>

              <select
                onChange={(event) => {
                  changeOperation(
                    event.target.value,
                  );
                }}
                value={
                  selectedOperation?.key ??
                  ""
                }
              >
                {operations.map(
                  (operation) => (
                    <option
                      key={operation.key}
                      value={operation.key}
                    >
                      {operationLabel(
                        operation,
                      )}
                    </option>
                  ),
                )}
              </select>
            </label>

            <label className="console-field">
              <span>
                Execution identity
              </span>

              <select
                disabled={
                  identitiesQuery.isPending
                }
                onChange={(event) => {
                  setSelectedIdentityId(
                    event.target.value,
                  );

                  executionMutation.reset();
                }}
                value={
                  selectedIdentity?.id ??
                  ""
                }
              >
                {identities.length ===
                0 ? (
                  <option value="">
                    No identities available
                  </option>
                ) : (
                  identities.map(
                    (identity) => (
                      <option
                        disabled={
                          !identity.enabled
                        }
                        key={identity.id}
                        value={identity.id}
                      >
                        {identity.name}
                        {" — "}
                        {identity.role}
                        {!identity.enabled
                          ? " (disabled)"
                          : ""}
                      </option>
                    ),
                  )
                )}
              </select>
            </label>
          </div>

          {selectedOperation ? (
            <div className="console-operation-summary">
              <span
                className={`console-method console-method-${selectedOperation.method.toLowerCase()}`}
              >
                {selectedOperation.method}
              </span>

              <code>
                {selectedOperation.path}
              </code>

              <span>
                {selectedOperation.summary ??
                  selectedOperation.operation_id}
              </span>
            </div>
          ) : null}
        </section>

        {pathParameters.length > 0 ? (
          <section className="console-form-section">
            <div className="console-form-heading">
              <span className="console-section-label">
                URL construction
              </span>

              <h4>
                Path parameters
              </h4>
            </div>

            <ParameterFields
              onChange={changeParameter}
              parameters={
                pathParameters
              }
              values={parameterValues}
            />
          </section>
        ) : null}

        {queryParameters.length > 0 ? (
          <section className="console-form-section">
            <div className="console-form-heading">
              <span className="console-section-label">
                Request parameters
              </span>

              <h4>
                Query parameters
              </h4>
            </div>

            <ParameterFields
              onChange={changeParameter}
              parameters={
                queryParameters
              }
              values={parameterValues}
            />
          </section>
        ) : null}

        {headerParameters.length > 0 ? (
          <section className="console-form-section">
            <div className="console-form-heading">
              <span className="console-section-label">
                Documented metadata
              </span>

              <h4>
                Header parameters
              </h4>
            </div>

            <ParameterFields
              onChange={changeParameter}
              parameters={
                headerParameters
              }
              values={parameterValues}
            />
          </section>
        ) : null}

        {cookieParameters.length > 0 ? (
          <section className="console-warning">
            <ShieldAlert
              aria-hidden="true"
              size={19}
            />

            <div>
              <strong>
                Manual cookies are unavailable
              </strong>

              <span>
                Cookie authentication must be
                configured through an identity
                profile rather than entered in
                the console.
              </span>
            </div>
          </section>
        ) : null}

        <section className="console-form-section">
          <div className="console-form-heading">
            <span className="console-section-label">
              Optional metadata
            </span>

            <h4>
              Additional headers
            </h4>

            <p>
              Use a JSON object containing string
              values. Authorization, Cookie, Host
              and other managed headers are blocked.
            </p>
          </div>

          <label className="console-field">
            <span>
              Header JSON
            </span>

            <textarea
              onChange={(event) => {
                setExtraHeadersText(
                  event.target.value,
                );
              }}
              rows={5}
              spellCheck={false}
              value={extraHeadersText}
            />
          </label>
        </section>

        {supportsBody ? (
          <section className="console-form-section">
            <div className="console-form-heading">
              <span className="console-section-label">
                Request payload
              </span>

              <h4>
                JSON body
              </h4>

              <p>
                Leave this field empty when the
                selected operation does not require
                a request body.
              </p>
            </div>

            <label className="console-field">
              <span>
                Request JSON
              </span>

              <textarea
                onChange={(event) => {
                  setRequestBodyText(
                    event.target.value,
                  );
                }}
                placeholder={
                  '{\n  "amount": 125.50,\n  "currency": "USD",\n  "description": "Console test invoice"\n}'
                }
                rows={10}
                spellCheck={false}
                value={requestBodyText}
              />
            </label>
          </section>
        ) : null}

        <section className="console-form-section">
          <div className="console-form-heading">
            <span className="console-section-label">
              Execution controls
            </span>

            <h4>
              Safety and timeout
            </h4>
          </div>

          <label className="console-field console-timeout-field">
            <span>
              Timeout in seconds
            </span>

            <input
              max={30}
              min={1}
              onChange={(event) => {
                setTimeoutSeconds(
                  Number(
                    event.target.value,
                  ),
                );
              }}
              type="number"
              value={timeoutSeconds}
            />
          </label>

          {blockedMethod ? (
            <section className="console-danger">
              <ShieldAlert
                aria-hidden="true"
                size={20}
              />

              <div>
                <strong>
                  Method completely blocked
                </strong>

                <span>
                  TRACE cannot be executed by the
                  AccessMatrix controlled executor.
                </span>
              </div>
            </section>
          ) : null}

          {unsafeMethod ? (
            <div className="console-unsafe-controls">
              <section className="console-danger">
                <ShieldAlert
                  aria-hidden="true"
                  size={20}
                />

                <div>
                  <strong>
                    Unsafe HTTP method
                  </strong>

                  <span>
                    This operation may create,
                    modify, or delete target data.
                  </span>
                </div>
              </section>

              <label className="console-checkbox-field">
                <input
                  checked={allowUnsafe}
                  onChange={(event) => {
                    setAllowUnsafe(
                      event.target.checked,
                    );
                  }}
                  type="checkbox"
                />

                <span>
                  <strong>
                    Permit this unsafe execution
                  </strong>

                  <small>
                    This confirmation applies only
                    to the current request.
                  </small>
                </span>
              </label>

              <label className="console-field">
                <span>
                  Exact confirmation phrase
                </span>

                <code className="console-confirmation-example">
                  {expectedConfirmation}
                </code>

                <input
                  autoComplete="off"
                  onChange={(event) => {
                    setConfirmation(
                      event.target.value,
                    );
                  }}
                  placeholder={
                    expectedConfirmation
                  }
                  type="text"
                  value={confirmation}
                />
              </label>
            </div>
          ) : null}
        </section>

        <footer className="console-form-actions">
          <div>
            {selectedIdentity ? (
              <>
                <CheckCircle2
                  aria-hidden="true"
                  size={17}
                />

                Executing as{" "}
                <strong>
                  {selectedIdentity.name}
                </strong>
              </>
            ) : (
              <>
                <AlertCircle
                  aria-hidden="true"
                  size={17}
                />

                No enabled identity selected
              </>
            )}
          </div>

          <button
            className="console-button console-button-primary"
            disabled={!canExecute}
            type="submit"
          >
            {executionMutation.isPending ? (
              <>
                <LoaderCircle
                  aria-hidden="true"
                  className="console-spinner"
                  size={17}
                />

                Executing request
              </>
            ) : (
              <>
                <Play
                  aria-hidden="true"
                  size={17}
                />

                Execute operation
              </>
            )}
          </button>
        </footer>
      </form>

      {executionMutation.data ? (
        <ExecutionResultPanel
          result={
            executionMutation.data
          }
        />
      ) : null}
    </section>
  );
}