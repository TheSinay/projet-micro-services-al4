import { apiClient } from "@/api/client";
import type {
  Address,
  AddressPayload,
  LoginPayload,
  RegisterPayload,
  TokenResponse,
  User,
} from "@/api/types";

export async function register(payload: RegisterPayload): Promise<User> {
  const { data } = await apiClient.post<User>("/api/v1/users", payload);
  return data;
}

export async function login(payload: LoginPayload): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>("/api/v1/auth/login", payload);
  return data;
}

export async function getProfile(): Promise<User> {
  const { data } = await apiClient.get<User>("/api/v1/users/me");
  return data;
}

export async function listAddresses(): Promise<Address[]> {
  const { data } = await apiClient.get<Address[]>("/api/v1/users/me/addresses");
  return data;
}

export async function createAddress(payload: AddressPayload): Promise<Address> {
  const { data } = await apiClient.post<Address>("/api/v1/users/me/addresses", payload);
  return data;
}

export async function deleteAddress(addressId: string): Promise<void> {
  await apiClient.delete(`/api/v1/users/me/addresses/${addressId}`);
}
