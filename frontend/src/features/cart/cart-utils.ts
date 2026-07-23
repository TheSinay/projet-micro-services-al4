import type { CartItem } from "@/api/types";

function round2(value: number): number {
  return Math.round(value * 100) / 100;
}

/** Total of one cart line: (unit price + option deltas) x quantity. */
export function lineTotal(item: CartItem): number {
  const optionsDelta = item.options.reduce((sum, option) => sum + option.price_delta, 0);
  return round2((item.unit_price + optionsDelta) * item.quantity);
}

/** Client-side estimate of the cart subtotal (mirrors the backend pricing rule). */
export function cartSubtotal(items: CartItem[]): number {
  return round2(items.reduce((sum, item) => sum + lineTotal(item), 0));
}

/** Number of articles in the cart (sum of quantities). */
export function cartCount(items: CartItem[]): number {
  return items.reduce((sum, item) => sum + item.quantity, 0);
}
