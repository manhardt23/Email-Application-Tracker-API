import { Navigate, Route, Routes } from "react-router-dom";

import { AdminRoute } from "./components/admin-route";
import { ProtectedRoute } from "./components/protected-route";
import { ApplicationsPage } from "./pages/applications-page";
import { DashboardPage } from "./pages/dashboard-page";
import { LoginPage } from "./pages/login-page";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/applications"
        element={
          <AdminRoute>
            <ApplicationsPage />
          </AdminRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
