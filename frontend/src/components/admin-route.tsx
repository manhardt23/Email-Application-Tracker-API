import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";

import { getTokenRole, getValidToken } from "../lib/auth";

type AdminRouteProps = {
  children: ReactNode;
};

export function AdminRoute({ children }: AdminRouteProps) {
  const token = getValidToken();
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  if (getTokenRole() !== "admin") {
    return <Navigate to="/forbidden" replace />;
  }
  return children;
}
