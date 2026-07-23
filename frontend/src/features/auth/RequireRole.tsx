import { useEffect } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { toast } from "sonner";

import type { UserRole } from "@/api/types";
import { PageSkeleton } from "@/components/PageSkeleton";
import { useAuth } from "@/features/auth/auth-context";
import { homePathForRole } from "@/lib/roles";

interface RequireRoleProps {
  /** Roles allowed to view the guarded routes. */
  allow: UserRole[];
}

/**
 * Route guard combining authentication and role checks.
 *
 * - Not logged in -> redirect to /login (keeping the target as state.from).
 * - Profile still loading -> show a loading placeholder.
 * - Logged in but role not allowed -> redirect to the role's home + toast.
 * - Otherwise render the nested routes.
 */
export function RequireRole({ allow }: RequireRoleProps) {
  const { token, user, isUserLoading } = useAuth();
  const location = useLocation();

  const isDenied = user !== null && !allow.includes(user.role);

  useEffect(() => {
    if (isDenied) {
      toast.error("Accès non autorisé pour votre profil.");
    }
  }, [isDenied]);

  if (token === null) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  if (isUserLoading || user === null) {
    return <PageSkeleton />;
  }

  if (isDenied) {
    return <Navigate to={homePathForRole(user.role)} replace />;
  }

  return <Outlet />;
}
