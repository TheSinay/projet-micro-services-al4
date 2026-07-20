import { Activity, History, LogOut, ShoppingBag, UtensilsCrossed } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cartCount } from "@/features/cart/cart-utils";
import { CartSheet } from "@/features/cart/CartSheet";
import { useCart } from "@/features/cart/use-cart";
import { useAuth } from "@/features/auth/auth-context";

export function Header() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [cartOpen, setCartOpen] = useState(false);
  const { data: cart } = useCart();

  const count = cart ? cartCount(cart.items) : 0;

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  return (
    <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur">
      <div className="container flex h-16 items-center justify-between gap-4">
        <Link to="/" className="flex items-center gap-2 font-display text-xl font-bold">
          <UtensilsCrossed className="h-6 w-6 text-primary" aria-hidden="true" />
          <span>
            Miam<span className="text-primary">Go</span>
          </span>
        </Link>

        <nav aria-label="Navigation principale" className="flex items-center gap-1 sm:gap-2">
          <Button variant="ghost" size="sm" asChild>
            <Link to="/tester" className="text-xs font-semibold text-amber-600 dark:text-amber-400">
              <Activity className="mr-1 inline h-4 w-4" aria-hidden="true" />
              <span>QA Testeur</span>
            </Link>
          </Button>
          {user ? (
            <>
              <Button variant="ghost" asChild>
                <Link to="/orders">
                  <History aria-hidden="true" />
                  <span className="hidden sm:inline">Mes commandes</span>
                </Link>
              </Button>
              <Button
                variant="outline"
                onClick={() => setCartOpen(true)}
                aria-label={`Ouvrir le panier (${count} article${count > 1 ? "s" : ""})`}
              >
                <ShoppingBag aria-hidden="true" />
                <span className="hidden sm:inline">Panier</span>
                {count > 0 ? <Badge aria-hidden="true">{count}</Badge> : null}
              </Button>
              <span className="hidden max-w-32 truncate text-sm text-muted-foreground md:inline">
                {user.name}
              </span>
              <Button
                variant="ghost"
                size="icon"
                onClick={handleLogout}
                aria-label="Se déconnecter"
              >
                <LogOut aria-hidden="true" />
              </Button>
            </>
          ) : (
            <>
              <Button variant="ghost" asChild>
                <Link to="/login">Connexion</Link>
              </Button>
              <Button asChild>
                <Link to="/register">Créer un compte</Link>
              </Button>
            </>
          )}
        </nav>
      </div>
      {user ? <CartSheet open={cartOpen} onOpenChange={setCartOpen} /> : null}
    </header>
  );
}
