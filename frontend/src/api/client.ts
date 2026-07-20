import axios, { type InternalAxiosRequestConfig } from "axios";

import { clearToken, getToken } from "@/lib/auth-storage";

/** Dispatched when the API answers 401 outside of the login flow. */
export const UNAUTHORIZED_EVENT = "miamgo:unauthorized";

const LOGIN_URL = "/api/v1/auth/login";

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "",
  headers: { "Content-Type": "application/json" },
});

/** Attach the persisted bearer token to every outgoing request. */
export function attachAuthToken(config: InternalAxiosRequestConfig): InternalAxiosRequestConfig {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}

apiClient.interceptors.request.use(attachAuthToken);

apiClient.interceptors.response.use(undefined, (error: unknown) => {
  // An expired/invalid session anywhere but on the login call logs the user out.
  if (
    axios.isAxiosError(error) &&
    error.response?.status === 401 &&
    error.config?.url !== LOGIN_URL
  ) {
    clearToken();
    window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
  }
  return Promise.reject(error);
});
