import { MapPin } from "lucide-react";
import { Link } from "react-router-dom";

import type { Restaurant } from "@/api/types";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { isOpenNow } from "@/lib/opening-hours";

interface RestaurantCardProps {
  restaurant: Restaurant;
}

export function RestaurantCard({ restaurant }: RestaurantCardProps) {
  const open = isOpenNow(restaurant.opening_hours);

  return (
    <Link
      to={`/restaurants/${restaurant.id}`}
      className="group block rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
      aria-label={`Voir le restaurant ${restaurant.name}`}
    >
      <Card className="h-full transition-shadow group-hover:shadow-md">
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between gap-2">
            <CardTitle className="text-lg">{restaurant.name}</CardTitle>
            {open === null ? null : open ? (
              <Badge variant="success">Ouvert</Badge>
            ) : (
              <Badge variant="secondary">Fermé</Badge>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-2">
          <Badge variant="outline">{restaurant.cuisine_type}</Badge>
          <p className="flex items-center gap-1 text-sm text-muted-foreground">
            <MapPin className="h-4 w-4 shrink-0" aria-hidden="true" />
            {restaurant.address}
          </p>
        </CardContent>
      </Card>
    </Link>
  );
}
