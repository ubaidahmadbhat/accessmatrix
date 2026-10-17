import {
  Route,
  Routes,
} from "react-router-dom";

import {
  AppShell,
} from "./components/AppShell";
import {
  DashboardPage,
} from "./pages/DashboardPage";
import {
  FindingsPage,
} from "./pages/FindingsPage";
import {
  PlaceholderPage,
} from "./pages/PlaceholderPage";
import {
  ProjectsPage,
} from "./pages/ProjectsPage";
import {
  ProjectWorkspacePage,
} from "./pages/ProjectWorkspacePage";
import {
  ReportsPage,
} from "./pages/ReportsPage";
import {
  ScansPage,
} from "./pages/ScansPage";
import {
  SettingsPage,
} from "./pages/SettingsPage";

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route
          index
          element={<DashboardPage />}
        />

        <Route
          path="projects"
          element={<ProjectsPage />}
        />

        <Route
          path="projects/:projectId"
          element={
            <ProjectWorkspacePage />
          }
        />

        <Route
          path="scans"
          element={<ScansPage />}
        />

        <Route
          path="findings"
          element={<FindingsPage />}
        />

        <Route
          path="reports"
          element={<ReportsPage />}
        />

        <Route
          path="settings"
          element={<SettingsPage />}
        />

        <Route
          path="*"
          element={
            <PlaceholderPage
              title="Page not found"
              description="The requested AccessMatrix page does not exist."
            />
          }
        />
      </Route>
    </Routes>
  );
}