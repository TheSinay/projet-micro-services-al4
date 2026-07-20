import { apiClient } from "@/api/client";
import type { Restaurant, RestaurantDetail, RestaurantSearchParams } from "@/api/types";

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
