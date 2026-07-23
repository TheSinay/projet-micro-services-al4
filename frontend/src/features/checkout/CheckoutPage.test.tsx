import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Cart, Order } from "@/api/types";
import { renderWithProviders } from "@/test/test-utils";

// --- Mocks (never touch the real network / router) --------------------------
const navigate = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return { ...actual, useNavigate: () => navigate };
});

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

vi.mock("@/api/orders", () => ({
  placeOrder: vi.fn(),
}));

vi.mock("@/api/users", () => ({
  listAddresses: vi.fn(),
  createAddress: vi.fn(),
}));

vi.mock("@/features/auth/auth-context", () => ({
  useAuth: () => ({
    user: { id: "user-1", name: "Alice", phone: "+33600000000" },
    token: "tok",
    isUserLoading: false,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  }),
}));

vi.mock("@/features/cart/use-cart", () => ({
  useCart: () => cartQueryStub,
}));

import { placeOrder } from "@/api/orders";
import { listAddresses } from "@/api/users";
import { toast } from "sonner";
import { CheckoutPage } from "./CheckoutPage";

const mockedPlaceOrder = vi.mocked(placeOrder);
const mockedListAddresses = vi.mocked(listAddresses);
const mockedToast = vi.mocked(toast);

const cart: Cart = {
  user_id: "user-1",
  restaurant_id: "resto-1",
  items: [
    {
      menu_item_id: "dish-1",
      name: "Pizza Margherita",
      unit_price: 12.5,
      quantity: 1,
      options: [],
    },
  ],
  restaurant_lat: 48.85,
  restaurant_lng: 2.35,
};

let cartQueryStub: {
  data: Cart;
  isPending: boolean;
  isError: boolean;
  refetch: () => void;
};

function makeOrder(overrides: Partial<Order> = {}): Order {
  return {
    id: "order-1",
    user_id: "user-1",
    restaurant_id: "resto-1",
    items: cart.items,
    delivery_address: { lat: 48.855, lng: 2.372 },
    subtotal: 12.5,
    delivery_fee: 2.5,
    total: 15,
    status: "PREPARING",
    saga_state: "CONFIRMED",
    payment_id: "pay-1",
    cancellation_reason: null,
    delivery_id: "del-1",
    created_at: "2026-07-23T12:00:00Z",
    updated_at: "2026-07-23T12:00:00Z",
    ...overrides,
  };
}

async function submitOrder() {
  const user = userEvent.setup();
  await user.click(await screen.findByRole("button", { name: /payer et commander/i }));
}

beforeEach(() => {
  vi.clearAllMocks();
  cartQueryStub = { data: cart, isPending: false, isError: false, refetch: vi.fn() };
  mockedListAddresses.mockResolvedValue([]);
});

describe("CheckoutPage — issue de la saga", () => {
  it("affiche le succès quand la commande aboutit (PREPARING)", async () => {
    mockedPlaceOrder.mockResolvedValue(makeOrder({ status: "PREPARING" }));

    renderWithProviders(<CheckoutPage />);
    await submitOrder();

    await waitFor(() => expect(mockedToast.success).toHaveBeenCalledTimes(1));
    expect(mockedToast.error).not.toHaveBeenCalled();
    expect(navigate).toHaveBeenCalledWith("/orders/order-1", { replace: true });
  });

  it("affiche le succès quand la commande est reçue (RECEIVED)", async () => {
    mockedPlaceOrder.mockResolvedValue(makeOrder({ status: "RECEIVED" }));

    renderWithProviders(<CheckoutPage />);
    await submitOrder();

    await waitFor(() => expect(mockedToast.success).toHaveBeenCalledTimes(1));
    expect(mockedToast.error).not.toHaveBeenCalled();
  });

  it("n'affiche PAS de succès mais un avertissement quand la commande est CANCELLED", async () => {
    mockedPlaceOrder.mockResolvedValue(
      makeOrder({
        status: "CANCELLED",
        saga_state: "CANCELLED_NO_COURIER",
        cancellation_reason: "aucun livreur disponible, remboursement effectué",
      }),
    );

    renderWithProviders(<CheckoutPage />);
    await submitOrder();

    await waitFor(() => expect(mockedToast.error).toHaveBeenCalledTimes(1));
    expect(mockedToast.success).not.toHaveBeenCalled();
    expect(mockedToast.error).toHaveBeenCalledWith(
      "aucun livreur disponible, remboursement effectué",
    );
    // The user is still routed to the detail page to understand what happened.
    expect(navigate).toHaveBeenCalledWith("/orders/order-1", { replace: true });
  });

  it("affiche un message générique quand la commande CANCELLED n'a pas de raison", async () => {
    mockedPlaceOrder.mockResolvedValue(
      makeOrder({ status: "CANCELLED", cancellation_reason: null }),
    );

    renderWithProviders(<CheckoutPage />);
    await submitOrder();

    await waitFor(() => expect(mockedToast.error).toHaveBeenCalledTimes(1));
    expect(mockedToast.success).not.toHaveBeenCalled();
    expect(mockedToast.error).toHaveBeenCalledWith(expect.stringMatching(/n'a pas pu aboutir/i));
  });
});
