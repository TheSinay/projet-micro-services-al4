import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CreditCard, ShoppingBag } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { z } from "zod";

import * as ordersApi from "@/api/orders";
import type { DeliveryAddress } from "@/api/types";
import * as usersApi from "@/api/users";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { PageSkeleton } from "@/components/PageSkeleton";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Separator } from "@/components/ui/separator";
import { useAuth } from "@/features/auth/auth-context";
import { cartSubtotal, lineTotal } from "@/features/cart/cart-utils";
import { useCart } from "@/features/cart/use-cart";
import { getErrorMessage } from "@/lib/errors";
import { formatPrice } from "@/lib/format";

const NEW_ADDRESS = "new";

const addressSchema = z.object({
  label: z.string().min(1, "Le libellé est requis (ex. Maison)").max(50, "Libellé trop long"),
  street: z.string().min(1, "La rue est requise").max(200, "Rue trop longue"),
  city: z.string().min(1, "La ville est requise").max(100, "Ville trop longue"),
  lat: z.coerce
    .number({ invalid_type_error: "Latitude invalide" })
    .min(-90, "Latitude invalide")
    .max(90, "Latitude invalide"),
  lng: z.coerce
    .number({ invalid_type_error: "Longitude invalide" })
    .min(-180, "Longitude invalide")
    .max(180, "Longitude invalide"),
});

type AddressValues = z.infer<typeof addressSchema>;

export function CheckoutPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [selectedAddressId, setSelectedAddressId] = useState<string>(NEW_ADDRESS);
  const [saveAddress, setSaveAddress] = useState(true);

  const cartQuery = useCart();
  const addressesQuery = useQuery({
    queryKey: ["addresses", user?.id],
    queryFn: usersApi.listAddresses,
    enabled: user !== null,
  });

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<AddressValues>({ resolver: zodResolver(addressSchema) });

  const placeOrder = useMutation({
    mutationFn: async ({ address, save }: { address: DeliveryAddress; save: boolean }) => {
      if (save) {
        await usersApi.createAddress({
          label: address.label ?? "Adresse",
          street: address.street ?? "",
          city: address.city ?? "",
          lat: address.lat,
          lng: address.lng,
        });
      }
      return ordersApi.placeOrder({ user_id: user!.id, delivery_address: address });
    },
    onSuccess: (order) => {
      void queryClient.invalidateQueries({ queryKey: ["cart", user?.id] });
      void queryClient.invalidateQueries({ queryKey: ["addresses", user?.id] });
      toast.success("Commande confirmée ! Suivez sa préparation en direct.");
      navigate(`/orders/${order.id}`, { replace: true });
    },
    onError: (error) => {
      toast.error(
        getErrorMessage(
          error,
          { 422: "Votre panier est vide ou invalide." },
          "Le paiement n'a pas abouti. Veuillez réessayer.",
        ),
      );
    },
  });

  if (cartQuery.isPending || addressesQuery.isPending) {
    return <PageSkeleton blocks={3} />;
  }

  if (cartQuery.isError) {
    return (
      <ErrorState
        message="Impossible de charger votre panier."
        onRetry={() => void cartQuery.refetch()}
      />
    );
  }

  const cart = cartQuery.data;
  const addresses = addressesQuery.data ?? [];

  if (cart.items.length === 0) {
    return (
      <EmptyState
        icon={ShoppingBag}
        title="Votre panier est vide"
        description="Ajoutez des plats avant de passer commande."
        action={
          <Button asChild>
            <Link to="/">Voir les restaurants</Link>
          </Button>
        }
      />
    );
  }

  const subtotal = cartSubtotal(cart.items);
  const isNewAddress = selectedAddressId === NEW_ADDRESS;
  const isProcessing = placeOrder.isPending;

  const submitWithSavedAddress = () => {
    const address = addresses.find((candidate) => candidate.id === selectedAddressId);
    if (!address) {
      toast.error("Veuillez choisir une adresse de livraison.");
      return;
    }
    placeOrder.mutate({
      address: {
        lat: address.lat,
        lng: address.lng,
        label: address.label,
        street: address.street,
        city: address.city,
      },
      save: false,
    });
  };

  const submitWithNewAddress = (values: AddressValues) => {
    placeOrder.mutate({ address: values, save: saveAddress });
  };

  const payButtonContent = (
    <>
      <CreditCard aria-hidden="true" />
      {isProcessing ? "Traitement en cours…" : "Payer et commander"}
    </>
  );

  return (
    <div className="grid gap-8 lg:grid-cols-[1fr_24rem]">
      <div className="space-y-6">
        <h1 className="font-display text-3xl font-bold">Finaliser ma commande</h1>

        <Card>
          <CardHeader>
            <CardTitle className="text-xl">Adresse de livraison</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <RadioGroup
              value={selectedAddressId}
              onValueChange={setSelectedAddressId}
              aria-label="Choix de l'adresse de livraison"
            >
              {addresses.map((address) => (
                <div key={address.id} className="flex items-start gap-3 rounded-md border p-3">
                  <RadioGroupItem value={address.id} id={`address-${address.id}`} />
                  <Label htmlFor={`address-${address.id}`} className="flex-1 font-normal">
                    <span className="block font-medium">{address.label}</span>
                    <span className="block text-sm text-muted-foreground">
                      {address.street}, {address.city}
                    </span>
                  </Label>
                </div>
              ))}
              <div className="flex items-center gap-3 rounded-md border p-3">
                <RadioGroupItem value={NEW_ADDRESS} id="address-new" />
                <Label htmlFor="address-new" className="font-normal">
                  Nouvelle adresse
                </Label>
              </div>
            </RadioGroup>

            {isNewAddress ? (
              <form
                id="new-address-form"
                className="space-y-4"
                onSubmit={handleSubmit(submitWithNewAddress)}
                noValidate
              >
                <div className="space-y-2">
                  <Label htmlFor="label">Libellé</Label>
                  <Input
                    id="label"
                    placeholder="Maison, Bureau…"
                    aria-invalid={errors.label ? true : undefined}
                    aria-describedby={errors.label ? "label-error" : undefined}
                    {...register("label")}
                  />
                  {errors.label ? (
                    <p id="label-error" className="text-sm text-destructive">
                      {errors.label.message}
                    </p>
                  ) : null}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="street">Rue</Label>
                  <Input
                    id="street"
                    placeholder="12 rue des Lilas"
                    autoComplete="street-address"
                    aria-invalid={errors.street ? true : undefined}
                    aria-describedby={errors.street ? "street-error" : undefined}
                    {...register("street")}
                  />
                  {errors.street ? (
                    <p id="street-error" className="text-sm text-destructive">
                      {errors.street.message}
                    </p>
                  ) : null}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="city">Ville</Label>
                  <Input
                    id="city"
                    placeholder="Lyon"
                    autoComplete="address-level2"
                    aria-invalid={errors.city ? true : undefined}
                    aria-describedby={errors.city ? "city-error" : undefined}
                    {...register("city")}
                  />
                  {errors.city ? (
                    <p id="city-error" className="text-sm text-destructive">
                      {errors.city.message}
                    </p>
                  ) : null}
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="lat">Latitude</Label>
                    <Input
                      id="lat"
                      type="number"
                      step="any"
                      placeholder="45.7640"
                      aria-invalid={errors.lat ? true : undefined}
                      aria-describedby={errors.lat ? "lat-error" : undefined}
                      {...register("lat")}
                    />
                    {errors.lat ? (
                      <p id="lat-error" className="text-sm text-destructive">
                        {errors.lat.message}
                      </p>
                    ) : null}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="lng">Longitude</Label>
                    <Input
                      id="lng"
                      type="number"
                      step="any"
                      placeholder="4.8357"
                      aria-invalid={errors.lng ? true : undefined}
                      aria-describedby={errors.lng ? "lng-error" : undefined}
                      {...register("lng")}
                    />
                    {errors.lng ? (
                      <p id="lng-error" className="text-sm text-destructive">
                        {errors.lng.message}
                      </p>
                    ) : null}
                  </div>
                </div>
                <p className="text-xs text-muted-foreground">
                  Les coordonnées GPS servent à calculer les frais de livraison.
                </p>
                <div className="flex items-center gap-2">
                  <Checkbox
                    id="save-address"
                    checked={saveAddress}
                    onCheckedChange={(value) => setSaveAddress(value === true)}
                  />
                  <Label htmlFor="save-address" className="font-normal">
                    Enregistrer cette adresse dans mon carnet
                  </Label>
                </div>
              </form>
            ) : null}
          </CardContent>
        </Card>
      </div>

      <div className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-xl">Récapitulatif</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <ul className="space-y-2">
              {cart.items.map((item) => (
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
            <div className="flex justify-between text-sm">
              <span>Sous-total</span>
              <span>{formatPrice(subtotal)}</span>
            </div>
            <p className="text-xs text-muted-foreground">
              Les frais de livraison seront calculés selon la distance et ajoutés au total.
            </p>
            {isNewAddress ? (
              <Button
                type="submit"
                form="new-address-form"
                className="w-full"
                disabled={isProcessing}
              >
                {payButtonContent}
              </Button>
            ) : (
              <Button className="w-full" disabled={isProcessing} onClick={submitWithSavedAddress}>
                {payButtonContent}
              </Button>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
