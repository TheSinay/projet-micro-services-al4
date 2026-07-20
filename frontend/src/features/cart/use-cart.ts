import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import * as ordersApi from "@/api/orders";
import type { AddCartItemPayload, Cart } from "@/api/types";
import { useAuth } from "@/features/auth/auth-context";

const cartKey = (userId: string | undefined) => ["cart", userId] as const;

/** Server cart of the authenticated user (disabled while logged out). */
export function useCart() {
  const { user } = useAuth();
  return useQuery({
    queryKey: cartKey(user?.id),
    queryFn: () => ordersApi.getCart(user!.id),
    enabled: user !== null,
  });
}

/** Mutations on the cart; every success refreshes the shared cart cache. */
export function useCartMutations() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const userId = user?.id;

  const setCart = (cart: Cart) => queryClient.setQueryData(cartKey(userId), cart);

  const addItem = useMutation({
    mutationFn: (payload: AddCartItemPayload) => ordersApi.addCartItem(userId!, payload),
    onSuccess: setCart,
  });

  const removeItem = useMutation({
    mutationFn: (menuItemId: string) => ordersApi.removeCartItem(userId!, menuItemId),
    onSuccess: setCart,
  });

  const clear = useMutation({
    mutationFn: () => ordersApi.clearCart(userId!),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cartKey(userId) }),
  });

  return { addItem, removeItem, clear };
}
