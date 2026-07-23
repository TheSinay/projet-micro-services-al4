import { isAxiosError } from "axios";

const GENERIC_MESSAGE = "Une erreur est survenue. Veuillez réessayer.";
const NETWORK_MESSAGE = "Impossible de contacter le serveur. Vérifiez votre connexion.";

/** True when `error` is an HTTP error with the given status code. */
export function hasStatus(error: unknown, status: number): boolean {
  return isAxiosError(error) && error.response?.status === status;
}

/**
 * Translate an API error into a clear French message for the user.
 * Raw API details are never shown; callers may map specific status codes
 * (e.g. `{ 409: "Un compte existe déjà avec cet e-mail." }`).
 */
export function getErrorMessage(
  error: unknown,
  byStatus: Partial<Record<number, string>> = {},
  fallback: string = GENERIC_MESSAGE,
): string {
  if (isAxiosError(error)) {
    if (!error.response) {
      return NETWORK_MESSAGE;
    }
    const mapped = byStatus[error.response.status];
    if (mapped) {
      return mapped;
    }
  }
  return fallback;
}
