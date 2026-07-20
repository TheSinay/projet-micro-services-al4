import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Toaster } from "sonner";

import { Layout } from "@/components/Layout";
import { AuthProvider } from "@/features/auth/auth-context";
import { LoginPage } from "@/features/auth/LoginPage";
import { RegisterPage } from "@/features/auth/RegisterPage";
import { RequireAuth } from "@/features/auth/RequireAuth";
import { CheckoutPage } from "@/features/checkout/CheckoutPage";
import { OrdersHistoryPage } from "@/features/orders/OrdersHistoryPage";
import { OrderTrackingPage } from "@/features/orders/OrderTrackingPage";
import { RestaurantPage } from "@/features/restaurants/RestaurantPage";
import { RestaurantsPage } from "@/features/restaurants/RestaurantsPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 30_000,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route element={<Layout />}>
              <Route index element={<RestaurantsPage />} />
              <Route path="restaurants/:id" element={<RestaurantPage />} />
              <Route path="login" element={<LoginPage />} />
              <Route path="register" element={<RegisterPage />} />
              <Route element={<RequireAuth />}>
                <Route path="checkout" element={<CheckoutPage />} />
                <Route path="orders" element={<OrdersHistoryPage />} />
                <Route path="orders/:id" element={<OrderTrackingPage />} />
              </Route>
            </Route>
          </Routes>
        </BrowserRouter>
        <Toaster richColors position="top-center" />
      </AuthProvider>
    </QueryClientProvider>
  );
}
