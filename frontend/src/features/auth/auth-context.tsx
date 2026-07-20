import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { UNAUTHORIZED_EVENT } from "@/api/client";
import type { RegisterPayload, User } from "@/api/types";
import * as usersApi from "@/api/users";
import { clearToken, getToken, setToken } from "@/lib/auth-storage";

export interface AuthContextValue {
  token: string | null;
  /** Authenticated profile (null while loading or logged out). */
  user: User | null;
  isUserLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(() => getToken());
  const queryClient = useQueryClient();

  // The API client dispatches this event on 401: the session is over.
  useEffect(() => {
    const onUnauthorized = () => setTokenState(null);
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
  }, []);

  const { data: user, isLoading } = useQuery({
    queryKey: ["me", token],
    queryFn: usersApi.getProfile,
    enabled: token !== null,
    staleTime: Number.POSITIVE_INFINITY,
    retry: false,
  });

  const login = useCallback(async (email: string, password: string) => {
    const { access_token } = await usersApi.login({ email, password });
    setToken(access_token);
    setTokenState(access_token);
  }, []);

  const register = useCallback(
    async (payload: RegisterPayload) => {
      await usersApi.register(payload);
      await login(payload.email, payload.password);
    },
    [login],
  );

  const logout = useCallback(() => {
    clearToken();
    setTokenState(null);
    queryClient.clear();
  }, [queryClient]);

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      user: user ?? null,
      isUserLoading: token !== null && isLoading,
      login,
      register,
      logout,
    }),
    [token, user, isLoading, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === null) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
