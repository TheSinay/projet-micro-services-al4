/**
 * DTO types mirroring the backend Pydantic schemas (source of truth:
 * services/users, services/restaurants, services/orders — app/schemas/).
 */

// ---------------------------------------------------------------------------
// users service (port 8001)
// ---------------------------------------------------------------------------

/** Application role controlling which views a user may access. */
export type UserRole = "client" | "restaurant_owner" | "courier";

export interface User {
  id: string;
  email: string;
  name: string;
  phone: string;
  role: UserRole;
}

export interface RegisterPayload {
  email: string;
  password: string;
  name: string;
  phone: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface Address {
  id: string;
  label: string;
  street: string;
  city: string;
  lat: number;
  lng: number;
}

export type AddressPayload = Omit<Address, "id">;

// ---------------------------------------------------------------------------
// restaurants service (port 8002)
// ---------------------------------------------------------------------------

/** Weekly opening slot; `day` uses 0 = Monday … 6 = Sunday. */
export interface OpeningHour {
  day: number;
  open: string;
  close: string;
}

export interface Restaurant {
  id: string;
  name: string;
  cuisine_type: string;
  address: string;
  lat: number;
  lng: number;
  opening_hours: OpeningHour[];
  auto_accept: boolean;
  owner_id?: string;
}

export interface MenuItemOption {
  name: string;
  price_delta: number;
}

export interface MenuItem {
  id: string;
  restaurant_id: string;
  name: string;
  description: string;
  price: number;
  options: MenuItemOption[];
  available: boolean;
}

export interface RestaurantDetail extends Restaurant {
  menu: MenuItem[];
}

export interface RestaurantSearchParams {
  cuisine?: string;
  q?: string;
  lat?: number;
  lng?: number;
  radius_km?: number;
}

// ---------------------------------------------------------------------------
// orders service (port 8003)
// ---------------------------------------------------------------------------

export interface CartItemOption {
  name: string;
  price_delta: number;
}

export interface CartItem {
  menu_item_id: string;
  name: string;
  unit_price: number;
  quantity: number;
  options: CartItemOption[];
}

export interface Cart {
  user_id: string;
  restaurant_id: string | null;
  items: CartItem[];
  restaurant_lat: number | null;
  restaurant_lng: number | null;
}

export interface AddCartItemPayload {
  restaurant_id: string;
  menu_item_id: string;
  name: string;
  unit_price: number;
  quantity: number;
  options: CartItemOption[];
  restaurant_lat?: number;
  restaurant_lng?: number;
}

export const ORDER_STATUSES = [
  "RECEIVED",
  "PREPARING",
  "DELIVERING",
  "DELIVERED",
  "CANCELLED",
] as const;

export type OrderStatus = (typeof ORDER_STATUSES)[number];

export interface DeliveryAddress {
  lat: number;
  lng: number;
  label?: string | null;
  street?: string | null;
  city?: string | null;
}

export interface PlaceOrderPayload {
  user_id: string;
  delivery_address: DeliveryAddress;
  restaurant_lat?: number;
  restaurant_lng?: number;
}

export interface Order {
  id: string;
  user_id: string;
  restaurant_id: string;
  items: CartItem[];
  delivery_address: DeliveryAddress;
  subtotal: number;
  delivery_fee: number;
  total: number;
  status: OrderStatus;
  saga_state: string;
  payment_id: string | null;
  delivery_id: string | null;
  created_at: string;
  updated_at: string;
}
