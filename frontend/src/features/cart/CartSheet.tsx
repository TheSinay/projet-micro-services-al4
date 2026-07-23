import { ShoppingBag, Trash2 } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { EmptyState } from "@/components/EmptyState";
import { cartSubtotal, lineTotal } from "@/features/cart/cart-utils";
import { useCart, useCartMutations } from "@/features/cart/use-cart";
import { getErrorMessage } from "@/lib/errors";
import { formatPrice } from "@/lib/format";

interface CartSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/** Cart drawer: lines with options, quantities, removal, estimated total. */
export function CartSheet({ open, onOpenChange }: CartSheetProps) {
  const navigate = useNavigate();
  const { data: cart } = useCart();
  const { removeItem, clear } = useCartMutations();

  const items = cart?.items ?? [];
  const subtotal = cartSubtotal(items);

  const handleRemove = (menuItemId: string, name: string) => {
    removeItem.mutate(menuItemId, {
      onSuccess: () => toast.success(`« ${name} » retiré du panier.`),
      onError: (error) => toast.error(getErrorMessage(error)),
    });
  };

  const handleClear = () => {
    clear.mutate(undefined, {
      onSuccess: () => toast.success("Panier vidé."),
      onError: (error) => toast.error(getErrorMessage(error)),
    });
  };

  const goToCheckout = () => {
    onOpenChange(false);
    navigate("/checkout");
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="flex w-full flex-col sm:max-w-md">
        <SheetHeader>
          <SheetTitle>Mon panier</SheetTitle>
          <SheetDescription>
            {items.length === 0
              ? "Votre panier est vide pour le moment."
              : "Vérifiez votre commande avant de passer au paiement."}
          </SheetDescription>
        </SheetHeader>

        {items.length === 0 ? (
          <div className="flex-1 py-4">
            <EmptyState
              icon={ShoppingBag}
              title="Votre panier est vide"
              description="Parcourez les restaurants et ajoutez des plats pour commencer."
            />
          </div>
        ) : (
          <>
            <ul className="flex-1 space-y-4 overflow-y-auto py-4">
              {items.map((item) => (
                <li key={item.menu_item_id} className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-medium">
                      {item.name}{" "}
                      <span className="text-sm text-muted-foreground">× {item.quantity}</span>
                    </p>
                    {item.options.length > 0 ? (
                      <p className="text-sm text-muted-foreground">
                        {item.options
                          .map((option) => `${option.name} (${formatPrice(option.price_delta)})`)
                          .join(", ")}
                      </p>
                    ) : null}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="whitespace-nowrap text-sm font-medium">
                      {formatPrice(lineTotal(item))}
                    </span>
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label={`Retirer ${item.name} du panier`}
                      disabled={removeItem.isPending}
                      onClick={() => handleRemove(item.menu_item_id, item.name)}
                    >
                      <Trash2 aria-hidden="true" />
                    </Button>
                  </div>
                </li>
              ))}
            </ul>

            <div className="space-y-4">
              <Separator />
              <div className="flex items-center justify-between font-semibold">
                <span>Total estimé</span>
                <span>{formatPrice(subtotal)}</span>
              </div>
              <p className="text-xs text-muted-foreground">
                Hors frais de livraison, calculés à la commande.
              </p>
              <SheetFooter className="gap-2">
                <Button variant="ghost" onClick={handleClear} disabled={clear.isPending}>
                  Vider le panier
                </Button>
                <Button onClick={goToCheckout}>Commander</Button>
              </SheetFooter>
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}
