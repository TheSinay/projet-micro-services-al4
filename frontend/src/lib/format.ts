const priceFormatter = new Intl.NumberFormat("fr-FR", {
  style: "currency",
  currency: "EUR",
});

const dateTimeFormatter = new Intl.DateTimeFormat("fr-FR", {
  dateStyle: "medium",
  timeStyle: "short",
});

/** Format an amount in euros (e.g. `12,50 €`). */
export function formatPrice(amount: number): string {
  return priceFormatter.format(amount);
}

/** Format an ISO date string for display (e.g. `5 juil. 2026, 12:30`). */
export function formatDateTime(iso: string): string {
  return dateTimeFormatter.format(new Date(iso));
}

/** Short human-friendly order reference from its id. */
export function shortId(id: string): string {
  return id.slice(0, 8).toUpperCase();
}
