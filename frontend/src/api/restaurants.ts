import { apiClient } from "@/api/client";
import type { MenuItem, Restaurant, RestaurantDetail, RestaurantSearchParams } from "@/api/types";

export async function searchRestaurants(
  params: RestaurantSearchParams = {},
): Promise<Restaurant[]> {
  const { data } = await apiClient.get<Restaurant[]>("/api/v1/restaurants", { params });
  return data;
}

export async function getRestaurant(restaurantId: string): Promise<RestaurantDetail> {
  const { data } = await apiClient.get<RestaurantDetail>(`/api/v1/restaurants/${restaurantId}`);
  return data;
}

export async function createRestaurant(payload: Omit<Restaurant, "id">): Promise<Restaurant> {
  const { data } = await apiClient.post<Restaurant>("/api/v1/restaurants", payload);
  return data;
}

export async function updateRestaurant(
  restaurantId: string,
  payload: Omit<Restaurant, "id">,
): Promise<Restaurant> {
  const { data } = await apiClient.put<Restaurant>(`/api/v1/restaurants/${restaurantId}`, payload);
  return data;
}

export async function createMenuItem(
  restaurantId: string,
  payload: Omit<MenuItem, "id" | "restaurant_id">,
): Promise<MenuItem> {
  const { data } = await apiClient.post<MenuItem>(
    `/api/v1/restaurants/${restaurantId}/menu-items`,
    payload,
  );
  return data;
}

export async function updateMenuItem(
  restaurantId: string,
  itemId: string,
  payload: Omit<MenuItem, "id" | "restaurant_id">,
): Promise<MenuItem> {
  const { data } = await apiClient.put<MenuItem>(
    `/api/v1/restaurants/${restaurantId}/menu-items/${itemId}`,
    payload,
  );
  return data;
}

export async function deleteMenuItem(restaurantId: string, itemId: string): Promise<void> {
  await apiClient.delete(`/api/v1/restaurants/${restaurantId}/menu-items/${itemId}`);
}

export type KitchenTicketStatus = "ACCEPTED" | "REFUSED" | "PREPARING" | "READY";

export interface KitchenTicketItem {
  menu_item_id: string;
  quantity: number;
}

export interface KitchenTicket {
  id: string;
  order_id: string;
  restaurant_id: string;
  status: KitchenTicketStatus;
  items: KitchenTicketItem[];
  created_at: string;
}

export async function listKitchenTickets(
  restaurantId: string,
  status?: KitchenTicketStatus,
): Promise<KitchenTicket[]> {
  const { data } = await apiClient.get<KitchenTicket[]>(
    `/api/v1/restaurants/${restaurantId}/kitchen-tickets`,
    { params: status ? { status } : undefined },
  );
  return data;
}

export async function updateKitchenTicketStatus(
  ticketId: string,
  status: "PREPARING" | "READY",
): Promise<KitchenTicket> {
  const { data } = await apiClient.patch<KitchenTicket>(`/api/v1/kitchen-tickets/${ticketId}`, {
    status,
  });
  return data;
}
