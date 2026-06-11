import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "./components/AppShell";
import { RequireAdmin, RequireAuth } from "./components/guards";
import { ApplicationDetail } from "./pages/ApplicationDetail";
import { Applications } from "./pages/Applications";
import { Dashboard } from "./pages/Dashboard";
import { Emails } from "./pages/Emails";
import { Forbidden } from "./pages/Forbidden";
import { JobsAdmin } from "./pages/JobsAdmin";
import { Login } from "./pages/Login";
import { ReviewQueue } from "./pages/ReviewQueue";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      <Route
        element={
          <RequireAuth>
            <AppShell />
          </RequireAuth>
        }
      >
        <Route
          index
          element={
            <RequireAdmin>
              <Dashboard />
            </RequireAdmin>
          }
        />
        <Route
          path="applications"
          element={
            <RequireAdmin>
              <Applications />
            </RequireAdmin>
          }
        />
        <Route
          path="applications/:id"
          element={
            <RequireAdmin>
              <ApplicationDetail />
            </RequireAdmin>
          }
        />
        <Route
          path="emails"
          element={
            <RequireAdmin>
              <Emails />
            </RequireAdmin>
          }
        />
        <Route path="review" element={<ReviewQueue />} />
        <Route
          path="jobs"
          element={
            <RequireAdmin>
              <JobsAdmin />
            </RequireAdmin>
          }
        />
        <Route path="forbidden" element={<Forbidden />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
