import { Navigate, Route, Routes } from "react-router-dom";

import { ProtectedRoute } from "./components/protected-route";
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
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
