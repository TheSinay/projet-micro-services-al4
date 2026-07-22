import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  ShieldAlert,
  Trash2,
  UserCheck,
} from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { apiClient } from "@/api/client";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/features/auth/auth-context";

const SERVICES = [
  { name: "Users", path: "/api/v1/users/health" },
  { name: "Restaurants", path: "/api/v1/restaurants/health" },
  { name: "Orders", path: "/api/v1/orders/health" },
  { name: "Payments", path: "/api/v1/payments/health" },
  { name: "Deliveries", path: "/api/v1/deliveries/health" },
  { name: "Notifications", path: "/api/v1/notifications/health" },
];

const MOCK_PROFILES = [
  {
    id: "usr_alice",
    name: "Alice (Client)",
    role: "client",
    email: "alice@example.com",
    password: "Password123!",
  },
  {
    id: "usr_resto",
    name: "Restaurateur (Le Chef)",
    role: "restaurant_owner",
    email: "chef@gourmet.fr",
    password: "Password123!",
  },
  {
    id: "usr_bob",
    name: "Bob (Livreur Rapide)",
    role: "courier",
    email: "bob@livreur.fr",
    password: "Password123!",
  },
];

export function TesterDashboardPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [chaosRate, setChaosRate] = useState<number>(0);

  // Health check query for each service
  const healthQueries = SERVICES.map((svc) => ({
    name: svc.name,
    // eslint-disable-next-line react-hooks/rules-of-hooks
    query: useQuery({
      queryKey: ["health", svc.name],
      queryFn: async () => {
        const res = await apiClient.get(svc.path);
        return res.data;
      },
      retry: 1,
    }),
  }));

  // PSP Chaos Mode mutation
  const chaosMutation = useMutation({
    mutationFn: async (rate: number) => {
      const res = await apiClient.post("/api/v1/_chaos", { failure_rate: rate });
      return res.data;
    },
    onSuccess: (data) => {
      setChaosRate(data.failure_rate);
      toast.success(`Mode Chaos PSP mis à jour : taux d'échec ${data.failure_rate * 100}%`);
    },
    onError: (err: Error) => {
      toast.error(`Erreur de modification du mode Chaos: ${err.message}`);
    },
  });

  const handleClearCache = () => {
    queryClient.clear();
    localStorage.clear();
    toast.success("Cache et Stockage Local nettoyés avec succès");
  };

  return (
    <div className="container space-y-8 py-8">
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-3">
          <Activity className="h-8 w-8 text-primary" />
          <h1 className="font-display text-3xl font-bold">Vue Testeur / Tester Dashboard</h1>
        </div>
        <p className="text-muted-foreground">
          Espace dédié à la validation QA, au suivi de santé des microservices et aux tests de
          résilience.
        </p>
      </div>

      {/* Grid: Health Checks */}
      <section className="space-y-4 rounded-xl border bg-card p-6">
        <div className="flex items-center justify-between">
          <h2 className="flex items-center gap-2 text-xl font-semibold">
            <CheckCircle2 className="h-5 w-5 text-emerald-500" />
            Santé des Microservices Backend
          </h2>
          <Button
            variant="outline"
            size="sm"
            onClick={() => healthQueries.forEach((h) => h.query.refetch())}
          >
            <RefreshCw className="mr-2 h-4 w-4" /> Actualiser
          </Button>
        </div>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {healthQueries.map(({ name, query }) => (
            <div
              key={name}
              className="flex items-center justify-between rounded-lg border bg-muted/40 p-4"
            >
              <div>
                <p className="font-semibold">{name}</p>
                <p className="text-xs text-muted-foreground">
                  {query.isLoading
                    ? "Vérification..."
                    : query.isError
                      ? "Erreur d'accès"
                      : "Opérationnel"}
                </p>
              </div>
              <div>
                {query.isLoading ? (
                  <RefreshCw className="h-5 w-5 animate-spin text-muted-foreground" />
                ) : query.isError ? (
                  <AlertTriangle className="h-5 w-5 text-destructive" />
                ) : (
                  <span className="block h-3 w-3 rounded-full bg-emerald-500" />
                )}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Grid: Chaos Testing & Simulation */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        {/* PSP Chaos Controller */}
        <section className="space-y-4 rounded-xl border bg-card p-6">
          <h2 className="flex items-center gap-2 text-xl font-semibold">
            <ShieldAlert className="h-5 w-5 text-amber-500" />
            Test de Résilience (PSP Chaos)
          </h2>
          <p className="text-sm text-muted-foreground">
            Simule des pannes du prestataire de paiement pour valider le comportement du Circuit
            Breaker et la compensation SAGA.
          </p>
          <div className="flex items-center gap-3 pt-2">
            <Button
              variant={chaosRate === 0 ? "default" : "outline"}
              onClick={() => chaosMutation.mutate(0.0)}
              disabled={chaosMutation.isPending}
            >
              Mode Normal (0% d'échec)
            </Button>
            <Button
              variant={chaosRate > 0 ? "destructive" : "outline"}
              onClick={() => chaosMutation.mutate(1.0)}
              disabled={chaosMutation.isPending}
            >
              Simuler Pannes PSP (100% échec)
            </Button>
          </div>
        </section>

        {/* Profiles & Actions */}
        <section className="space-y-4 rounded-xl border bg-card p-6">
          <h2 className="flex items-center gap-2 text-xl font-semibold">
            <UserCheck className="h-5 w-5 text-blue-500" />
            Session de Test & Actions
          </h2>
          <div className="space-y-2 text-sm">
            <p>
              <strong>Utilisateur actuel :</strong>{" "}
              {user ? `${user.name} (${user.email})` : "Non connecté"}
            </p>
            <div className="flex flex-col gap-3 pt-2">
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Comptes de Test Proposés (Connexion Automatique) :
              </p>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                {MOCK_PROFILES.map((profile) => (
                  <Button
                    key={profile.id}
                    variant="outline"
                    className="flex h-auto flex-col items-start gap-1 p-3 text-left"
                    onClick={async () => {
                      try {
                        await login(profile.email, profile.password);
                        toast.success(`Session activée pour ${profile.name} !`);
                        if (profile.role === "restaurant_owner") {
                          navigate("/restaurant/dashboard");
                        } else if (profile.role === "courier") {
                          navigate("/courier/dashboard");
                        } else {
                          navigate("/");
                        }
                      } catch {
                        toast.error("Erreur de connexion auto testeur");
                      }
                    }}
                  >
                    <span className="text-sm font-semibold">{profile.name}</span>
                    <span className="text-xs text-muted-foreground">{profile.email}</span>
                  </Button>
                ))}
              </div>
            </div>
          </div>
          <div className="border-t pt-4">
            <Button
              variant="outline"
              size="sm"
              onClick={handleClearCache}
              className="text-destructive"
            >
              <Trash2 className="mr-2 h-4 w-4" /> Vider Caches & Local Storage
            </Button>
          </div>
        </section>
      </div>
    </div>
  );
}
