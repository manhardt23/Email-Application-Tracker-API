import type { ReactElement } from "react";
import { Navigate } from "react-router-dom";

import { getTokenRole, getValidToken } from "../lib/auth";

export function RequireAuth({ children }: { children: ReactElement }) {
  if (!getValidToken()) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

export function RequireAdmin({ children }: { children: ReactElement }) {
  if (!getValidToken()) {
    return <Navigate to="/login" replace />;
  }
  if (getTokenRole() !== "admin") {
    return <Navigate to="/forbidden" replace />;
  }
  return children;
}
