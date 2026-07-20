import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Search, Store } from "lucide-react";
import { useMemo, useState } from "react";

import * as restaurantsApi from "@/api/restaurants";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { RestaurantCard } from "@/features/restaurants/RestaurantCard";
import { useDebouncedValue } from "@/lib/use-debounced-value";

const ALL_CUISINES = "all";

export function RestaurantsPage() {
  const [searchText, setSearchText] = useState("");
  const [cuisine, setCuisine] = useState<string>(ALL_CUISINES);
  const debouncedSearch = useDebouncedValue(searchText, 350);

  const params = useMemo(
    () => ({
      q: debouncedSearch.trim() || undefined,
      cuisine: cuisine === ALL_CUISINES ? undefined : cuisine,
    }),
    [debouncedSearch, cuisine],
  );

  const restaurantsQuery = useQuery({
    queryKey: ["restaurants", params],
    queryFn: () => restaurantsApi.searchRestaurants(params),
    placeholderData: keepPreviousData,
  });

  // Cuisine facets come from the full (unfiltered) catalogue.
  const cuisinesQuery = useQuery({
    queryKey: ["restaurants", "cuisines"],
    queryFn: () => restaurantsApi.searchRestaurants(),
    select: (restaurants) =>
      [...new Set(restaurants.map((restaurant) => restaurant.cuisine_type))].sort((a, b) =>
        a.localeCompare(b, "fr"),
      ),
  });

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="font-display text-3xl font-bold">Envie de quoi aujourd&apos;hui ?</h1>
        <p className="text-muted-foreground">
          Trouvez un restaurant et faites-vous livrer en quelques minutes.
        </p>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
        <div className="flex-1 space-y-2">
          <Label htmlFor="restaurant-search">Rechercher</Label>
          <div className="relative">
            <Search
              className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
              aria-hidden="true"
            />
            <Input
              id="restaurant-search"
              type="search"
              placeholder="Un restaurant, un plat…"
              className="pl-9"
              value={searchText}
              onChange={(event) => setSearchText(event.target.value)}
            />
          </div>
        </div>
        <div className="w-full space-y-2 sm:w-56">
          <Label htmlFor="cuisine-filter">Type de cuisine</Label>
          <Select value={cuisine} onValueChange={setCuisine}>
            <SelectTrigger id="cuisine-filter" aria-label="Filtrer par type de cuisine">
              <SelectValue placeholder="Toutes les cuisines" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL_CUISINES}>Toutes les cuisines</SelectItem>
              {(cuisinesQuery.data ?? []).map((cuisineType) => (
                <SelectItem key={cuisineType} value={cuisineType}>
                  {cuisineType}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {restaurantsQuery.isPending ? (
        <div
          className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
          aria-busy="true"
          aria-label="Chargement des restaurants"
        >
          {Array.from({ length: 6 }, (_, index) => (
            <Skeleton key={index} className="h-40" data-testid="restaurant-skeleton" />
          ))}
        </div>
      ) : restaurantsQuery.isError ? (
        <ErrorState
          message="Impossible de charger les restaurants."
          onRetry={() => void restaurantsQuery.refetch()}
        />
      ) : restaurantsQuery.data.length === 0 ? (
        <EmptyState
          icon={Store}
          title="Aucun restaurant trouvé"
          description="Essayez un autre mot-clé ou changez de type de cuisine."
        />
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {restaurantsQuery.data.map((restaurant) => (
            <li key={restaurant.id}>
              <RestaurantCard restaurant={restaurant} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
