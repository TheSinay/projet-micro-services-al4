import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { User, UserRole } from "@/api/types";
import type { AuthContextValue } from "@/features/auth/auth-context";
import { LoginPage } from "@/features/auth/LoginPage";

let currentUser: User | null = null;
let profileToLoad: User | null = null;

const login = vi.fn(async () => {
  currentUser = profileToLoad;
});

vi.mock("@/features/auth/auth-context", () => ({
  useAuth: (): AuthContextValue => ({
    token: currentUser ? "tok" : null,
    user: currentUser,
    isUserLoading: false,
    login,
    register: vi.fn(),
    logout: vi.fn(),
  }),
}));

function makeUser(role: UserRole): User {
  return { id: "u1", email: "u@example.com", name: "Test", phone: "0600000000", role };
}

function renderLogin(initialEntry: { pathname: string; state?: unknown } = { pathname: "/login" }) {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<p>Accueil client</p>} />
        <Route path="/restaurant/dashboard" element={<p>Espace restaurateur</p>} />
        <Route path="/courier/dashboard" element={<p>Espace livreur</p>} />
        <Route path="/orders" element={<p>Mes commandes</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

async function submitCredentials() {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText(/adresse e-mail/i), "u@example.com");
  await user.type(screen.getByLabelText(/mot de passe/i), "Password123!");
  await user.click(screen.getByRole("button", { name: /se connecter/i }));
}

describe("LoginPage", () => {
  beforeEach(() => {
    currentUser = null;
    profileToLoad = null;
    login.mockClear();
  });

  it("affiche le formulaire de connexion", () => {
    renderLogin();

    expect(screen.getByLabelText(/adresse e-mail/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/mot de passe/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /se connecter/i })).toBeInTheDocument();
  });

  it("redirige un client vers l'accueil après connexion", async () => {
    profileToLoad = makeUser("client");
    renderLogin();

    await submitCredentials();

    expect(await screen.findByText("Accueil client")).toBeInTheDocument();
    expect(login).toHaveBeenCalledWith("u@example.com", "Password123!");
  });

  it("redirige un restaurateur vers son espace après connexion", async () => {
    profileToLoad = makeUser("restaurant_owner");
    renderLogin();

    await submitCredentials();

    expect(await screen.findByText("Espace restaurateur")).toBeInTheDocument();
  });

  it("redirige un livreur vers son espace après connexion", async () => {
    profileToLoad = makeUser("courier");
    renderLogin();

    await submitCredentials();

    expect(await screen.findByText("Espace livreur")).toBeInTheDocument();
  });

  it("honore l'origine demandée quand le rôle l'autorise", async () => {
    profileToLoad = makeUser("client");
    renderLogin({ pathname: "/login", state: { from: "/orders" } });

    await submitCredentials();

    expect(await screen.findByText("Mes commandes")).toBeInTheDocument();
  });
});
