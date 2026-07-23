import { screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Courier, Delivery } from "@/api/orders";
import { renderWithProviders } from "@/test/test-utils";

// --- Mock the API layer (never call the real network) ----------------------
vi.mock("@/api/orders", () => ({
  listDeliveries: vi.fn(),
  listCouriers: vi.fn(),
  updateDeliveryStatus: vi.fn(),
  createCourier: vi.fn(),
}));

// --- Mock the auth context (component reads user only) ----------------------
vi.mock("@/features/auth/auth-context", () => ({
  useAuth: () => ({
    user: { id: "u1", name: "Bob", phone: "+33711223344" },
    token: "tok",
    isUserLoading: false,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  }),
}));

import { listCouriers, listDeliveries } from "@/api/orders";
import { CourierDashboardPage } from "./CourierDashboardPage";

const mockedListDeliveries = vi.mocked(listDeliveries);
const mockedListCouriers = vi.mocked(listCouriers);

const courier: Courier = {
  id: "c1",
  name: "Bob",
  phone: "+33711223344",
  available: true,
  location: { lat: 48.8566, lng: 2.3522 },
};

function makeDelivery(overrides: Partial<Delivery> = {}): Delivery {
  return {
    id: "delivery-abcdef",
    order_id: "order-123456",
    courier_id: "c1",
    status: "ACCEPTED",
    pickup_address: { label: "15 rue de Paris, 75001 Paris", lat: 48.8566, lng: 2.3522 },
    dropoff_address: { label: "8 avenue Client, 75010 Paris", lat: 48.87, lng: 2.36 },
    events: [{ status: "ACCEPTED", at: "2026-07-22T10:00:00Z" }],
    created_at: "2026-07-22T10:00:00Z",
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  mockedListCouriers.mockResolvedValue([courier]);
});

describe("CourierDashboardPage", () => {
  it("affiche une livraison ACCEPTED sans crash, avec les adresses via label", async () => {
    mockedListDeliveries.mockResolvedValue([makeDelivery()]);

    renderWithProviders(<CourierDashboardPage />);

    expect(await screen.findByText(/15 rue de Paris/)).toBeInTheDocument();
    expect(screen.getByText(/8 avenue Client/)).toBeInTheDocument();
    // Libellé de statut clair, pas le code brut
    expect(screen.getByText("Prête à récupérer")).toBeInTheDocument();
    expect(screen.queryByText("ACCEPTED")).not.toBeInTheDocument();
  });

  it("affiche des coordonnées lisibles quand l'adresse n'a pas de label", async () => {
    mockedListDeliveries.mockResolvedValue([
      makeDelivery({
        dropoff_address: { label: null, lat: 48.87, lng: 2.36 },
      }),
    ]);

    renderWithProviders(<CourierDashboardPage />);

    expect(await screen.findByText("48.8700, 2.3600")).toBeInTheDocument();
  });

  it("affiche le bouton de prise en charge à l'état ACCEPTED", async () => {
    mockedListDeliveries.mockResolvedValue([makeDelivery({ status: "ACCEPTED" })]);

    renderWithProviders(<CourierDashboardPage />);

    expect(await screen.findByRole("button", { name: /prise en charge/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /valider la livraison/i })).not.toBeInTheDocument();
  });

  it("affiche le bouton de validation à l'état PICKED_UP", async () => {
    mockedListDeliveries.mockResolvedValue([makeDelivery({ status: "PICKED_UP" })]);

    renderWithProviders(<CourierDashboardPage />);

    expect(
      await screen.findByRole("button", { name: /valider la livraison/i }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /prise en charge/i })).not.toBeInTheDocument();
  });

  it("affiche un état vide quand il n'y a aucune livraison", async () => {
    mockedListDeliveries.mockResolvedValue([]);

    renderWithProviders(<CourierDashboardPage />);

    await waitFor(() =>
      expect(screen.getByText(/Aucune livraison en attente/i)).toBeInTheDocument(),
    );
  });
});
