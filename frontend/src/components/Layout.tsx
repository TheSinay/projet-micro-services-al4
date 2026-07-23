import { Outlet } from "react-router-dom";

import { Header } from "@/components/Header";

export function Layout() {
  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <main className="container flex-1 py-8">
        <Outlet />
      </main>
      <footer className="border-t py-6">
        <div className="container text-center text-sm text-muted-foreground">
          MiamGo — projet pédagogique de plateforme de livraison de repas.
        </div>
      </footer>
    </div>
  );
}
