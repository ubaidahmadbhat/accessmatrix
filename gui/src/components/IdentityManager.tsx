import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  AlertCircle,
  CheckCircle2,
  Edit3,
  Eye,
  EyeOff,
  Fingerprint,
  KeyRound,
  LoaderCircle,
  Plus,
  RefreshCw,
  ShieldCheck,
  ShieldOff,
  Trash2,
  UserRound,
  UsersRound,
  X,
} from "lucide-react";
import type {
  FormEvent,
} from "react";
import {
  useState,
} from "react";

import type {
  AuthLocation,
  AuthType,
  IdentityInput,
  IdentityProfile,
  SecretSource,
} from "../api/identities";
import {
  createIdentity,
  deleteIdentity,
  listIdentities,
  updateIdentity,
} from "../api/identities";
import {
  ApiRequestError,
} from "../api/projects";

import "./IdentityManager.css";

interface IdentityManagerProps {
  projectId: string;
}

interface SaveIdentityVariables {
  identityId: string | null;
  input: IdentityInput;
}

const EMPTY_IDENTITY_FORM: IdentityInput = {
  name: "",
  description: "",
  role: "",
  tenant: "",
  department: "",
  auth_type: "none",
  secret_source: "environment",
  secret_reference: null,
  username_reference: null,
  password_reference: null,
  auth_location: null,
  auth_name: null,
  auth_prefix: null,
  enabled: true,
};

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

function normalizeOptionalText(
  value: string | null,
): string | null {
  if (value === null) {
    return null;
  }

  const normalized = value.trim();

  return normalized || null;
}

function normalizeIdentityInput(
  form: IdentityInput,
): IdentityInput {
  const normalized: IdentityInput = {
    ...form,
    name: form.name.trim(),
    description: normalizeOptionalText(
      form.description,
    ),
    role: form.role.trim(),
    tenant: normalizeOptionalText(
      form.tenant,
    ),
    department: normalizeOptionalText(
      form.department,
    ),
    secret_reference:
      normalizeOptionalText(
        form.secret_reference,
      ),
    username_reference:
      normalizeOptionalText(
        form.username_reference,
      ),
    password_reference:
      normalizeOptionalText(
        form.password_reference,
      ),
    auth_name: normalizeOptionalText(
      form.auth_name,
    ),
    auth_prefix: normalizeOptionalText(
      form.auth_prefix,
    ),
  };

  if (normalized.auth_type === "none") {
    return {
      ...normalized,
      secret_reference: null,
      username_reference: null,
      password_reference: null,
      auth_location: null,
      auth_name: null,
      auth_prefix: null,
    };
  }

  if (normalized.auth_type === "bearer") {
    return {
      ...normalized,
      username_reference: null,
      password_reference: null,
      auth_location: null,
      auth_name: null,
      auth_prefix:
        normalized.auth_prefix ??
        "Bearer",
    };
  }

  if (normalized.auth_type === "basic") {
    return {
      ...normalized,
      secret_reference: null,
      auth_location: null,
      auth_name: null,
      auth_prefix: null,
    };
  }

  if (normalized.auth_type === "cookie") {
    return {
      ...normalized,
      username_reference: null,
      password_reference: null,
      auth_location: "cookie",
      auth_prefix: null,
    };
  }

  if (
    normalized.auth_type ===
    "custom_header"
  ) {
    return {
      ...normalized,
      username_reference: null,
      password_reference: null,
      auth_location: "header",
    };
  }

  return {
    ...normalized,
    username_reference: null,
    password_reference: null,
  };
}

function identityToInput(
  identity: IdentityProfile,
): IdentityInput {
  return {
    name: identity.name,
    description:
      identity.description ?? "",
    role: identity.role,
    tenant: identity.tenant ?? "",
    department:
      identity.department ?? "",
    auth_type: identity.auth_type,
    secret_source:
      identity.secret_source,
    secret_reference:
      identity.secret_reference,
    username_reference:
      identity.username_reference,
    password_reference:
      identity.password_reference,
    auth_location:
      identity.auth_location,
    auth_name:
      identity.auth_name,
    auth_prefix:
      identity.auth_prefix,
    enabled: identity.enabled,
  };
}

function identityCanBeSubmitted(
  form: IdentityInput,
): boolean {
  if (
    form.name.trim().length < 2 ||
    form.role.trim().length < 1
  ) {
    return false;
  }

  if (form.auth_type === "none") {
    return true;
  }

  if (form.auth_type === "bearer") {
    return Boolean(
      form.secret_reference?.trim(),
    );
  }

  if (form.auth_type === "basic") {
    return Boolean(
      form.username_reference?.trim() &&
      form.password_reference?.trim(),
    );
  }

  if (form.auth_type === "api_key") {
    return Boolean(
      form.secret_reference?.trim() &&
      form.auth_name?.trim() &&
      form.auth_location,
    );
  }

  if (
    form.auth_type === "cookie" ||
    form.auth_type === "custom_header"
  ) {
    return Boolean(
      form.secret_reference?.trim() &&
      form.auth_name?.trim(),
    );
  }

  return false;
}

function getAuthDescription(
  identity: IdentityProfile,
): string {
  if (identity.auth_type === "none") {
    return "No credentials";
  }

  if (identity.auth_type === "basic") {
    return [
      identity.username_reference,
      identity.password_reference,
    ]
      .filter(Boolean)
      .join(" / ");
  }

  if (identity.auth_type === "bearer") {
    return (
      identity.secret_reference ??
      "Token reference missing"
    );
  }

  const name =
    identity.auth_name ??
    "Authentication name missing";

  const reference =
    identity.secret_reference ??
    "Secret reference missing";

  return `${name} · ${reference}`;
}

interface IdentityDialogProps {
  form: IdentityInput;
  editingIdentity: IdentityProfile | null;
  isPending: boolean;
  onAuthTypeChange: (
    authType: AuthType,
  ) => void;
  onChange: (
    field: keyof IdentityInput,
    value:
      | string
      | boolean
      | null,
  ) => void;
  onClose: () => void;
  onSubmit: (
    event: FormEvent<HTMLFormElement>,
  ) => void;
}

function IdentityDialog({
  form,
  editingIdentity,
  isPending,
  onAuthTypeChange,
  onChange,
  onClose,
  onSubmit,
}: IdentityDialogProps) {
  const isEditing =
    editingIdentity !== null;

  return (
    <div className="identity-dialog-backdrop">
      <section
        aria-labelledby="identity-dialog-title"
        aria-modal="true"
        className="identity-dialog"
        role="dialog"
      >
        <header className="identity-dialog-header">
          <div>
            <span className="identity-section-label">
              {isEditing
                ? "Update identity"
                : "New identity"}
            </span>

            <h3 id="identity-dialog-title">
              {isEditing
                ? "Edit identity profile"
                : "Create identity profile"}
            </h3>

            <p>
              Store credential references only.
              Never enter a real token, password,
              cookie value, or API key here.
            </p>
          </div>

          <button
            aria-label="Close identity dialog"
            className="identity-icon-button"
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
          className="identity-form"
          onSubmit={onSubmit}
        >
          <section className="identity-form-section">
            <div className="identity-form-section-heading">
              <span className="identity-section-label">
                Profile
              </span>

              <h4>
                Identity information
              </h4>
            </div>

            <div className="identity-form-grid">
              <label className="identity-field">
                <span>
                  Display name
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
                  placeholder="Customer Alice"
                  required
                  type="text"
                  value={form.name}
                />
              </label>

              <label className="identity-field">
                <span>
                  Role
                  <strong aria-hidden="true">
                    *
                  </strong>
                </span>

                <input
                  maxLength={120}
                  onChange={(event) => {
                    onChange(
                      "role",
                      event.target.value,
                    );
                  }}
                  placeholder="customer"
                  required
                  type="text"
                  value={form.role}
                />
              </label>

              <label className="identity-field">
                <span>
                  Tenant
                </span>

                <input
                  maxLength={120}
                  onChange={(event) => {
                    onChange(
                      "tenant",
                      event.target.value,
                    );
                  }}
                  placeholder="tenant-a"
                  type="text"
                  value={form.tenant ?? ""}
                />
              </label>

              <label className="identity-field">
                <span>
                  Department
                </span>

                <input
                  maxLength={120}
                  onChange={(event) => {
                    onChange(
                      "department",
                      event.target.value,
                    );
                  }}
                  placeholder="finance"
                  type="text"
                  value={
                    form.department ?? ""
                  }
                />
              </label>
            </div>

            <label className="identity-field">
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
                placeholder="Describe what this identity represents and which objects it owns."
                rows={3}
                value={
                  form.description ?? ""
                }
              />
            </label>
          </section>

          <section className="identity-form-section">
            <div className="identity-form-section-heading">
              <span className="identity-section-label">
                Authentication
              </span>

              <h4>
                Credential configuration
              </h4>
            </div>

            <div className="identity-form-grid">
              <label className="identity-field">
                <span>
                  Authentication type
                </span>

                <select
                  onChange={(event) => {
                    onAuthTypeChange(
                      event.target
                        .value as AuthType,
                    );
                  }}
                  value={form.auth_type}
                >
                  <option value="none">
                    No authentication
                  </option>

                  <option value="bearer">
                    Bearer token
                  </option>

                  <option value="api_key">
                    API key
                  </option>

                  <option value="basic">
                    HTTP Basic
                  </option>

                  <option value="cookie">
                    Cookie
                  </option>

                  <option value="custom_header">
                    Custom header
                  </option>
                </select>
              </label>

              {form.auth_type !== "none" ? (
                <label className="identity-field">
                  <span>
                    Secret source
                  </span>

                  <select
                    onChange={(event) => {
                      onChange(
                        "secret_source",
                        event.target
                          .value as SecretSource,
                      );
                    }}
                    value={
                      form.secret_source
                    }
                  >
                    <option value="environment">
                      Environment variable
                    </option>

                    <option value="keyring">
                      Operating-system keyring
                    </option>
                  </select>
                </label>
              ) : null}
            </div>

            {form.auth_type === "none" ? (
              <div className="identity-auth-notice">
                <ShieldOff
                  aria-hidden="true"
                  size={20}
                />

                <div>
                  <strong>
                    Unauthenticated identity
                  </strong>

                  <span>
                    Requests executed with this
                    identity will not contain
                    authentication credentials.
                  </span>
                </div>
              </div>
            ) : null}

            {form.auth_type === "bearer" ? (
              <div className="identity-form-grid">
                <label className="identity-field">
                  <span>
                    Token reference
                    <strong aria-hidden="true">
                      *
                    </strong>
                  </span>

                  <input
                    onChange={(event) => {
                      onChange(
                        "secret_reference",
                        event.target.value,
                      );
                    }}
                    placeholder="ACCESSMATRIX_ALICE_TOKEN"
                    required
                    type="text"
                    value={
                      form.secret_reference ??
                      ""
                    }
                  />
                </label>

                <label className="identity-field">
                  <span>
                    Authorization prefix
                  </span>

                  <input
                    onChange={(event) => {
                      onChange(
                        "auth_prefix",
                        event.target.value,
                      );
                    }}
                    placeholder="Bearer"
                    type="text"
                    value={
                      form.auth_prefix ?? ""
                    }
                  />
                </label>
              </div>
            ) : null}

            {form.auth_type === "api_key" ? (
              <>
                <div className="identity-form-grid">
                  <label className="identity-field">
                    <span>
                      API key reference
                      <strong aria-hidden="true">
                        *
                      </strong>
                    </span>

                    <input
                      onChange={(event) => {
                        onChange(
                          "secret_reference",
                          event.target.value,
                        );
                      }}
                      placeholder="ACCESSMATRIX_API_KEY"
                      required
                      type="text"
                      value={
                        form.secret_reference ??
                        ""
                      }
                    />
                  </label>

                  <label className="identity-field">
                    <span>
                      Location
                      <strong aria-hidden="true">
                        *
                      </strong>
                    </span>

                    <select
                      onChange={(event) => {
                        onChange(
                          "auth_location",
                          event.target
                            .value as AuthLocation,
                        );
                      }}
                      value={
                        form.auth_location ??
                        "header"
                      }
                    >
                      <option value="header">
                        Header
                      </option>

                      <option value="query">
                        Query parameter
                      </option>

                      <option value="cookie">
                        Cookie
                      </option>
                    </select>
                  </label>
                </div>

                <div className="identity-form-grid">
                  <label className="identity-field">
                    <span>
                      Authentication name
                      <strong aria-hidden="true">
                        *
                      </strong>
                    </span>

                    <input
                      onChange={(event) => {
                        onChange(
                          "auth_name",
                          event.target.value,
                        );
                      }}
                      placeholder="X-API-Key"
                      required
                      type="text"
                      value={
                        form.auth_name ?? ""
                      }
                    />
                  </label>

                  <label className="identity-field">
                    <span>
                      Optional value prefix
                    </span>

                    <input
                      onChange={(event) => {
                        onChange(
                          "auth_prefix",
                          event.target.value,
                        );
                      }}
                      placeholder="Token"
                      type="text"
                      value={
                        form.auth_prefix ?? ""
                      }
                    />
                  </label>
                </div>
              </>
            ) : null}

            {form.auth_type === "basic" ? (
              <div className="identity-form-grid">
                <label className="identity-field">
                  <span>
                    Username reference
                    <strong aria-hidden="true">
                      *
                    </strong>
                  </span>

                  <input
                    onChange={(event) => {
                      onChange(
                        "username_reference",
                        event.target.value,
                      );
                    }}
                    placeholder="ACCESSMATRIX_BASIC_USERNAME"
                    required
                    type="text"
                    value={
                      form.username_reference ??
                      ""
                    }
                  />
                </label>

                <label className="identity-field">
                  <span>
                    Password reference
                    <strong aria-hidden="true">
                      *
                    </strong>
                  </span>

                  <input
                    onChange={(event) => {
                      onChange(
                        "password_reference",
                        event.target.value,
                      );
                    }}
                    placeholder="ACCESSMATRIX_BASIC_PASSWORD"
                    required
                    type="text"
                    value={
                      form.password_reference ??
                      ""
                    }
                  />
                </label>
              </div>
            ) : null}

            {form.auth_type === "cookie" ? (
              <div className="identity-form-grid">
                <label className="identity-field">
                  <span>
                    Cookie value reference
                    <strong aria-hidden="true">
                      *
                    </strong>
                  </span>

                  <input
                    onChange={(event) => {
                      onChange(
                        "secret_reference",
                        event.target.value,
                      );
                    }}
                    placeholder="ACCESSMATRIX_SESSION_COOKIE"
                    required
                    type="text"
                    value={
                      form.secret_reference ??
                      ""
                    }
                  />
                </label>

                <label className="identity-field">
                  <span>
                    Cookie name
                    <strong aria-hidden="true">
                      *
                    </strong>
                  </span>

                  <input
                    onChange={(event) => {
                      onChange(
                        "auth_name",
                        event.target.value,
                      );
                    }}
                    placeholder="session_id"
                    required
                    type="text"
                    value={
                      form.auth_name ?? ""
                    }
                  />
                </label>
              </div>
            ) : null}

            {form.auth_type ===
            "custom_header" ? (
              <>
                <div className="identity-form-grid">
                  <label className="identity-field">
                    <span>
                      Header value reference
                      <strong aria-hidden="true">
                        *
                      </strong>
                    </span>

                    <input
                      onChange={(event) => {
                        onChange(
                          "secret_reference",
                          event.target.value,
                        );
                      }}
                      placeholder="ACCESSMATRIX_CUSTOM_TOKEN"
                      required
                      type="text"
                      value={
                        form.secret_reference ??
                        ""
                      }
                    />
                  </label>

                  <label className="identity-field">
                    <span>
                      Header name
                      <strong aria-hidden="true">
                        *
                      </strong>
                    </span>

                    <input
                      onChange={(event) => {
                        onChange(
                          "auth_name",
                          event.target.value,
                        );
                      }}
                      placeholder="X-Authentication-Token"
                      required
                      type="text"
                      value={
                        form.auth_name ?? ""
                      }
                    />
                  </label>
                </div>

                <label className="identity-field">
                  <span>
                    Optional value prefix
                  </span>

                  <input
                    onChange={(event) => {
                      onChange(
                        "auth_prefix",
                        event.target.value,
                      );
                    }}
                    placeholder="Token"
                    type="text"
                    value={
                      form.auth_prefix ?? ""
                    }
                  />
                </label>
              </>
            ) : null}

            {form.auth_type !== "none" ? (
              <div className="identity-secret-warning">
                <EyeOff
                  aria-hidden="true"
                  size={19}
                />

                <div>
                  <strong>
                    Reference only
                  </strong>

                  <span>
                    Enter the environment-variable
                    or keyring entry name, not the
                    secret value itself.
                  </span>
                </div>
              </div>
            ) : null}
          </section>

          <label className="identity-toggle-field">
            <input
              checked={form.enabled}
              onChange={(event) => {
                onChange(
                  "enabled",
                  event.target.checked,
                );
              }}
              type="checkbox"
            />

            <span>
              <strong>
                Identity enabled
              </strong>

              <small>
                Disabled identities remain stored
                but will not be available for scans.
              </small>
            </span>
          </label>

          <footer className="identity-dialog-actions">
            <button
              className="identity-button identity-button-secondary"
              disabled={isPending}
              onClick={onClose}
              type="button"
            >
              Cancel
            </button>

            <button
              className="identity-button identity-button-primary"
              disabled={
                isPending ||
                !identityCanBeSubmitted(form)
              }
              type="submit"
            >
              {isPending ? (
                <>
                  <LoaderCircle
                    aria-hidden="true"
                    className="identity-spinner"
                    size={17}
                  />

                  Saving
                </>
              ) : (
                <>
                  <CheckCircle2
                    aria-hidden="true"
                    size={17}
                  />

                  {isEditing
                    ? "Save changes"
                    : "Create identity"}
                </>
              )}
            </button>
          </footer>
        </form>
      </section>
    </div>
  );
}

interface DeleteIdentityDialogProps {
  identity: IdentityProfile;
  isPending: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}

function DeleteIdentityDialog({
  identity,
  isPending,
  onCancel,
  onConfirm,
}: DeleteIdentityDialogProps) {
  return (
    <div className="identity-dialog-backdrop">
      <section
        aria-labelledby="delete-identity-title"
        aria-modal="true"
        className="identity-dialog identity-delete-dialog"
        role="dialog"
      >
        <header className="identity-dialog-header">
          <div>
            <span className="identity-section-label identity-danger-label">
              Destructive action
            </span>

            <h3 id="delete-identity-title">
              Delete identity
            </h3>
          </div>

          <button
            aria-label="Close delete identity dialog"
            className="identity-icon-button"
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

        <div className="identity-delete-message">
          <div className="identity-delete-icon">
            <Trash2
              aria-hidden="true"
              size={23}
            />
          </div>

          <div>
            <p>
              Delete{" "}
              <strong>
                {identity.name}
              </strong>
              ?
            </p>

            <span>
              The identity profile and its
              credential references will be
              removed. Secret values stored
              externally are not deleted.
            </span>
          </div>
        </div>

        <footer className="identity-dialog-actions">
          <button
            className="identity-button identity-button-secondary"
            disabled={isPending}
            onClick={onCancel}
            type="button"
          >
            Cancel
          </button>

          <button
            className="identity-button identity-button-danger"
            disabled={isPending}
            onClick={onConfirm}
            type="button"
          >
            {isPending ? (
              <>
                <LoaderCircle
                  aria-hidden="true"
                  className="identity-spinner"
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

                Delete identity
              </>
            )}
          </button>
        </footer>
      </section>
    </div>
  );
}

export function IdentityManager({
  projectId,
}: IdentityManagerProps) {
  const queryClient =
    useQueryClient();

  const [
    dialogOpen,
    setDialogOpen,
  ] = useState(false);

  const [
    editingIdentity,
    setEditingIdentity,
  ] = useState<IdentityProfile | null>(
    null,
  );

  const [
    deleteTarget,
    setDeleteTarget,
  ] = useState<IdentityProfile | null>(
    null,
  );

  const [
    form,
    setForm,
  ] = useState<IdentityInput>(
    EMPTY_IDENTITY_FORM,
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

  const saveMutation = useMutation({
    mutationFn: ({
      identityId,
      input,
    }: SaveIdentityVariables) => {
      if (identityId) {
        return updateIdentity(
          projectId,
          identityId,
          input,
        );
      }

      return createIdentity(
        projectId,
        input,
      );
    },

    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: [
          "projects",
          projectId,
          "identities",
        ],
      });

      setDialogOpen(false);
      setEditingIdentity(null);
      setForm(EMPTY_IDENTITY_FORM);
    },
  });

  const toggleMutation = useMutation({
    mutationFn: (
      identity: IdentityProfile,
    ) =>
      updateIdentity(
        projectId,
        identity.id,
        {
          ...identityToInput(identity),
          enabled: !identity.enabled,
        },
      ),

    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: [
          "projects",
          projectId,
          "identities",
        ],
      });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (
      identityId: string,
    ) =>
      deleteIdentity(
        projectId,
        identityId,
      ),

    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: [
          "projects",
          projectId,
          "identities",
        ],
      });

      setDeleteTarget(null);
    },
  });

  const combinedError =
    identitiesQuery.error ??
    saveMutation.error ??
    toggleMutation.error ??
    deleteMutation.error;

  const identities =
    identitiesQuery.data ?? [];

  const enabledCount =
    identities.filter(
      (identity) => identity.enabled,
    ).length;

  const authenticatedCount =
    identities.filter(
      (identity) =>
        identity.auth_type !== "none",
    ).length;

  function openCreateDialog(): void {
    saveMutation.reset();
    setEditingIdentity(null);
    setForm(EMPTY_IDENTITY_FORM);
    setDialogOpen(true);
  }

  function openEditDialog(
    identity: IdentityProfile,
  ): void {
    saveMutation.reset();
    setEditingIdentity(identity);
    setForm(identityToInput(identity));
    setDialogOpen(true);
  }

  function closeDialog(): void {
    if (saveMutation.isPending) {
      return;
    }

    saveMutation.reset();
    setDialogOpen(false);
    setEditingIdentity(null);
  }

  function updateForm(
    field: keyof IdentityInput,
    value:
      | string
      | boolean
      | null,
  ): void {
    setForm((current) => ({
      ...current,
      [field]: value,
    }));
  }

  function changeAuthType(
    authType: AuthType,
  ): void {
    setForm((current) => {
      const updated: IdentityInput = {
        ...current,
        auth_type: authType,
        secret_reference: null,
        username_reference: null,
        password_reference: null,
        auth_location: null,
        auth_name: null,
        auth_prefix: null,
      };

      if (authType === "bearer") {
        updated.auth_prefix =
          "Bearer";
      }

      if (authType === "api_key") {
        updated.auth_location =
          "header";
      }

      if (authType === "cookie") {
        updated.auth_location =
          "cookie";
      }

      if (
        authType === "custom_header"
      ) {
        updated.auth_location =
          "header";
      }

      return updated;
    });
  }

  function submitIdentity(
    event: FormEvent<HTMLFormElement>,
  ): void {
    event.preventDefault();

    saveMutation.mutate({
      identityId:
        editingIdentity?.id ?? null,
      input:
        normalizeIdentityInput(form),
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

  return (
    <section className="identity-manager">
      <header className="identity-manager-header">
        <div>
          <span className="identity-section-label">
            Authorization actors
          </span>

          <h3>
            Identity manager
          </h3>

          <p>
            Define the authenticated and
            unauthenticated identities that will
            be compared during authorization tests.
          </p>
        </div>

        <div className="identity-manager-actions">
          <button
            className="identity-button identity-button-secondary"
            disabled={
              identitiesQuery.isFetching
            }
            onClick={() => {
              void identitiesQuery.refetch();
            }}
            type="button"
          >
            <RefreshCw
              aria-hidden="true"
              className={
                identitiesQuery.isFetching
                  ? "identity-spinner"
                  : undefined
              }
              size={17}
            />

            Refresh
          </button>

          <button
            className="identity-button identity-button-primary"
            onClick={openCreateDialog}
            type="button"
          >
            <Plus
              aria-hidden="true"
              size={17}
            />

            Create identity
          </button>
        </div>
      </header>

      <section className="identity-stat-grid">
        <article>
          <UsersRound
            aria-hidden="true"
            size={20}
          />

          <div>
            <span>
              Total identities
            </span>

            <strong>
              {identities.length}
            </strong>
          </div>
        </article>

        <article>
          <ShieldCheck
            aria-hidden="true"
            size={20}
          />

          <div>
            <span>
              Enabled
            </span>

            <strong>
              {enabledCount}
            </strong>
          </div>
        </article>

        <article>
          <KeyRound
            aria-hidden="true"
            size={20}
          />

          <div>
            <span>
              Authenticated
            </span>

            <strong>
              {authenticatedCount}
            </strong>
          </div>
        </article>
      </section>

      {combinedError ? (
        <section
          className="identity-alert"
          role="alert"
        >
          <AlertCircle
            aria-hidden="true"
            size={21}
          />

          <div>
            <strong>
              The identity operation failed.
            </strong>

            <span>
              {getErrorMessage(
                combinedError,
              )}
            </span>
          </div>
        </section>
      ) : null}

      {identitiesQuery.isPending ? (
        <section className="identity-loading">
          <LoaderCircle
            aria-hidden="true"
            className="identity-spinner"
            size={28}
          />

          <strong>
            Loading identities
          </strong>
        </section>
      ) : null}

      {!identitiesQuery.isPending &&
      identities.length === 0 ? (
        <section className="identity-empty-state">
          <div className="identity-empty-icon">
            <Fingerprint
              aria-hidden="true"
              size={31}
            />
          </div>

          <span className="identity-section-label">
            No identities configured
          </span>

          <h4>
            Add the first authorization actor
          </h4>

          <p>
            Start with an anonymous identity and
            at least two authenticated identities
            that own different API objects.
          </p>

          <button
            className="identity-button identity-button-primary"
            onClick={openCreateDialog}
            type="button"
          >
            <Plus
              aria-hidden="true"
              size={17}
            />

            Create first identity
          </button>
        </section>
      ) : null}

      {identities.length > 0 ? (
        <div className="identity-grid">
          {identities.map(
            (identity) => {
              const togglingThisIdentity =
                toggleMutation.isPending &&
                toggleMutation.variables
                  ?.id === identity.id;

              return (
                <article
                  className={
                    identity.enabled
                      ? "identity-card"
                      : "identity-card identity-card-disabled"
                  }
                  key={identity.id}
                >
                  <header className="identity-card-header">
                    <div className="identity-card-title">
                      <div className="identity-avatar">
                        <UserRound
                          aria-hidden="true"
                          size={21}
                        />
                      </div>

                      <div>
                        <h4>
                          {identity.name}
                        </h4>

                        <span>
                          {identity.role}
                        </span>
                      </div>
                    </div>

                    <span
                      className={
                        identity.enabled
                          ? "identity-status identity-status-enabled"
                          : "identity-status identity-status-disabled"
                      }
                    >
                      {identity.enabled
                        ? "Enabled"
                        : "Disabled"}
                    </span>
                  </header>

                  <p className="identity-card-description">
                    {identity.description ??
                      "No identity description has been provided."}
                  </p>

                  <dl className="identity-card-metadata">
                    <div>
                      <dt>
                        Authentication
                      </dt>

                      <dd>
                        {
                          AUTH_TYPE_LABELS[
                            identity.auth_type
                          ]
                        }
                      </dd>
                    </div>

                    <div>
                      <dt>
                        Tenant
                      </dt>

                      <dd>
                        {identity.tenant ??
                          "Not configured"}
                      </dd>
                    </div>

                    <div>
                      <dt>
                        Department
                      </dt>

                      <dd>
                        {identity.department ??
                          "Not configured"}
                      </dd>
                    </div>

                    <div>
                      <dt>
                        Secret source
                      </dt>

                      <dd>
                        {identity.auth_type ===
                        "none"
                          ? "Not applicable"
                          : identity.secret_source}
                      </dd>
                    </div>
                  </dl>

                  <div className="identity-auth-reference">
                    {identity.auth_type ===
                    "none" ? (
                      <ShieldOff
                        aria-hidden="true"
                        size={17}
                      />
                    ) : (
                      <KeyRound
                        aria-hidden="true"
                        size={17}
                      />
                    )}

                    <div>
                      <span>
                        Credential reference
                      </span>

                      <strong
                        title={getAuthDescription(
                          identity,
                        )}
                      >
                        {getAuthDescription(
                          identity,
                        )}
                      </strong>
                    </div>
                  </div>

                  <footer className="identity-card-actions">
                    <button
                      className="identity-button identity-button-secondary"
                      disabled={
                        saveMutation.isPending ||
                        deleteMutation.isPending ||
                        toggleMutation.isPending
                      }
                      onClick={() => {
                        openEditDialog(
                          identity,
                        );
                      }}
                      type="button"
                    >
                      <Edit3
                        aria-hidden="true"
                        size={16}
                      />

                      Edit
                    </button>

                    <button
                      className="identity-button identity-button-secondary"
                      disabled={
                        toggleMutation.isPending ||
                        deleteMutation.isPending
                      }
                      onClick={() => {
                        toggleMutation.mutate(
                          identity,
                        );
                      }}
                      type="button"
                    >
                      {togglingThisIdentity ? (
                        <LoaderCircle
                          aria-hidden="true"
                          className="identity-spinner"
                          size={16}
                        />
                      ) : identity.enabled ? (
                        <EyeOff
                          aria-hidden="true"
                          size={16}
                        />
                      ) : (
                        <Eye
                          aria-hidden="true"
                          size={16}
                        />
                      )}

                      {identity.enabled
                        ? "Disable"
                        : "Enable"}
                    </button>

                    <button
                      aria-label={`Delete ${identity.name}`}
                      className="identity-icon-button identity-delete-button"
                      disabled={
                        deleteMutation.isPending ||
                        toggleMutation.isPending
                      }
                      onClick={() => {
                        deleteMutation.reset();
                        setDeleteTarget(
                          identity,
                        );
                      }}
                      title="Delete identity"
                      type="button"
                    >
                      <Trash2
                        aria-hidden="true"
                        size={17}
                      />
                    </button>
                  </footer>
                </article>
              );
            },
          )}
        </div>
      ) : null}

      {dialogOpen ? (
        <IdentityDialog
          editingIdentity={
            editingIdentity
          }
          form={form}
          isPending={
            saveMutation.isPending
          }
          onAuthTypeChange={
            changeAuthType
          }
          onChange={updateForm}
          onClose={closeDialog}
          onSubmit={submitIdentity}
        />
      ) : null}

      {deleteTarget ? (
        <DeleteIdentityDialog
          identity={deleteTarget}
          isPending={
            deleteMutation.isPending
          }
          onCancel={() => {
            if (
              !deleteMutation.isPending
            ) {
              setDeleteTarget(null);
            }
          }}
          onConfirm={confirmDelete}
        />
      ) : null}
    </section>
  );
}