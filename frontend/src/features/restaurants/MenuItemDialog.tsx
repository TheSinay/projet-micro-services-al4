import { Minus, Plus, ShoppingBag } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import type { MenuItem, MenuItemOption, RestaurantDetail } from "@/api/types";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { useCartMutations } from "@/features/cart/use-cart";
import { getErrorMessage, hasStatus } from "@/lib/errors";
import { formatPrice } from "@/lib/format";

interface MenuItemDialogProps {
  item: MenuItem;
  restaurant: RestaurantDetail;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/**
 * Option + quantity picker for a dish. Handles the single-restaurant cart
 * conflict (HTTP 409) by offering to clear the cart and retry.
 */
export function MenuItemDialog({ item, restaurant, open, onOpenChange }: MenuItemDialogProps) {
  const [selectedOptions, setSelectedOptions] = useState<MenuItemOption[]>([]);
  const [quantity, setQuantity] = useState(1);
  const [conflictOpen, setConflictOpen] = useState(false);
  const { addItem, clear } = useCartMutations();

  const optionsDelta = selectedOptions.reduce((sum, option) => sum + option.price_delta, 0);
  const total = (item.price + optionsDelta) * quantity;

  const toggleOption = (option: MenuItemOption, checked: boolean) => {
    setSelectedOptions((current) =>
      checked ? [...current, option] : current.filter((o) => o.name !== option.name),
    );
  };

  const buildPayload = () => ({
    restaurant_id: restaurant.id,
    menu_item_id: item.id,
    name: item.name,
    unit_price: item.price,
    quantity,
    options: selectedOptions.map((option) => ({
      name: option.name,
      price_delta: option.price_delta,
    })),
    restaurant_lat: restaurant.lat,
    restaurant_lng: restaurant.lng,
  });

  const reset = () => {
    setSelectedOptions([]);
    setQuantity(1);
  };

  const handleAdd = async () => {
    try {
      await addItem.mutateAsync(buildPayload());
      toast.success(`« ${item.name} » ajouté au panier.`);
      reset();
      onOpenChange(false);
    } catch (error) {
      if (hasStatus(error, 409)) {
        setConflictOpen(true);
      } else {
        toast.error(getErrorMessage(error, {}, "Impossible d'ajouter ce plat au panier."));
      }
    }
  };

  const handleConflictConfirm = async () => {
    try {
      await clear.mutateAsync();
      await addItem.mutateAsync(buildPayload());
      toast.success(`Panier vidé, « ${item.name} » ajouté.`);
      setConflictOpen(false);
      reset();
      onOpenChange(false);
    } catch (error) {
      toast.error(getErrorMessage(error, {}, "Impossible d'ajouter ce plat au panier."));
    }
  };

  const isBusy = addItem.isPending || clear.isPending;

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{item.name}</DialogTitle>
            <DialogDescription>
              {item.description || "Personnalisez votre plat avant de l'ajouter au panier."}
            </DialogDescription>
          </DialogHeader>

          {item.options.length > 0 ? (
            <fieldset className="space-y-3">
              <legend className="text-sm font-medium">Options</legend>
              {item.options.map((option) => {
                const checkboxId = `option-${item.id}-${option.name}`;
                const checked = selectedOptions.some((o) => o.name === option.name);
                return (
                  <div key={option.name} className="flex items-center gap-2">
                    <Checkbox
                      id={checkboxId}
                      checked={checked}
                      onCheckedChange={(value) => toggleOption(option, value === true)}
                    />
                    <Label htmlFor={checkboxId} className="flex-1 font-normal">
                      {option.name}
                    </Label>
                    <span className="text-sm text-muted-foreground">
                      +{formatPrice(option.price_delta)}
                    </span>
                  </div>
                );
              })}
            </fieldset>
          ) : null}

          <div className="flex items-center justify-between">
            <span className="text-sm font-medium" id={`quantity-label-${item.id}`}>
              Quantité
            </span>
            <div
              className="flex items-center gap-3"
              role="group"
              aria-labelledby={`quantity-label-${item.id}`}
            >
              <Button
                variant="outline"
                size="icon"
                aria-label="Diminuer la quantité"
                disabled={quantity <= 1}
                onClick={() => setQuantity((q) => Math.max(1, q - 1))}
              >
                <Minus aria-hidden="true" />
              </Button>
              <span className="w-6 text-center font-medium" aria-live="polite">
                {quantity}
              </span>
              <Button
                variant="outline"
                size="icon"
                aria-label="Augmenter la quantité"
                onClick={() => setQuantity((q) => q + 1)}
              >
                <Plus aria-hidden="true" />
              </Button>
            </div>
          </div>

          <Separator />

          <DialogFooter className="items-center gap-2 sm:justify-between">
            <span className="text-lg font-semibold">{formatPrice(total)}</span>
            <Button onClick={() => void handleAdd()} disabled={isBusy}>
              <ShoppingBag aria-hidden="true" />
              {isBusy ? "Ajout…" : "Ajouter au panier"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={conflictOpen} onOpenChange={setConflictOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Changer de restaurant ?</DialogTitle>
            <DialogDescription>
              Votre panier contient déjà des plats d&apos;un autre restaurant. Pour commander chez{" "}
              {restaurant.name}, il faut d&apos;abord vider votre panier.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setConflictOpen(false)} disabled={isBusy}>
              Garder mon panier
            </Button>
            <Button
              variant="destructive"
              onClick={() => void handleConflictConfirm()}
              disabled={isBusy}
            >
              {isBusy ? "Un instant…" : "Vider le panier et ajouter"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
