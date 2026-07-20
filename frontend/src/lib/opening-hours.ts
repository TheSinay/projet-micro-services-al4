import type { OpeningHour } from "@/api/types";

/**
 * Whether a restaurant is currently open, from its weekly opening slots
 * (`day`: 0 = Monday … 6 = Sunday; times as "HH:MM").
 * Returns `null` when no hours are declared (unknown → no badge shown).
 */
export function isOpenNow(hours: OpeningHour[], now: Date = new Date()): boolean | null {
  if (hours.length === 0) {
    return null;
  }
  // JS getDay(): 0 = Sunday … 6 = Saturday → API convention 0 = Monday.
  const day = (now.getDay() + 6) % 7;
  const time = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
  return hours.some((slot) => slot.day === day && slot.open <= time && time < slot.close);
}
