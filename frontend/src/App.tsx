import type { ReactElement } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { AdminRoute } from "./components/admin-route";
import { AppShell } from "./components/app-shell";
import { ApplicationsPage } from "./pages/applications-page";
import { DashboardPage } from "./pages/dashboard-page";
import { ForbiddenPage } from "./pages/forbidden-page";
import { LoginPage } from "./pages/login-page";

function withShell(element: ReactElement): ReactElement {
  return <AppShell>{element}</AppShell>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={withShell(<DashboardPage />)} />
      <Route
        path="/applications"
        element={withShell(
          <AdminRoute>
            <ApplicationsPage />
          </AdminRoute>,
        )}
      />
      <Route path="/forbidden" element={withShell(<ForbiddenPage />)} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
