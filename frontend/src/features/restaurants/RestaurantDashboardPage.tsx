import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ChefHat, Plus, Edit2, Trash2, Utensils, Store } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { useAuth } from "@/features/auth/auth-context";
import {
  searchRestaurants,
  getRestaurant,
  createRestaurant,
  createMenuItem,
  updateMenuItem,
  deleteMenuItem,
  type MenuItem,
} from "@/api/restaurants";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

export function RestaurantDashboardPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();

  const [createRestoOpen, setCreateRestoOpen] = useState(false);
  const [addDishOpen, setAddDishOpen] = useState(false);

  // Form states
  const [restoName, setRestoName] = useState("");
  const [cuisineType, setCuisineType] = useState("french");
  const [address, setAddress] = useState("15 rue de Paris, 75001 Paris");

  // Dish form states
  const [dishName, setDishName] = useState("");
  const [dishDesc, setDishDesc] = useState("");
  const [dishPrice, setDishPrice] = useState("12.50");

  // Fetch all restaurants to find the one attached to this user (or fallback to La Bella Napoli)
  const { data: restaurants = [] } = useQuery({
    queryKey: ["restaurants"],
    queryFn: () => searchRestaurants(),
  });

  const myRestaurant =
    restaurants.find((r) => r.owner_id === user?.id) ||
    restaurants.find((r) => r.id === "resto-bella-napoli") ||
    restaurants[0];

  // Fetch full details (menu included)
  const { data: restaurantDetail } = useQuery({
    queryKey: ["restaurantDetail", myRestaurant?.id],
    queryFn: () => getRestaurant(myRestaurant.id),
    enabled: Boolean(myRestaurant?.id),
  });

  // Create Restaurant Mutation
  const createRestoMutation = useMutation({
    mutationFn: async () => {
      return createRestaurant({
        name: restoName,
        cuisine_type: cuisineType,
        address,
        lat: 48.8566,
        lng: 2.3522,
        opening_hours: [
          { day: 0, open: "11:00", close: "23:00" },
          { day: 1, open: "11:00", close: "23:00" },
          { day: 2, open: "11:00", close: "23:00" },
          { day: 3, open: "11:00", close: "23:00" },
          { day: 4, open: "11:00", close: "23:00" },
          { day: 5, open: "11:00", close: "23:00" },
          { day: 6, open: "11:00", close: "23:00" },
        ],
        auto_accept: true,
        owner_id: user?.id,
      });
    },
    onSuccess: (newResto) => {
      queryClient.invalidateQueries({ queryKey: ["restaurants"] });
      setCreateRestoOpen(false);
      toast.success(`Restaurant "${newResto.name}" créé avec succès !`);
    },
    onError: (err: Error) => {
      toast.error(`Erreur lors de la création : ${err.message}`);
    },
  });

  // Add Dish Mutation
  const addDishMutation = useMutation({
    mutationFn: async () => {
      if (!myRestaurant) return;
      return createMenuItem(myRestaurant.id, {
        name: dishName,
        description: dishDesc,
        price: parseFloat(dishPrice),
        options: [],
        available: true,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["restaurantDetail", myRestaurant?.id] });
      setAddDishOpen(false);
      setDishName("");
      setDishDesc("");
      toast.success("Plat ajouté au menu !");
    },
  });

  // Update Dish Mutation
  const updateDishMutation = useMutation({
    mutationFn: async (dish: MenuItem) => {
      if (!myRestaurant) return;
      return updateMenuItem(myRestaurant.id, dish.id, {
        name: dish.name,
        description: dish.description,
        price: dish.price,
        options: dish.options,
        available: !dish.available,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["restaurantDetail", myRestaurant?.id] });
      toast.success("Disponibilité du plat mise à jour");
    },
  });

  // Delete Dish Mutation
  const deleteDishMutation = useMutation({
    mutationFn: async (dishId: string) => {
      if (!myRestaurant) return;
      return deleteMenuItem(myRestaurant.id, dishId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["restaurantDetail", myRestaurant?.id] });
      toast.success("Plat supprimé du menu");
    },
  });

  return (
    <div className="container space-y-8 py-8">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <ChefHat className="h-8 w-8 text-primary" />
            <h1 className="font-display text-3xl font-bold">Espace Restaurateur</h1>
          </div>
          <p className="text-muted-foreground">
            Gérez votre établissement, vos menus et le suivi des préprations en cuisine.
          </p>
        </div>

        {!myRestaurant && (
          <Dialog open={createRestoOpen} onOpenChange={setCreateRestoOpen}>
            <DialogTrigger asChild>
              <Button>
                <Store className="mr-2 h-4 w-4" /> Créer mon Etablissement
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Créer votre Restaurant</DialogTitle>
                <DialogDescription>
                  Renseignez les informations principales de votre établissement.
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label>Nom de l'établissement</Label>
                  <Input
                    value={restoName}
                    onChange={(e) => setRestoName(e.target.value)}
                    placeholder="ex: Le Bistro Gourmand"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Type de Cuisine</Label>
                  <Input
                    value={cuisineType}
                    onChange={(e) => setCuisineType(e.target.value)}
                    placeholder="french, italian, japanese..."
                  />
                </div>
                <div className="space-y-2">
                  <Label>Adresse</Label>
                  <Input value={address} onChange={(e) => setAddress(e.target.value)} />
                </div>
                <Button
                  className="w-full"
                  onClick={() => createRestoMutation.mutate()}
                  disabled={createRestoMutation.isPending || !restoName}
                >
                  Valider la Création
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        )}
      </div>

      {myRestaurant ? (
        <div className="space-y-8">
          {/* Restaurant Profile Card */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-2xl">{myRestaurant.name}</CardTitle>
                  <CardDescription className="mt-1 flex items-center gap-2">
                    <Badge variant="outline">{myRestaurant.cuisine_type}</Badge>
                    <span>{myRestaurant.address}</span>
                  </CardDescription>
                </div>
                <Badge className="bg-emerald-500">Auto-Accept Actif</Badge>
              </div>
            </CardHeader>
          </Card>

          {/* Menu Management Section */}
          <section className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="flex items-center gap-2 text-xl font-semibold">
                <Utensils className="h-5 w-5 text-primary" />
                Gestion de la Carte / Menu
              </h2>
              <Dialog open={addDishOpen} onOpenChange={setAddDishOpen}>
                <DialogTrigger asChild>
                  <Button size="sm">
                    <Plus className="mr-2 h-4 w-4" /> Ajouter un Plat
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Ajouter un nouveau plat</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-4 py-4">
                    <div className="space-y-2">
                      <Label>Nom du plat</Label>
                      <Input
                        value={dishName}
                        onChange={(e) => setDishName(e.target.value)}
                        placeholder="ex: Burger Gourmet Aveyronnais"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Description</Label>
                      <Input
                        value={dishDesc}
                        onChange={(e) => setDishDesc(e.target.value)}
                        placeholder="ex: Pain brioché, steak haché 180g, cantal AOP"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Prix (€)</Label>
                      <Input
                        type="number"
                        step="0.5"
                        value={dishPrice}
                        onChange={(e) => setDishPrice(e.target.value)}
                      />
                    </div>
                    <Button
                      className="w-full"
                      onClick={() => addDishMutation.mutate()}
                      disabled={addDishMutation.isPending || !dishName}
                    >
                      Ajouter au Menu
                    </Button>
                  </div>
                </DialogContent>
              </Dialog>
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
              {(restaurantDetail?.menu || []).map((dish) => (
                <Card key={dish.id} className="flex flex-col justify-between">
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div>
                        <CardTitle className="text-base">{dish.name}</CardTitle>
                        <p className="mt-1 text-sm font-bold text-primary">
                          {dish.price.toFixed(2)} €
                        </p>
                      </div>
                      <Badge variant={dish.available ? "default" : "secondary"}>
                        {dish.available ? "Disponible" : "Épuisé"}
                      </Badge>
                    </div>
                    <CardDescription className="mt-2 line-clamp-2 text-xs">
                      {dish.description}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="flex items-center gap-2 border-t pt-2">
                    <Button
                      variant="outline"
                      size="sm"
                      className="w-full"
                      onClick={() => updateDishMutation.mutate(dish)}
                    >
                      <Edit2 className="mr-1 h-3.5 w-3.5" />
                      {dish.available ? "Marquer Épuisé" : "Marquer Dispo"}
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="shrink-0 text-destructive"
                      onClick={() => deleteDishMutation.mutate(dish.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          </section>
        </div>
      ) : null}
    </div>
  );
}
