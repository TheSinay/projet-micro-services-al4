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
