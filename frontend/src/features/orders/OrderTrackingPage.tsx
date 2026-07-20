import { useQuery } from "@tanstack/react-query";
import { MapPin } from "lucide-react";
import { useParams } from "react-router-dom";

import * as ordersApi from "@/api/orders";
import { ErrorState } from "@/components/ErrorState";
import { PageSkeleton } from "@/components/PageSkeleton";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { lineTotal } from "@/features/cart/cart-utils";
import { OrderStatusBadge } from "@/features/orders/OrderStatusBadge";
import { OrderStatusTimeline } from "@/features/orders/OrderStatusTimeline";
import { formatDateTime, formatPrice, shortId } from "@/lib/format";

/** Polling period while the order is still moving through its lifecycle. */
const TRACKING_REFETCH_INTERVAL_MS = 4000;

export function OrderTrackingPage() {
  const { id } = useParams<{ id: string }>();

  const orderQuery = useQuery({
    queryKey: ["order", id],
    queryFn: () => ordersApi.getOrder(id!),
    enabled: id !== undefined,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      // Terminal states: stop polling.
      return status === "DELIVERED" || status === "CANCELLED"
        ? false
        : TRACKING_REFETCH_INTERVAL_MS;
    },
  });

  if (orderQuery.isPending) {
    return <PageSkeleton blocks={3} />;
  }

  if (orderQuery.isError) {
    return (
      <ErrorState
        message="Impossible de charger cette commande."
        onRetry={() => void orderQuery.refetch()}
      />
    );
  }

  const order = orderQuery.data;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="font-display text-3xl font-bold">Commande #{shortId(order.id)}</h1>
        <OrderStatusBadge status={order.status} />
      </div>
      <p className="text-sm text-muted-foreground">Passée le {formatDateTime(order.created_at)}</p>

      <div className="grid gap-6 lg:grid-cols-[1fr_24rem]">
        <Card>
          <CardHeader>
            <CardTitle className="text-xl">Suivi en temps réel</CardTitle>
          </CardHeader>
          <CardContent>
            <OrderStatusTimeline status={order.status} />
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-xl">Détail</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <ul className="space-y-2">
                {order.items.map((item) => (
                  <li key={item.menu_item_id} className="flex justify-between gap-2 text-sm">
                    <span>
                      {item.name} × {item.quantity}
                      {item.options.length > 0 ? (
                        <span className="block text-xs text-muted-foreground">
                          {item.options.map((option) => option.name).join(", ")}
                        </span>
                      ) : null}
                    </span>
                    <span className="whitespace-nowrap">{formatPrice(lineTotal(item))}</span>
                  </li>
                ))}
              </ul>
              <Separator />
              <dl className="space-y-1 text-sm">
                <div className="flex justify-between">
                  <dt>Sous-total</dt>
                  <dd>{formatPrice(order.subtotal)}</dd>
                </div>
                <div className="flex justify-between">
                  <dt>Frais de livraison</dt>
                  <dd>{formatPrice(order.delivery_fee)}</dd>
                </div>
                <div className="flex justify-between text-base font-semibold">
                  <dt>Total</dt>
                  <dd>{formatPrice(order.total)}</dd>
                </div>
              </dl>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-xl">Livraison</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="flex items-start gap-2 text-sm">
                <MapPin
                  className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground"
                  aria-hidden="true"
                />
                <span>
                  {order.delivery_address.label ? (
                    <span className="block font-medium">{order.delivery_address.label}</span>
                  ) : null}
                  {[order.delivery_address.street, order.delivery_address.city]
                    .filter(Boolean)
                    .join(", ") || "Adresse repérée par coordonnées GPS"}
                </span>
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
