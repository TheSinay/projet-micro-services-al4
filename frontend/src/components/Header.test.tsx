import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Header } from "@/components/Header";
import { AuthProvider } from "@/features/auth/auth-context";
import { renderWithProviders } from "@/test/test-utils";

describe("Header component", () => {
  it("renders brand name and QA Testeur link", () => {
    renderWithProviders(
      <AuthProvider>
        <Header />
      </AuthProvider>,
    );

    expect(screen.getByText("Miam")).toBeInTheDocument();
    expect(screen.getByText("Go")).toBeInTheDocument();
    expect(screen.getByText("QA Testeur")).toBeInTheDocument();
    expect(screen.getByText("Connexion")).toBeInTheDocument();
  });
});
