import {
  FileText,
  FolderKanban,
  LayoutDashboard,
  ScanSearch,
  Settings,
  ShieldCheck,
  TriangleAlert,
} from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

const navigation = [
  {
    name: "Dashboard",
    path: "/",
    icon: LayoutDashboard,
    end: true,
  },
  {
    name: "Projects",
    path: "/projects",
    icon: FolderKanban,
  },
  {
    name: "Scans",
    path: "/scans",
    icon: ScanSearch,
  },
  {
    name: "Findings",
    path: "/findings",
    icon: TriangleAlert,
  },
  {
    name: "Reports",
    path: "/reports",
    icon: FileText,
  },
  {
    name: "Settings",
    path: "/settings",
    icon: Settings,
  },
];

export function AppShell() {
  return (
    <div className="application-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">
            <ShieldCheck size={25} />
          </div>

          <div>
            <strong>AccessMatrix</strong>
            <span>Authorization testing</span>
          </div>
        </div>

        <nav className="navigation">
          {navigation.map((item) => {
            const Icon = item.icon;

            return (
              <NavLink
                key={item.path}
                to={item.path}
                end={item.end}
                className={({ isActive }) =>
                  isActive
                    ? "navigation-link active"
                    : "navigation-link"
                }
              >
                <Icon size={19} />
                <span>{item.name}</span>
              </NavLink>
            );
          })}
        </nav>

        <div className="sidebar-footer">
          <span className="status-indicator" />

          <div>
            <strong>Local-first</strong>
            <span>No cloud dependency</span>
          </div>
        </div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <span className="eyebrow">Security workspace</span>
            <h1>API Authorization Assurance</h1>
          </div>

          <div className="engine-status">
            <span className="status-indicator" />
            Local engine
          </div>
        </header>

        <main className="workspace-content">
          <Outlet />
        </main>
      </section>
    </div>
  );
}