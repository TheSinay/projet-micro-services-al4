import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { User } from "@/api/types";
import type { AuthContextValue } from "@/features/auth/auth-context";
import { Header } from "@/components/Header";

const useAuthMock = vi.fn<() => AuthContextValue>();
vi.mock("@/features/auth/auth-context", () => ({
  useAuth: () => useAuthMock(),
}));

vi.mock("@/features/cart/use-cart", () => ({
  useCart: () => ({ data: undefined }),
}));

vi.mock("@/features/cart/CartSheet", () => ({
  CartSheet: () => <div data-testid="cart-sheet" />,
}));

function makeAuth(user: User | null): AuthContextValue {
  return {
    token: user ? "tok" : null,
    user,
    isUserLoading: false,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  };
}

function makeUser(role: User["role"]): User {
  return { id: "u1", email: "u@example.com", name: "Test User", phone: "0600000000", role };
}

function renderHeader() {
  return render(
    <MemoryRouter>
      <Header />
    </MemoryRouter>,
  );
}

describe("Header", () => {
  beforeEach(() => {
    useAuthMock.mockReset();
  });

  it("affiche la connexion et le lien QA pour un visiteur non connecté", () => {
    useAuthMock.mockReturnValue(makeAuth(null));

    renderHeader();

    expect(screen.getByText("QA Testeur")).toBeInTheDocument();
    expect(screen.getByText("Connexion")).toBeInTheDocument();
    expect(screen.getByText("Créer un compte")).toBeInTheDocument();
    expect(screen.queryByText("Mes commandes")).not.toBeInTheDocument();
  });

  it("montre panier et commandes pour un client", () => {
    useAuthMock.mockReturnValue(makeAuth(makeUser("client")));

    renderHeader();

    expect(screen.getByText("Mes commandes")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /ouvrir le panier/i })).toBeInTheDocument();
    expect(screen.getByTestId("cart-sheet")).toBeInTheDocument();
    expect(screen.queryByText("Espace Restaurateur")).not.toBeInTheDocument();
    expect(screen.queryByText("Espace Livreur")).not.toBeInTheDocument();
  });

  it("montre l'espace restaurateur sans panier pour un restaurateur", () => {
    useAuthMock.mockReturnValue(makeAuth(makeUser("restaurant_owner")));

    renderHeader();

    expect(screen.getByText("Espace Restaurateur")).toBeInTheDocument();
    expect(screen.queryByText("Mes commandes")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /ouvrir le panier/i })).not.toBeInTheDocument();
    expect(screen.queryByTestId("cart-sheet")).not.toBeInTheDocument();
  });

  it("montre l'espace livreur sans panier pour un livreur", () => {
    useAuthMock.mockReturnValue(makeAuth(makeUser("courier")));

    renderHeader();

    expect(screen.getByText("Espace Livreur")).toBeInTheDocument();
    expect(screen.queryByText("Mes commandes")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /ouvrir le panier/i })).not.toBeInTheDocument();
    expect(screen.queryByTestId("cart-sheet")).not.toBeInTheDocument();
  });
});
