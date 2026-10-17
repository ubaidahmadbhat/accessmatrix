import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  AlertCircle,
  CheckCircle2,
  Database,
  FileJson2,
  LoaderCircle,
  RefreshCw,
  Save,
  ShieldAlert,
  Sparkles,
  TestTube2,
} from "lucide-react";
import {
  useEffect,
  useState,
} from "react";

import type {
  AuthorizationDataset,
  AuthorizationDatasetValidation,
  BOLATestPlanItem,
} from "../api/authorization";
import {
  getAuthorizationDataset,
  getBOLATestPlan,
  saveAuthorizationDataset,
  seedDemoAuthorizationDataset,
  validateAuthorizationDataset,
} from "../api/authorization";
import {
  ApiRequestError,
} from "../api/projects";

import "./AuthorizationDatasetPanel.css";

interface AuthorizationDatasetPanelProps {
  projectId: string;
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

function formatDataset(
  dataset: AuthorizationDataset,
): string {
  return JSON.stringify(
    dataset,
    null,
    2,
  );
}

function parseDataset(
  value: string,
): AuthorizationDataset {
  let parsed: unknown;

  try {
    parsed = JSON.parse(
      value,
    ) as unknown;
  } catch {
    throw new Error(
      "The authorization dataset must contain valid JSON.",
    );
  }

  if (
    typeof parsed !== "object" ||
    parsed === null ||
    Array.isArray(parsed)
  ) {
    throw new Error(
      "The authorization dataset must be a JSON object.",
    );
  }

  return parsed as AuthorizationDataset;
}

function planStatusClass(
  planItem: BOLATestPlanItem,
): string {
  return planItem.ready
    ? "authorization-plan-status authorization-plan-status-ready"
    : "authorization-plan-status authorization-plan-status-blocked";
}

export function AuthorizationDatasetPanel({
  projectId,
}: AuthorizationDatasetPanelProps) {
  const queryClient =
    useQueryClient();

  const [
    editorText,
    setEditorText,
  ] = useState("");

  const [
    editorDirty,
    setEditorDirty,
  ] = useState(false);

  const [
    editorError,
    setEditorError,
  ] = useState<string | null>(
    null,
  );

  const [
    validationResult,
    setValidationResult,
  ] = useState<
    AuthorizationDatasetValidation
    | null
  >(null);

  const datasetQuery = useQuery({
    queryKey: [
      "projects",
      projectId,
      "authorization-dataset",
    ],
    queryFn: () =>
      getAuthorizationDataset(
        projectId,
      ),
  });

  const planQuery = useQuery({
    queryKey: [
      "projects",
      projectId,
      "bola-plan",
    ],
    queryFn: () =>
      getBOLATestPlan(
        projectId,
      ),
    enabled: datasetQuery.isSuccess,
  });

  useEffect(() => {
    if (
      datasetQuery.data &&
      !editorDirty
    ) {
      setEditorText(
        formatDataset(
          datasetQuery.data,
        ),
      );
    }
  }, [
    datasetQuery.data,
    editorDirty,
  ]);

  async function refreshData(
  ): Promise<void> {
    setEditorError(null);
    setValidationResult(null);

    const result =
      await datasetQuery.refetch();

    if (result.data) {
      setEditorText(
        formatDataset(
          result.data,
        ),
      );

      setEditorDirty(false);
    }

    await planQuery.refetch();
  }

  async function refreshQueries(
  ): Promise<void> {
    await queryClient.invalidateQueries({
      queryKey: [
        "projects",
        projectId,
        "authorization-dataset",
      ],
    });

    await queryClient.invalidateQueries({
      queryKey: [
        "projects",
        projectId,
        "bola-plan",
      ],
    });
  }

  const validationMutation =
    useMutation({
      mutationFn: (
        dataset: AuthorizationDataset,
      ) =>
        validateAuthorizationDataset(
          projectId,
          dataset,
        ),

      onSuccess: (
        result,
      ) => {
        setValidationResult(
          result,
        );
      },
    });

  const saveMutation =
    useMutation({
      mutationFn: (
        dataset: AuthorizationDataset,
      ) =>
        saveAuthorizationDataset(
          projectId,
          dataset,
        ),

      onSuccess: async (
        dataset,
      ) => {
        setEditorText(
          formatDataset(
            dataset,
          ),
        );

        setEditorDirty(false);
        setValidationResult({
          valid: true,
          issue_count: 0,
          issues: [],
        });

        await refreshQueries();
      },
    });

  const seedMutation =
    useMutation({
      mutationFn: () =>
        seedDemoAuthorizationDataset(
          projectId,
        ),

      onSuccess: async (
        dataset,
      ) => {
        setEditorText(
          formatDataset(
            dataset,
          ),
        );

        setEditorDirty(false);
        setEditorError(null);
        setValidationResult({
          valid: true,
          issue_count: 0,
          issues: [],
        });

        await refreshQueries();
      },
    });

  function buildDraft(
  ): AuthorizationDataset | null {
    setEditorError(null);

    try {
      return parseDataset(
        editorText,
      );
    } catch (error) {
      setEditorError(
        getErrorMessage(error),
      );

      return null;
    }
  }

  function validateDraft(): void {
    const dataset = buildDraft();

    if (!dataset) {
      return;
    }

    validationMutation.mutate(
      dataset,
    );
  }

  function saveDraft(): void {
    const dataset = buildDraft();

    if (!dataset) {
      return;
    }

    saveMutation.mutate(
      dataset,
    );
  }

  const dataset =
    datasetQuery.data;

  const plan =
    planQuery.data;

  const combinedError =
    datasetQuery.error ??
    planQuery.error ??
    validationMutation.error ??
    saveMutation.error ??
    seedMutation.error;

  const busy =
    datasetQuery.isFetching ||
    planQuery.isFetching ||
    validationMutation.isPending ||
    saveMutation.isPending ||
    seedMutation.isPending;

  return (
    <section className="authorization-panel">
      <header className="authorization-header">
        <div>
          <span className="authorization-section-label">
            Ownership configuration
          </span>

          <h3>
            Authorization dataset
          </h3>

          <p>
            Define protected resources, known
            objects, ownership, operation bindings,
            and expected allow or deny outcomes.
          </p>
        </div>

        <div className="authorization-header-actions">
          <button
            className="authorization-button authorization-button-secondary"
            disabled={busy}
            onClick={() => {
              void refreshData();
            }}
            type="button"
          >
            <RefreshCw
              aria-hidden="true"
              className={
                datasetQuery.isFetching ||
                planQuery.isFetching
                  ? "authorization-spinner"
                  : undefined
              }
              size={17}
            />

            Reload
          </button>

          <button
            className="authorization-button authorization-button-seed"
            disabled={busy}
            onClick={() => {
              seedMutation.mutate();
            }}
            type="button"
          >
            <Sparkles
              aria-hidden="true"
              size={17}
            />

            Seed invoice demo
          </button>
        </div>
      </header>

      {combinedError ? (
        <section
          className="authorization-alert"
          role="alert"
        >
          <AlertCircle
            aria-hidden="true"
            size={20}
          />

          <div>
            <strong>
              The authorization operation failed.
            </strong>

            <span>
              {getErrorMessage(
                combinedError,
              )}
            </span>
          </div>
        </section>
      ) : null}

      {editorError ? (
        <section
          className="authorization-alert"
          role="alert"
        >
          <AlertCircle
            aria-hidden="true"
            size={20}
          />

          <div>
            <strong>
              Dataset JSON is invalid.
            </strong>

            <span>
              {editorError}
            </span>
          </div>
        </section>
      ) : null}

      {validationResult ? (
        <section
          className={
            validationResult.valid
              ? "authorization-validation authorization-validation-valid"
              : "authorization-validation authorization-validation-invalid"
          }
          role="status"
        >
          {validationResult.valid ? (
            <CheckCircle2
              aria-hidden="true"
              size={20}
            />
          ) : (
            <ShieldAlert
              aria-hidden="true"
              size={20}
            />
          )}

          <div>
            <strong>
              {validationResult.valid
                ? "Dataset is valid."
                : `${validationResult.issue_count} validation issue(s) found.`}
            </strong>

            {validationResult.issues
              .length > 0 ? (
              <ul>
                {validationResult.issues.map(
                  (issue) => (
                    <li key={issue}>
                      {issue}
                    </li>
                  ),
                )}
              </ul>
            ) : (
              <span>
                The dataset is ready to be
                saved and used for plan generation.
              </span>
            )}
          </div>
        </section>
      ) : null}

      {datasetQuery.isPending ? (
        <section className="authorization-loading">
          <LoaderCircle
            aria-hidden="true"
            className="authorization-spinner"
            size={28}
          />

          <strong>
            Loading authorization dataset
          </strong>
        </section>
      ) : (
        <>
          <section className="authorization-stat-grid">
            <article>
              <Database
                aria-hidden="true"
                size={20}
              />

              <div>
                <span>
                  Resources
                </span>

                <strong>
                  {dataset?.resources.length ??
                    0}
                </strong>
              </div>
            </article>

            <article>
              <FileJson2
                aria-hidden="true"
                size={20}
              />

              <div>
                <span>
                  Objects
                </span>

                <strong>
                  {dataset?.objects.length ??
                    0}
                </strong>
              </div>
            </article>

            <article>
              <TestTube2
                aria-hidden="true"
                size={20}
              />

              <div>
                <span>
                  Cases
                </span>

                <strong>
                  {dataset?.cases.length ??
                    0}
                </strong>
              </div>
            </article>

            <article>
              <CheckCircle2
                aria-hidden="true"
                size={20}
              />

              <div>
                <span>
                  Ready BOLA probes
                </span>

                <strong>
                  {plan?.ready_count ??
                    0}
                </strong>
              </div>
            </article>
          </section>

          <section className="authorization-editor-section">
            <div className="authorization-section-heading">
              <span className="authorization-section-label">
                Dataset editor
              </span>

              <h4>
                Local JSON configuration
              </h4>

              <p>
                The demonstration seed replaces
                the current project dataset.
                Validate before saving manual edits.
              </p>
            </div>

            <textarea
              aria-label="Authorization dataset JSON"
              className="authorization-editor"
              onChange={(event) => {
                setEditorText(
                  event.target.value,
                );

                setEditorDirty(true);
                setValidationResult(null);
                setEditorError(null);
              }}
              rows={28}
              spellCheck={false}
              value={editorText}
            />

            <footer className="authorization-editor-actions">
              <span>
                {editorDirty
                  ? "Unsaved local changes"
                  : "Editor matches the saved dataset"}
              </span>

              <div>
                <button
                  className="authorization-button authorization-button-secondary"
                  disabled={busy}
                  onClick={validateDraft}
                  type="button"
                >
                  <CheckCircle2
                    aria-hidden="true"
                    size={17}
                  />

                  Validate
                </button>

                <button
                  className="authorization-button authorization-button-primary"
                  disabled={
                    busy ||
                    !editorDirty
                  }
                  onClick={saveDraft}
                  type="button"
                >
                  {saveMutation.isPending ? (
                    <LoaderCircle
                      aria-hidden="true"
                      className="authorization-spinner"
                      size={17}
                    />
                  ) : (
                    <Save
                      aria-hidden="true"
                      size={17}
                    />
                  )}

                  Save dataset
                </button>
              </div>
            </footer>
          </section>

          <section className="authorization-plan-section">
            <div className="authorization-section-heading">
              <span className="authorization-section-label">
                Automatic planning
              </span>

              <h4>
                Cross-owner BOLA plan
              </h4>

              <p>
                Each ready item pairs an allowed
                owned-object baseline with a denied
                cross-owner object probe.
              </p>
            </div>

            {planQuery.isPending ? (
              <section className="authorization-loading authorization-plan-loading">
                <LoaderCircle
                  aria-hidden="true"
                  className="authorization-spinner"
                  size={25}
                />

                <strong>
                  Generating BOLA plan
                </strong>
              </section>
            ) : plan &&
              plan.items.length > 0 ? (
              <div className="authorization-plan-grid">
                {plan.items.map(
                  (planItem) => (
                    <article
                      className="authorization-plan-card"
                      key={planItem.case_id}
                    >
                      <header>
                        <div>
                          <span>
                            {planItem.resource_type}
                          </span>

                          <h5>
                            {planItem.case_name}
                          </h5>
                        </div>

                        <span
                          className={planStatusClass(
                            planItem,
                          )}
                        >
                          {planItem.ready
                            ? "Ready"
                            : "Blocked"}
                        </span>
                      </header>

                      <dl>
                        <div>
                          <dt>
                            Identity
                          </dt>

                          <dd>
                            {planItem.identity_name}
                          </dd>
                        </div>

                        <div>
                          <dt>
                            Operation
                          </dt>

                          <dd>
                            <code>
                              {planItem.operation_key}
                            </code>
                          </dd>
                        </div>

                        <div>
                          <dt>
                            Owned baseline
                          </dt>

                          <dd>
                            <code>
                              {planItem.baseline_object_id ??
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
                              {planItem.probe_object_id}
                            </code>
                          </dd>
                        </div>

                        <div>
                          <dt>
                            Probe owner
                          </dt>

                          <dd>
                            {planItem.probe_owner_identity_name ??
                              "Unknown"}
                          </dd>
                        </div>

                        <div>
                          <dt>
                            Expected denial
                          </dt>

                          <dd>
                            {planItem
                              .expected_probe_status_codes
                              .join(", ")}
                          </dd>
                        </div>
                      </dl>

                      {planItem.issues.length >
                      0 ? (
                        <ul className="authorization-plan-issues">
                          {planItem.issues.map(
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
            ) : (
              <section className="authorization-empty">
                <TestTube2
                  aria-hidden="true"
                  size={29}
                />

                <h5>
                  No BOLA probes generated
                </h5>

                <p>
                  Seed or configure deny cases
                  with owned-object allow baselines.
                </p>
              </section>
            )}
          </section>
        </>
      )}
    </section>
  );
}