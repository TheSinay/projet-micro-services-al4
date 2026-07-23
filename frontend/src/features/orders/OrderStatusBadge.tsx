import type { OrderStatus } from "@/api/types";
import { Badge } from "@/components/ui/badge";

export const ORDER_STATUS_LABELS: Record<OrderStatus, string> = {
  RECEIVED: "Reçue",
  PREPARING: "En préparation",
  DELIVERING: "En livraison",
  DELIVERED: "Livrée",
  CANCELLED: "Annulée",
};

const STATUS_VARIANTS: Record<
  OrderStatus,
  "secondary" | "warning" | "info" | "success" | "destructive"
> = {
  RECEIVED: "secondary",
  PREPARING: "warning",
  DELIVERING: "info",
  DELIVERED: "success",
  CANCELLED: "destructive",
};

export function OrderStatusBadge({ status }: { status: OrderStatus }) {
  return <Badge variant={STATUS_VARIANTS[status]}>{ORDER_STATUS_LABELS[status]}</Badge>;
}
