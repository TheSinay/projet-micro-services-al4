import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { User } from "@/api/types";
import type { AuthContextValue } from "@/features/auth/auth-context";
import { RequireRole } from "@/features/auth/RequireRole";

const toastError = vi.fn();
vi.mock("sonner", () => ({
  toast: { error: (msg: string) => toastError(msg) },
}));

const useAuthMock = vi.fn<() => AuthContextValue>();
vi.mock("@/features/auth/auth-context", () => ({
  useAuth: () => useAuthMock(),
}));

function makeAuth(overrides: Partial<AuthContextValue>): AuthContextValue {
  return {
    token: null,
    user: null,
    isUserLoading: false,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
    ...overrides,
  };
}

function makeUser(role: User["role"]): User {
  return { id: "u1", email: "u@example.com", name: "Test", phone: "0600000000", role };
}

function renderGuard(allow: User["role"][], route = "/orders") {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <Routes>
        <Route element={<RequireRole allow={allow} />}>
          <Route path="/orders" element={<p>Contenu protégé</p>} />
        </Route>
        <Route path="/login" element={<p>Page de connexion</p>} />
        <Route path="/" element={<p>Accueil client</p>} />
        <Route path="/restaurant/dashboard" element={<p>Espace restaurateur</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("RequireRole", () => {
  beforeEach(() => {
    toastError.mockClear();
    useAuthMock.mockReset();
  });

  it("redirige un visiteur non connecté vers la page de connexion", () => {
    useAuthMock.mockReturnValue(makeAuth({ token: null }));

    renderGuard(["client"]);

    expect(screen.getByText("Page de connexion")).toBeInTheDocument();
    expect(screen.queryByText("Contenu protégé")).not.toBeInTheDocument();
  });

  it("affiche un état de chargement pendant le chargement du profil", () => {
    useAuthMock.mockReturnValue(makeAuth({ token: "tok", isUserLoading: true }));

    renderGuard(["client"]);

    expect(screen.getByLabelText("Chargement en cours")).toBeInTheDocument();
    expect(screen.queryByText("Contenu protégé")).not.toBeInTheDocument();
  });

  it("rend le contenu pour un rôle autorisé", () => {
    useAuthMock.mockReturnValue(makeAuth({ token: "tok", user: makeUser("client") }));

    renderGuard(["client"]);

    expect(screen.getByText("Contenu protégé")).toBeInTheDocument();
  });

  it("redirige un rôle non autorisé vers son accueil et affiche un toast", () => {
    useAuthMock.mockReturnValue(makeAuth({ token: "tok", user: makeUser("restaurant_owner") }));

    renderGuard(["client"]);

    expect(screen.getByText("Espace restaurateur")).toBeInTheDocument();
    expect(screen.queryByText("Contenu protégé")).not.toBeInTheDocument();
    expect(toastError).toHaveBeenCalledWith("Accès non autorisé pour votre profil.");
  });
});
