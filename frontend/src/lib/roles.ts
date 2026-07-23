import type { UserRole } from "@/api/types";

/** Landing route for each role after login or when a route is off-limits. */
export function homePathForRole(role: UserRole): string {
  switch (role) {
    case "restaurant_owner":
      return "/restaurant/dashboard";
    case "courier":
      return "/courier/dashboard";
    case "client":
    default:
      return "/";
  }
}

/** Whether a route path is reachable by the given role. */
export function isPathAllowedForRole(path: string, role: UserRole): boolean {
  const isRestaurantSpace = path.startsWith("/restaurant/dashboard");
  const isCourierSpace = path.startsWith("/courier/dashboard");

  switch (role) {
    case "restaurant_owner":
      return isRestaurantSpace;
    case "courier":
      return isCourierSpace;
    case "client":
    default:
      // Clients may reach any non-professional route.
      return !isRestaurantSpace && !isCourierSpace;
  }
}

/**
 * Resolve where to send a user right after login: honour the originally
 * requested route when the role allows it, otherwise fall back to its home.
 */
export function resolvePostLoginPath(role: UserRole, from?: string | null): string {
  if (from && from !== "/login" && isPathAllowedForRole(from, role)) {
    return from;
  }
  return homePathForRole(role);
}
