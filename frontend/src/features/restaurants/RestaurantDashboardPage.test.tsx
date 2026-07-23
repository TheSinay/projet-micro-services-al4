import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { KitchenTicket } from "@/api/restaurants";
import type { RestaurantDetail } from "@/api/types";
import { renderWithProviders } from "@/test/test-utils";

// --- Mock the API layer (never call the real network) ----------------------
vi.mock("@/api/restaurants", () => ({
  searchRestaurants: vi.fn(),
  getRestaurant: vi.fn(),
  createRestaurant: vi.fn(),
  createMenuItem: vi.fn(),
  updateMenuItem: vi.fn(),
  deleteMenuItem: vi.fn(),
  listKitchenTickets: vi.fn(),
  updateKitchenTicketStatus: vi.fn(),
}));

// --- Mock the auth context (component reads user only) ----------------------
vi.mock("@/features/auth/auth-context", () => ({
  useAuth: () => ({
    user: { id: "owner-1", name: "Mario", phone: "+33711223344" },
    token: "tok",
    isUserLoading: false,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  }),
}));

import {
  getRestaurant,
  listKitchenTickets,
  searchRestaurants,
  updateKitchenTicketStatus,
} from "@/api/restaurants";
import { RestaurantDashboardPage } from "./RestaurantDashboardPage";

const mockedSearch = vi.mocked(searchRestaurants);
const mockedGetRestaurant = vi.mocked(getRestaurant);
const mockedListTickets = vi.mocked(listKitchenTickets);
const mockedUpdateTicket = vi.mocked(updateKitchenTicketStatus);

const restaurant = {
  id: "resto-1",
  name: "La Bella Napoli",
  cuisine_type: "italian",
  address: "15 rue de Paris, 75001 Paris",
  lat: 48.8566,
  lng: 2.3522,
  opening_hours: [],
  auto_accept: true,
  owner_id: "owner-1",
};

const restaurantDetail: RestaurantDetail = {
  ...restaurant,
  menu: [
    {
      id: "dish-1",
      restaurant_id: "resto-1",
      name: "Pizza Margherita",
      description: "Tomate, mozzarella, basilic",
      price: 12.5,
      options: [],
      available: true,
    },
  ],
};

function makeTicket(overrides: Partial<KitchenTicket> = {}): KitchenTicket {
  return {
    id: "ticket-abcdef",
    order_id: "order-123456",
    restaurant_id: "resto-1",
    status: "ACCEPTED",
    items: [{ menu_item_id: "dish-1", quantity: 2 }],
    created_at: "2026-07-23T12:00:00Z",
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  mockedSearch.mockResolvedValue([restaurant]);
  mockedGetRestaurant.mockResolvedValue(restaurantDetail);
  mockedListTickets.mockResolvedValue([]);
});

describe("RestaurantDashboardPage — suivi cuisine", () => {
  it("affiche un ticket avec le nom du plat résolu et un libellé de statut clair", async () => {
    mockedListTickets.mockResolvedValue([makeTicket()]);

    renderWithProviders(<RestaurantDashboardPage />);

    expect(await screen.findByText(/Commande #123456/)).toBeInTheDocument();
    // Le nom du plat apparaît dans le ticket (et aussi dans la carte menu)
    expect(screen.getAllByText(/Pizza Margherita/).length).toBeGreaterThan(0);
    expect(screen.getByText("2 ×")).toBeInTheDocument();
    expect(screen.getByText("Acceptée")).toBeInTheDocument();
    expect(screen.queryByText("ACCEPTED")).not.toBeInTheDocument();
  });

  it("affiche le bouton « Commencer la préparation » à l'état ACCEPTED", async () => {
    mockedListTickets.mockResolvedValue([makeTicket({ status: "ACCEPTED" })]);

    renderWithProviders(<RestaurantDashboardPage />);

    expect(
      await screen.findByRole("button", { name: /commencer la préparation/i }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /marquer prête/i })).not.toBeInTheDocument();
  });

  it("affiche le bouton « Marquer prête » à l'état PREPARING", async () => {
    mockedListTickets.mockResolvedValue([makeTicket({ status: "PREPARING" })]);

    renderWithProviders(<RestaurantDashboardPage />);

    expect(await screen.findByRole("button", { name: /marquer prête/i })).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /commencer la préparation/i }),
    ).not.toBeInTheDocument();
  });

  it("affiche l'attente du livreur pour un ticket READY, sans bouton d'action", async () => {
    mockedListTickets.mockResolvedValue([makeTicket({ status: "READY" })]);

    renderWithProviders(<RestaurantDashboardPage />);

    expect(await screen.findByText(/en attente du livreur/i)).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /commencer la préparation|marquer prête/i }),
    ).not.toBeInTheDocument();
  });

  it("affiche un état vide quand la cuisine n'a aucune commande", async () => {
    mockedListTickets.mockResolvedValue([]);

    renderWithProviders(<RestaurantDashboardPage />);

    await waitFor(() =>
      expect(screen.getByText(/aucune commande en cuisine pour le moment/i)).toBeInTheDocument(),
    );
  });

  it("déclenche le PATCH PREPARING au clic sur « Commencer la préparation »", async () => {
    mockedListTickets.mockResolvedValue([makeTicket({ status: "ACCEPTED" })]);
    mockedUpdateTicket.mockResolvedValue(makeTicket({ status: "PREPARING" }));

    renderWithProviders(<RestaurantDashboardPage />);

    const button = await screen.findByRole("button", { name: /commencer la préparation/i });
    await userEvent.click(button);

    await waitFor(() =>
      expect(mockedUpdateTicket).toHaveBeenCalledWith("ticket-abcdef", "PREPARING"),
    );
  });

  it("déclenche le PATCH READY au clic sur « Marquer prête »", async () => {
    mockedListTickets.mockResolvedValue([makeTicket({ status: "PREPARING" })]);
    mockedUpdateTicket.mockResolvedValue(makeTicket({ status: "READY" }));

    renderWithProviders(<RestaurantDashboardPage />);

    const button = await screen.findByRole("button", { name: /marquer prête/i });
    await userEvent.click(button);

    await waitFor(() => expect(mockedUpdateTicket).toHaveBeenCalledWith("ticket-abcdef", "READY"));
  });
});
