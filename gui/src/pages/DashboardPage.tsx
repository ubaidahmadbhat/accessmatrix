import {
  useQuery,
} from "@tanstack/react-query";
import {
  Activity,
  Braces,
  Database,
  Network,
  ShieldAlert,
} from "lucide-react";
import {
  useNavigate,
} from "react-router-dom";

import {
  fetchHealth,
} from "../api/health";

const capabilities = [
  {
    title: "BOLA testing",
    description:
      "Test whether users can access objects owned by other identities.",
    icon: Network,
  },
  {
    title: "BFLA testing",
    description:
      "Verify access to restricted, administrative and privileged functions.",
    icon: ShieldAlert,
  },
  {
    title: "BOPLA testing",
    description:
      "Detect unauthorized request and response property exposure.",
    icon: Braces,
  },
];

export function DashboardPage() {
  const navigate = useNavigate();

  const healthQuery = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
    refetchInterval: 30000,
  });

  const health = healthQuery.data;

  return (
    <div className="page">
      <section className="hero-panel">
        <div>
          <span className="section-label">
            Authorization regression testing
          </span>

          <h2>
            Test who can do what,
            to which API object.
          </h2>

          <p>
            Import an OpenAPI specification,
            configure identities and define
            the expected authorization policy
            before executing controlled BOLA,
            BFLA and BOPLA tests.
          </p>

          <div className="hero-actions">
            <button
              className="button primary"
              onClick={() => {
                navigate("/projects");
              }}
              type="button"
            >
              Create project
            </button>

            <button
              className="button secondary"
              onClick={() => {
                navigate("/projects");
              }}
              type="button"
            >
              Import OpenAPI
            </button>
          </div>
        </div>

        <div className="matrix-visual">
          {Array.from(
            {
              length: 25,
            },
            (_, index) => (
              <span
                className={
                  index === 7 ||
                  index === 13 ||
                  index === 19
                    ? "matrix-cell denied"
                    : index % 3 === 0
                      ? "matrix-cell allowed"
                      : "matrix-cell"
                }
                key={index}
              />
            ),
          )}
        </div>
      </section>

      <section className="status-grid">
        <article className="status-card">
          <Activity size={21} />

          <div>
            <span>
              Engine status
            </span>

            <strong>
              {healthQuery.isPending
                ? "Checking"
                : healthQuery.isError
                  ? "Unavailable"
                  : "Operational"}
            </strong>
          </div>
        </article>

        <article className="status-card">
          <ShieldAlert size={21} />

          <div>
            <span>
              Engine version
            </span>

            <strong>
              {health?.version ??
                "Loading..."}
            </strong>
          </div>
        </article>

        <article className="status-card">
          <Database size={21} />

          <div>
            <span>
              Storage mode
            </span>

            <strong>
              Local workspace
            </strong>
          </div>
        </article>
      </section>

      <section className="dashboard-grid">
        <article className="panel">
          <span className="section-label">
            Testing engines
          </span>

          <h3>
            Authorization coverage
          </h3>

          <div className="capability-list">
            {capabilities.map(
              (capability) => {
                const Icon =
                  capability.icon;

                return (
                  <div
                    className="capability-item"
                    key={capability.title}
                  >
                    <div className="capability-icon">
                      <Icon size={20} />
                    </div>

                    <div>
                      <strong>
                        {capability.title}
                      </strong>

                      <p>
                        {capability.description}
                      </p>
                    </div>

                    <span className="badge">
                      Planned
                    </span>
                  </div>
                );
              },
            )}
          </div>
        </article>

        <article className="panel">
          <span className="section-label">
            Runtime
          </span>

          <h3>
            System information
          </h3>

          <dl className="system-list">
            <div>
              <dt>
                Application
              </dt>

              <dd>
                {health?.application ??
                  "AccessMatrix"}
              </dd>
            </div>

            <div>
              <dt>
                Python
              </dt>

              <dd>
                {health?.python_version ??
                  "Loading..."}
              </dd>
            </div>

            <div>
              <dt>
                Platform
              </dt>

              <dd>
                {health?.platform ??
                  "Loading..."}
              </dd>
            </div>

            <div>
              <dt>
                Data directory
              </dt>

              <dd>
                {health?.data_directory ??
                  "Loading..."}
              </dd>
            </div>
          </dl>
        </article>
      </section>
    </div>
  );
}