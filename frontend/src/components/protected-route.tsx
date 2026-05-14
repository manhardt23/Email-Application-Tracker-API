import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";

import { getValidToken } from "../lib/auth";

type ProtectedRouteProps = {
  children: ReactNode;
};

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const token = getValidToken();
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;
}
