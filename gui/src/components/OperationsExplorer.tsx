import {
  Braces,
  ChevronDown,
  ChevronUp,
  Hash,
  KeyRound,
  Search,
  ShieldCheck,
  ShieldOff,
  Tags,
} from "lucide-react";
import {
  useMemo,
  useState,
} from "react";

import type {
  OpenAPIOperation,
} from "../api/operations";

type SecurityFilter =
  | "all"
  | "secured"
  | "public";

interface OperationsExplorerProps {
  operations: OpenAPIOperation[];
}

function getMethodClass(
  method: string,
): string {
  return [
    "workspace-method",
    `workspace-method-${method.toLowerCase()}`,
  ].join(" ");
}

function matchesSearch(
  operation: OpenAPIOperation,
  searchTerm: string,
): boolean {
  if (!searchTerm) {
    return true;
  }

  const searchableValues = [
    operation.method,
    operation.path,
    operation.operation_id,
    operation.summary ?? "",
    operation.description ?? "",
    ...operation.tags,
  ];

  return searchableValues.some((value) =>
    value.toLowerCase().includes(
      searchTerm,
    ),
  );
}

interface OperationCardProps {
  expanded: boolean;
  operation: OpenAPIOperation;
  onToggle: () => void;
}

function OperationCard({
  expanded,
  operation,
  onToggle,
}: OperationCardProps) {
  return (
    <article className="operation-card">
      <button
        aria-expanded={expanded}
        className="operation-card-summary"
        onClick={onToggle}
        type="button"
      >
        <span
          className={getMethodClass(
            operation.method,
          )}
        >
          {operation.method}
        </span>

        <div className="operation-primary">
          <code>
            {operation.path}
          </code>

          <span>
            {operation.summary ??
              operation.operation_id}
          </span>
        </div>

        <div className="operation-indicators">
          {operation.deprecated ? (
            <span className="operation-deprecated">
              Deprecated
            </span>
          ) : null}

          <span
            className={
              operation.security_required
                ? "operation-security operation-security-secured"
                : "operation-security operation-security-public"
            }
          >
            {operation.security_required ? (
              <ShieldCheck
                aria-hidden="true"
                size={15}
              />
            ) : (
              <ShieldOff
                aria-hidden="true"
                size={15}
              />
            )}

            {operation.security_required
              ? "Secured"
              : "Public"}
          </span>

          {expanded ? (
            <ChevronUp
              aria-hidden="true"
              size={19}
            />
          ) : (
            <ChevronDown
              aria-hidden="true"
              size={19}
            />
          )}
        </div>
      </button>

      {expanded ? (
        <div className="operation-details">
          <section className="operation-detail-grid">
            <div className="operation-detail-item">
              <span>
                <Hash
                  aria-hidden="true"
                  size={15}
                />

                Operation ID
              </span>

              <code>
                {operation.operation_id}
              </code>
            </div>

            <div className="operation-detail-item">
              <span>
                <KeyRound
                  aria-hidden="true"
                  size={15}
                />

                Authorization
              </span>

              <strong>
                {operation.security_required
                  ? "Authentication required"
                  : "No OpenAPI security requirement"}
              </strong>
            </div>

            <div className="operation-detail-item">
              <span>
                <Braces
                  aria-hidden="true"
                  size={15}
                />

                Request content
              </span>

              <strong>
                {operation.request_content_types
                  .length > 0
                  ? operation.request_content_types.join(
                      ", ",
                    )
                  : "No request body"}
              </strong>
            </div>

            <div className="operation-detail-item">
              <span>
                <Tags
                  aria-hidden="true"
                  size={15}
                />

                Tags
              </span>

              <strong>
                {operation.tags.length > 0
                  ? operation.tags.join(", ")
                  : "No tags"}
              </strong>
            </div>
          </section>

          {operation.description ? (
            <section className="operation-description">
              <h4>
                Description
              </h4>

              <p>
                {operation.description}
              </p>
            </section>
          ) : null}

          <section className="operation-detail-section">
            <div className="operation-section-heading">
              <div>
                <span className="workspace-section-label">
                  Request structure
                </span>

                <h4>
                  Parameters
                </h4>
              </div>

              <span className="operation-count-badge">
                {operation.parameters.length}
              </span>
            </div>

            {operation.parameters.length === 0 ? (
              <div className="operation-empty-detail">
                No path, query, header, or
                cookie parameters are documented.
              </div>
            ) : (
              <div className="parameter-table-wrapper">
                <table className="parameter-table">
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Location</th>
                      <th>Type</th>
                      <th>Required</th>
                      <th>Description</th>
                    </tr>
                  </thead>

                  <tbody>
                    {operation.parameters.map(
                      (parameter) => (
                        <tr
                          key={`${parameter.location}:${parameter.name}`}
                        >
                          <td>
                            <code>
                              {parameter.name}
                            </code>
                          </td>

                          <td>
                            <span className="parameter-location">
                              {parameter.location}
                            </span>
                          </td>

                          <td>
                            {parameter.schema_type ??
                              "Unknown"}
                          </td>

                          <td>
                            {parameter.required
                              ? "Yes"
                              : "No"}
                          </td>

                          <td>
                            {parameter.description ??
                              "No description"}
                          </td>
                        </tr>
                      ),
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section className="operation-response-section">
            <div>
              <span className="workspace-section-label">
                Documented responses
              </span>

              <h4>
                Response codes
              </h4>
            </div>

            <div className="response-code-list">
              {operation.response_codes
                .length > 0 ? (
                operation.response_codes.map(
                  (responseCode) => (
                    <span
                      className="response-code"
                      key={responseCode}
                    >
                      {responseCode}
                    </span>
                  ),
                )
              ) : (
                <span className="operation-empty-detail">
                  No responses documented
                </span>
              )}
            </div>
          </section>
        </div>
      ) : null}
    </article>
  );
}

export function OperationsExplorer({
  operations,
}: OperationsExplorerProps) {
  const [
    searchValue,
    setSearchValue,
  ] = useState("");

  const [
    methodFilter,
    setMethodFilter,
  ] = useState("ALL");

  const [
    securityFilter,
    setSecurityFilter,
  ] = useState<SecurityFilter>("all");

  const [
    expandedOperations,
    setExpandedOperations,
  ] = useState<Set<string>>(
    () => new Set(),
  );

  const methodOptions = useMemo(
    () =>
      Array.from(
        new Set(
          operations.map(
            (operation) =>
              operation.method,
          ),
        ),
      ).sort(),
    [operations],
  );

  const filteredOperations =
    useMemo(() => {
      const normalizedSearch =
        searchValue
          .trim()
          .toLowerCase();

      return operations.filter(
        (operation) => {
          const methodMatches =
            methodFilter === "ALL" ||
            operation.method ===
              methodFilter;

          const securityMatches =
            securityFilter === "all" ||
            (
              securityFilter ===
                "secured" &&
              operation.security_required
            ) ||
            (
              securityFilter ===
                "public" &&
              !operation.security_required
            );

          return (
            methodMatches &&
            securityMatches &&
            matchesSearch(
              operation,
              normalizedSearch,
            )
          );
        },
      );
    }, [
      methodFilter,
      operations,
      searchValue,
      securityFilter,
    ]);

  function toggleOperation(
    operationKey: string,
  ): void {
    setExpandedOperations(
      (current) => {
        const updated =
          new Set(current);

        if (updated.has(operationKey)) {
          updated.delete(operationKey);
        } else {
          updated.add(operationKey);
        }

        return updated;
      },
    );
  }

  return (
    <section className="operations-panel">
      <header className="operations-panel-heading">
        <div>
          <span className="workspace-section-label">
            API surface
          </span>

          <h3>
            Operations explorer
          </h3>

          <p>
            Search and inspect the operations
            discovered from the imported
            OpenAPI document.
          </p>
        </div>

        <span className="operations-result-count">
          {filteredOperations.length} of{" "}
          {operations.length}
        </span>
      </header>

      <div className="operations-controls">
        <label className="operations-search">
          <Search
            aria-hidden="true"
            size={18}
          />

          <input
            onChange={(event) => {
              setSearchValue(
                event.target.value,
              );
            }}
            placeholder="Search path, operation ID, summary, or tag"
            type="search"
            value={searchValue}
          />
        </label>

        <label className="operations-select">
          <span>
            Method
          </span>

          <select
            onChange={(event) => {
              setMethodFilter(
                event.target.value,
              );
            }}
            value={methodFilter}
          >
            <option value="ALL">
              All methods
            </option>

            {methodOptions.map(
              (method) => (
                <option
                  key={method}
                  value={method}
                >
                  {method}
                </option>
              ),
            )}
          </select>
        </label>

        <label className="operations-select">
          <span>
            Security
          </span>

          <select
            onChange={(event) => {
              setSecurityFilter(
                event.target
                  .value as SecurityFilter,
              );
            }}
            value={securityFilter}
          >
            <option value="all">
              All operations
            </option>

            <option value="secured">
              Secured only
            </option>

            <option value="public">
              Public only
            </option>
          </select>
        </label>
      </div>

      {filteredOperations.length === 0 ? (
        <section className="operations-empty-state">
          <Search
            aria-hidden="true"
            size={28}
          />

          <h4>
            No matching operations
          </h4>

          <p>
            Adjust the search term or filters
            to display more operations.
          </p>
        </section>
      ) : (
        <div className="operations-list">
          {filteredOperations.map(
            (operation) => (
              <OperationCard
                expanded={expandedOperations.has(
                  operation.key,
                )}
                key={operation.key}
                onToggle={() => {
                  toggleOperation(
                    operation.key,
                  );
                }}
                operation={operation}
              />
            ),
          )}
        </div>
      )}
    </section>
  );
}