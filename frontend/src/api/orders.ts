import { apiClient } from "@/api/client";
import type { AddCartItemPayload, Cart, Order, PlaceOrderPayload } from "@/api/types";

// --- Cart -------------------------------------------------------------------

export async function getCart(userId: string): Promise<Cart> {
  const { data } = await apiClient.get<Cart>(`/api/v1/carts/${userId}`);
  return data;
}

export async function addCartItem(userId: string, payload: AddCartItemPayload): Promise<Cart> {
  const { data } = await apiClient.post<Cart>(`/api/v1/carts/${userId}/items`, payload);
  return data;
}

export async function removeCartItem(userId: string, menuItemId: string): Promise<Cart> {
  const { data } = await apiClient.delete<Cart>(`/api/v1/carts/${userId}/items/${menuItemId}`);
  return data;
}

export async function clearCart(userId: string): Promise<void> {
  await apiClient.delete(`/api/v1/carts/${userId}`);
}

// --- Orders ------------------------------------------------------------------

export async function placeOrder(payload: PlaceOrderPayload): Promise<Order> {
  const { data } = await apiClient.post<Order>("/api/v1/orders", payload);
  return data;
}

export async function listOrders(userId: string): Promise<Order[]> {
  const { data } = await apiClient.get<Order[]>("/api/v1/orders", {
    params: { user_id: userId },
  });
  return data;
}

export async function getOrder(orderId: string): Promise<Order> {
  const { data } = await apiClient.get<Order>(`/api/v1/orders/${orderId}`);
  return data;
}

export async function updateOrderStatus(orderId: string, status: string): Promise<Order> {
  const { data } = await apiClient.patch<Order>(`/api/v1/orders/${orderId}/status`, { status });
  return data;
}

// --- Deliveries & Couriers ---------------------------------------------------

export interface Courier {
  id: string;
  name: string;
  phone: string;
  available: boolean;
  lat: number;
  lng: number;
}

export interface Delivery {
  id: string;
  order_id: string;
  courier_id: string | null;
  status: "ASSIGNED" | "PICKED_UP" | "DELIVERED" | "FAILED";
  pickup_address: string | null;
  delivery_address: string;
  created_at: string;
  updated_at: string;
}

export async function listDeliveries(orderId?: string): Promise<Delivery[]> {
  const { data } = await apiClient.get<Delivery[]>("/api/v1/deliveries", {
    params: orderId ? { order_id: orderId } : {},
  });
  return data;
}

export async function updateDeliveryStatus(
  deliveryId: string,
  status: "ASSIGNED" | "PICKED_UP" | "DELIVERED" | "FAILED",
): Promise<Delivery> {
  const { data } = await apiClient.patch<Delivery>(`/api/v1/deliveries/${deliveryId}`, { status });
  return data;
}

export async function listCouriers(): Promise<Courier[]> {
  const { data } = await apiClient.get<Courier[]>("/api/v1/couriers");
  return data;
}

export async function createCourier(payload: {
  name: string;
  phone: string;
  lat: number;
  lng: number;
  available?: boolean;
}): Promise<Courier> {
  const { data } = await apiClient.post<Courier>("/api/v1/couriers", payload);
  return data;
}
