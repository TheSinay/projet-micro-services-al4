import { useQuery } from "@tanstack/react-query";
import { MapPin, Plus, UtensilsCrossed } from "lucide-react";
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";

import * as restaurantsApi from "@/api/restaurants";
import type { MenuItem } from "@/api/types";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { PageSkeleton } from "@/components/PageSkeleton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useAuth } from "@/features/auth/auth-context";
import { MenuItemDialog } from "@/features/restaurants/MenuItemDialog";
import { formatPrice } from "@/lib/format";
import { isOpenNow } from "@/lib/opening-hours";

export function RestaurantPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [selectedItem, setSelectedItem] = useState<MenuItem | null>(null);

  const restaurantQuery = useQuery({
    queryKey: ["restaurant", id],
    queryFn: () => restaurantsApi.getRestaurant(id!),
    enabled: id !== undefined,
  });

  if (restaurantQuery.isPending) {
    return <PageSkeleton blocks={4} />;
  }

  if (restaurantQuery.isError) {
    return (
      <ErrorState
        message="Impossible de charger ce restaurant."
        onRetry={() => void restaurantQuery.refetch()}
      />
    );
  }

  const restaurant = restaurantQuery.data;
  const open = isOpenNow(restaurant.opening_hours);
  const availableItems = restaurant.menu.filter((item) => item.available);
  const unavailableItems = restaurant.menu.filter((item) => !item.available);

  const handleChoose = (item: MenuItem) => {
    if (!user) {
      toast.info("Connectez-vous pour commander.");
      navigate("/login", { state: { from: `/restaurants/${restaurant.id}` } });
      return;
    }
    setSelectedItem(item);
  };

  const renderItem = (item: MenuItem, available: boolean) => (
    <li key={item.id}>
      <Card className={available ? undefined : "opacity-60"}>
        <CardContent className="flex items-center justify-between gap-4 p-4">
          <div className="min-w-0">
            <p className="font-medium">{item.name}</p>
            {item.description ? (
              <p className="truncate text-sm text-muted-foreground">{item.description}</p>
            ) : null}
            {item.options.length > 0 ? (
              <p className="text-xs text-muted-foreground">
                {item.options.length} option{item.options.length > 1 ? "s" : ""} disponible
                {item.options.length > 1 ? "s" : ""}
              </p>
            ) : null}
          </div>
          <div className="flex shrink-0 items-center gap-3">
            <span className="font-semibold">{formatPrice(item.price)}</span>
            {available ? (
              <Button
                size="sm"
                onClick={() => handleChoose(item)}
                aria-label={`Ajouter ${item.name} au panier`}
              >
                <Plus aria-hidden="true" />
                Ajouter
              </Button>
            ) : (
              <Badge variant="secondary">Indisponible</Badge>
            )}
          </div>
        </CardContent>
      </Card>
    </li>
  );

  return (
    <div className="space-y-8">
      <div className="space-y-3">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="font-display text-3xl font-bold">{restaurant.name}</h1>
          {open === null ? null : open ? (
            <Badge variant="success">Ouvert</Badge>
          ) : (
            <Badge variant="secondary">Fermé</Badge>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
          <Badge variant="outline">{restaurant.cuisine_type}</Badge>
          <span className="flex items-center gap-1">
            <MapPin className="h-4 w-4" aria-hidden="true" />
            {restaurant.address}
          </span>
        </div>
      </div>

      {restaurant.menu.length === 0 ? (
        <EmptyState
          icon={UtensilsCrossed}
          title="Menu indisponible"
          description="Ce restaurant n'a pas encore publié son menu."
        />
      ) : (
        <div className="space-y-8">
          <section aria-labelledby="menu-heading" className="space-y-4">
            <h2 id="menu-heading" className="text-xl font-semibold">
              Menu
            </h2>
            <ul className="space-y-3">{availableItems.map((item) => renderItem(item, true))}</ul>
          </section>

          {unavailableItems.length > 0 ? (
            <section aria-labelledby="unavailable-heading" className="space-y-4">
              <h2 id="unavailable-heading" className="text-xl font-semibold text-muted-foreground">
                Indisponibles en ce moment
              </h2>
              <ul className="space-y-3">
                {unavailableItems.map((item) => renderItem(item, false))}
              </ul>
            </section>
          ) : null}
        </div>
      )}

      {selectedItem ? (
        <MenuItemDialog
          item={selectedItem}
          restaurant={restaurant}
          open={selectedItem !== null}
          onOpenChange={(dialogOpen) => {
            if (!dialogOpen) {
              setSelectedItem(null);
            }
          }}
        />
      ) : null}
    </div>
  );
}
