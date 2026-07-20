import { useQuery } from "@tanstack/react-query";
import { ChevronRight, ReceiptText } from "lucide-react";
import { Link } from "react-router-dom";

import * as ordersApi from "@/api/orders";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { PageSkeleton } from "@/components/PageSkeleton";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useAuth } from "@/features/auth/auth-context";
import { OrderStatusBadge } from "@/features/orders/OrderStatusBadge";
import { formatDateTime, formatPrice, shortId } from "@/lib/format";

export function OrdersHistoryPage() {
  const { user } = useAuth();

  const ordersQuery = useQuery({
    queryKey: ["orders", user?.id],
    queryFn: () => ordersApi.listOrders(user!.id),
    enabled: user !== null,
    // Most recent order first, whatever the API ordering is.
    select: (orders) =>
      [...orders].sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
      ),
  });

  if (ordersQuery.isPending) {
    return <PageSkeleton blocks={4} />;
  }

  if (ordersQuery.isError) {
    return (
      <ErrorState
        message="Impossible de charger vos commandes."
        onRetry={() => void ordersQuery.refetch()}
      />
    );
  }

  const orders = ordersQuery.data;

  return (
    <div className="space-y-6">
      <h1 className="font-display text-3xl font-bold">Mes commandes</h1>

      {orders.length === 0 ? (
        <EmptyState
          icon={ReceiptText}
          title="Aucune commande pour le moment"
          description="Votre première commande apparaîtra ici."
          action={
            <Button asChild>
              <Link to="/">Voir les restaurants</Link>
            </Button>
          }
        />
      ) : (
        <ul className="space-y-3">
          {orders.map((order) => {
            const itemsSummary =
              order.items.length === 1
                ? order.items[0].name
                : `${order.items[0].name} et ${order.items.length - 1} autre${
                    order.items.length > 2 ? "s" : ""
                  }`;
            return (
              <li key={order.id}>
                <Link
                  to={`/orders/${order.id}`}
                  className="block rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                  aria-label={`Voir la commande ${shortId(order.id)}`}
                >
                  <Card className="transition-shadow hover:shadow-md">
                    <CardContent className="flex items-center justify-between gap-4 p-4">
                      <div className="min-w-0 space-y-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-medium">Commande #{shortId(order.id)}</span>
                          <OrderStatusBadge status={order.status} />
                        </div>
                        <p className="truncate text-sm text-muted-foreground">{itemsSummary}</p>
                        <p className="text-xs text-muted-foreground">
                          {formatDateTime(order.created_at)}
                        </p>
                      </div>
                      <div className="flex shrink-0 items-center gap-2">
                        <span className="font-semibold">{formatPrice(order.total)}</span>
                        <ChevronRight
                          className="h-5 w-5 text-muted-foreground"
                          aria-hidden="true"
                        />
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
