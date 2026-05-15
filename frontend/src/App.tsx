import { Navigate, Route, Routes } from "react-router-dom";

import { AdminRoute } from "./components/admin-route";
import { AppNavbar } from "./components/app-navbar";
import { ApplicationsPage } from "./pages/applications-page";
import { DashboardPage } from "./pages/dashboard-page";
import { ForbiddenPage } from "./pages/forbidden-page";
import { LoginPage } from "./pages/login-page";

export default function App() {
  return (
    <main className="min-h-screen bg-slate-100 p-4 md:p-8">
      <div className="mx-auto max-w-6xl">
        <AppNavbar />
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<DashboardPage />} />
          <Route
            path="/applications"
            element={
              <AdminRoute>
                <ApplicationsPage />
              </AdminRoute>
            }
          />
          <Route path="/forbidden" element={<ForbiddenPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </main>
  );
}
