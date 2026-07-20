import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "@/features/auth/auth-context";

/** Route guard: unauthenticated visitors are sent to the login page. */
export function RequireAuth() {
  const { token } = useAuth();
  const location = useLocation();

  if (token === null) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <Outlet />;
}
