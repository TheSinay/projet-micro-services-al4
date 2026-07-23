import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AuthProvider } from "@/features/auth/auth-context";
import { TesterDashboardPage } from "@/features/tester/TesterDashboardPage";
import { renderWithProviders } from "@/test/test-utils";

describe("TesterDashboardPage component", () => {
  it("renders QA tester dashboard elements and service health list", () => {
    renderWithProviders(
      <AuthProvider>
        <TesterDashboardPage />
      </AuthProvider>,
    );

    expect(screen.getByRole("heading", { name: /vue testeur/i })).toBeInTheDocument();
    expect(screen.getByText("Users")).toBeInTheDocument();
    expect(screen.getByText("Restaurants")).toBeInTheDocument();
    expect(screen.getByText("Orders")).toBeInTheDocument();
    expect(screen.getByText("Payments")).toBeInTheDocument();
    expect(screen.getByText(/mode normal/i)).toBeInTheDocument();
    expect(screen.getByText(/simuler pannes psp/i)).toBeInTheDocument();
  });
});
