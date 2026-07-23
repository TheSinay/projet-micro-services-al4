import { zodResolver } from "@hookform/resolvers/zod";
import { LogIn } from "lucide-react";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/features/auth/auth-context";
import { getErrorMessage } from "@/lib/errors";
import { resolvePostLoginPath } from "@/lib/roles";

const loginSchema = z.object({
  email: z.string().min(1, "L'adresse e-mail est requise").email("Adresse e-mail invalide"),
  password: z.string().min(1, "Le mot de passe est requis"),
});

type LoginValues = z.infer<typeof loginSchema>;

export function LoginPage() {
  const { login, user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [apiError, setApiError] = useState<string | null>(null);
  const [awaitingProfile, setAwaitingProfile] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginValues>({ resolver: zodResolver(loginSchema) });

  const from = (location.state as { from?: string } | null)?.from ?? null;

  // Redirect once the profile (and therefore the role) is available.
  useEffect(() => {
    if (awaitingProfile && user !== null) {
      setAwaitingProfile(false);
      navigate(resolvePostLoginPath(user.role, from), { replace: true });
    }
  }, [awaitingProfile, user, from, navigate]);

  const onSubmit = async (values: LoginValues) => {
    setApiError(null);
    try {
      await login(values.email, values.password);
      setAwaitingProfile(true);
    } catch (error) {
      setApiError(
        getErrorMessage(error, {
          401: "E-mail ou mot de passe incorrect.",
        }),
      );
    }
  };

  return (
    <div className="mx-auto max-w-md">
      <Card>
        <CardHeader>
          <CardTitle>Connexion</CardTitle>
          <CardDescription>Connectez-vous pour commander vos plats préférés.</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" onSubmit={handleSubmit(onSubmit)} noValidate>
            <div className="space-y-2">
              <Label htmlFor="email">Adresse e-mail</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                placeholder="vous@exemple.fr"
                aria-invalid={errors.email ? true : undefined}
                aria-describedby={errors.email ? "email-error" : undefined}
                {...register("email")}
              />
              {errors.email ? (
                <p id="email-error" className="text-sm text-destructive">
                  {errors.email.message}
                </p>
              ) : null}
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Mot de passe</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                aria-invalid={errors.password ? true : undefined}
                aria-describedby={errors.password ? "password-error" : undefined}
                {...register("password")}
              />
              {errors.password ? (
                <p id="password-error" className="text-sm text-destructive">
                  {errors.password.message}
                </p>
              ) : null}
            </div>
            {apiError ? (
              <p role="alert" className="text-sm font-medium text-destructive">
                {apiError}
              </p>
            ) : null}
            <Button type="submit" className="w-full" disabled={isSubmitting || awaitingProfile}>
              <LogIn aria-hidden="true" />
              {isSubmitting || awaitingProfile ? "Connexion…" : "Se connecter"}
            </Button>
          </form>
          <p className="mt-4 text-center text-sm text-muted-foreground">
            Pas encore de compte ?{" "}
            <Link
              to="/register"
              className="font-medium text-primary underline-offset-4 hover:underline"
            >
              Créer un compte
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
