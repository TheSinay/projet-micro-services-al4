import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Bike, CheckCircle2, Clock, MapPin, PackageCheck, Truck } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { useAuth } from "@/features/auth/auth-context";
import {
  listDeliveries,
  listCouriers,
  updateDeliveryStatus,
  createCourier,
  type Delivery,
  type DeliveryAddress,
  type DeliveryStatus,
} from "@/api/orders";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export function CourierDashboardPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();

  const [selectedCourierId, setSelectedCourierId] = useState<string>("");

  // Deliveries list
  const { data: deliveries = [], isLoading: isDeliveriesLoading } = useQuery({
    queryKey: ["deliveries"],
    queryFn: () => listDeliveries(),
    refetchInterval: 5000,
  });

  // Couriers list
  const { data: couriers = [] } = useQuery({
    queryKey: ["couriers"],
    queryFn: () => listCouriers(),
  });

  // Register / attach courier fleet profile if needed
  const createCourierMutation = useMutation({
    mutationFn: async () => {
      return createCourier({
        name: user?.name ?? "Bob (Livreur Rapide)",
        phone: user?.phone ?? "+33711223344",
        lat: 48.8566,
        lng: 2.3522,
        available: true,
      });
    },
    onSuccess: (newCourier) => {
      queryClient.invalidateQueries({ queryKey: ["couriers"] });
      setSelectedCourierId(newCourier.id);
      toast.success(`Profil livreur activé ! ID: ${newCourier.id}`);
    },
  });

  // Update status mutation
  const updateStatusMutation = useMutation({
    mutationFn: async ({
      deliveryId,
      status,
    }: {
      deliveryId: string;
      status: "PICKED_UP" | "DELIVERED";
    }) => {
      return updateDeliveryStatus(deliveryId, status);
    },
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ["deliveries"] });
      toast.success(`Livraison mise à jour : ${STATUS_LABELS[updated.status]}`);
    },
    onError: (err: Error) => {
      toast.error(`Erreur de mise à jour : ${err.message}`);
    },
  });

  const activeCourier = couriers.find((c) => c.id === selectedCourierId) || couriers[0];

  return (
    <div className="container space-y-8 py-8">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <Bike className="h-8 w-8 text-primary" />
            <h1 className="font-display text-3xl font-bold">Espace Livreur</h1>
          </div>
          <p className="text-muted-foreground">
            Gérez vos livraisons assignées et confirmez la prise en charge et la remise au client.
          </p>
        </div>

        {/* Courier selector / Quick setup */}
        <div className="flex items-center gap-3">
          {couriers.length > 0 ? (
            <div className="flex items-center gap-2 rounded-lg border bg-card p-2 px-3 text-sm">
              <Truck className="h-4 w-4 text-emerald-500" />
              <span>
                Livreur actif : <strong>{activeCourier?.name}</strong>
              </span>
            </div>
          ) : (
            <Button
              onClick={() => createCourierMutation.mutate()}
              disabled={createCourierMutation.isPending}
            >
              <Bike className="mr-2 h-4 w-4" /> Activer mon Profil Livreur
            </Button>
          )}
        </div>
      </div>

      {/* Deliveries Feed */}
      <section className="space-y-4">
        <h2 className="text-xl font-semibold">Missions & Livraisons Disponibles</h2>

        {isDeliveriesLoading ? (
          <div className="text-muted-foreground">Chargement des courses...</div>
        ) : deliveries.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center p-8 text-center">
              <PackageCheck className="mb-2 h-10 w-10 text-muted-foreground" />
              <p className="font-semibold">Aucune livraison en attente</p>
              <p className="text-sm text-muted-foreground">
                Les nouvelles commandes prêtes apparaîtront ici automatiquement.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            {deliveries.map((delivery) => (
              <DeliveryCard
                key={delivery.id}
                delivery={delivery}
                onUpdateStatus={(status) =>
                  updateStatusMutation.mutate({ deliveryId: delivery.id, status })
                }
                isUpdating={updateStatusMutation.isPending}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function formatAddress(addr: DeliveryAddress): string {
  if (addr.label) return addr.label;
  return `${addr.lat.toFixed(4)}, ${addr.lng.toFixed(4)}`;
}

const STATUS_LABELS: Record<DeliveryStatus, string> = {
  PROPOSED: "Proposée",
  ACCEPTED: "Prête à récupérer",
  PICKED_UP: "En livraison",
  DELIVERED: "Livrée",
};

function getBadgeVariant(status: DeliveryStatus): "secondary" | "default" | "outline" {
  switch (status) {
    case "PROPOSED":
    case "ACCEPTED":
      return "secondary";
    case "PICKED_UP":
      return "default";
    case "DELIVERED":
      return "outline";
  }
}

function DeliveryCard({
  delivery,
  onUpdateStatus,
  isUpdating,
}: {
  delivery: Delivery;
  onUpdateStatus: (status: "PICKED_UP" | "DELIVERED") => void;
  isUpdating: boolean;
}) {
  return (
    <Card className="flex flex-col justify-between">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-base font-bold">Livraison #{delivery.id.slice(-6)}</CardTitle>
          <Badge variant={getBadgeVariant(delivery.status)}>{STATUS_LABELS[delivery.status]}</Badge>
        </div>
        <CardDescription>Commande #{delivery.order_id.slice(-6)}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2 text-sm">
          <div className="flex items-start gap-2">
            <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" />
            <div>
              <span className="font-semibold">Retrait Restaurant :</span>
              <p className="text-muted-foreground">{formatAddress(delivery.pickup_address)}</p>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
            <div>
              <span className="font-semibold">Adresse du Client :</span>
              <p className="text-muted-foreground">{formatAddress(delivery.dropoff_address)}</p>
            </div>
          </div>
          <div className="flex items-center gap-2 pt-1 text-xs text-muted-foreground">
            <Clock className="h-3.5 w-3.5" />
            <span>Créée le {new Date(delivery.created_at).toLocaleTimeString()}</span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="pt-2">
          {delivery.status === "ACCEPTED" && (
            <Button
              className="w-full"
              onClick={() => onUpdateStatus("PICKED_UP")}
              disabled={isUpdating}
            >
              <Truck className="mr-2 h-4 w-4" /> Confirmer la prise en charge (En livraison)
            </Button>
          )}

          {delivery.status === "PICKED_UP" && (
            <Button
              className="w-full bg-emerald-600 text-white hover:bg-emerald-700"
              onClick={() => onUpdateStatus("DELIVERED")}
              disabled={isUpdating}
            >
              <CheckCircle2 className="mr-2 h-4 w-4" /> Valider la livraison au client
            </Button>
          )}

          {delivery.status === "DELIVERED" && (
            <div className="flex items-center justify-center gap-2 rounded-md bg-emerald-50 p-2 text-sm font-semibold text-emerald-600 dark:bg-emerald-950/40">
              <CheckCircle2 className="h-4 w-4" /> Course terminée et livrée
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
