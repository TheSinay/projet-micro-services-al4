import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Toaster } from "sonner";

import { Layout } from "@/components/Layout";
import { AuthProvider, useAuth } from "@/features/auth/auth-context";
import { LoginPage } from "@/features/auth/LoginPage";
import { RegisterPage } from "@/features/auth/RegisterPage";
import { RequireRole } from "@/features/auth/RequireRole";
import { CheckoutPage } from "@/features/checkout/CheckoutPage";
import { OrdersHistoryPage } from "@/features/orders/OrdersHistoryPage";
import { OrderTrackingPage } from "@/features/orders/OrderTrackingPage";
import { RestaurantPage } from "@/features/restaurants/RestaurantPage";
import { RestaurantsPage } from "@/features/restaurants/RestaurantsPage";
import { RestaurantDashboardPage } from "@/features/restaurants/RestaurantDashboardPage";
import { CourierDashboardPage } from "@/features/deliveries/CourierDashboardPage";
import { TesterDashboardPage } from "@/features/tester/TesterDashboardPage";
import { homePathForRole } from "@/lib/roles";

/**
 * Home route: the catalogue is for clients (and anonymous visitors).
 * A logged-in restaurateur or courier is redirected to their own space.
 */
function HomeRoute() {
  const { user } = useAuth();

  if (user !== null && user.role !== "client") {
    return <Navigate to={homePathForRole(user.role)} replace />;
  }
  return <RestaurantsPage />;
}

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
              <Route index element={<HomeRoute />} />
              <Route path="restaurants/:id" element={<RestaurantPage />} />
              <Route path="login" element={<LoginPage />} />
              <Route path="register" element={<RegisterPage />} />
              <Route path="tester" element={<TesterDashboardPage />} />
              <Route element={<RequireRole allow={["restaurant_owner"]} />}>
                <Route path="restaurant/dashboard" element={<RestaurantDashboardPage />} />
              </Route>
              <Route element={<RequireRole allow={["courier"]} />}>
                <Route path="courier/dashboard" element={<CourierDashboardPage />} />
              </Route>
              <Route element={<RequireRole allow={["client"]} />}>
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
