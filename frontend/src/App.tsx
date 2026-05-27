import type { ReactElement } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { AdminRoute } from "./components/admin-route";
import { AppShell } from "./components/AppShell";
import { Applications } from "./pages/Applications";
import { Dashboard } from "./pages/Dashboard";
import { ForbiddenPage } from "./pages/forbidden-page";
import { LoginPage } from "./pages/login-page";

function withShell(element: ReactElement): ReactElement {
  return <AppShell>{element}</AppShell>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={withShell(<Dashboard />)} />
      <Route
        path="/applications"
        element={withShell(
          <AdminRoute>
            <Applications />
          </AdminRoute>,
        )}
      />
      <Route path="/forbidden" element={withShell(<ForbiddenPage />)} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
