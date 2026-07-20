import { Bike, ChefHat, PackageCheck, Receipt, XCircle, type LucideIcon } from "lucide-react";

import type { OrderStatus } from "@/api/types";
import { cn } from "@/lib/utils";

interface TimelineStep {
  status: OrderStatus;
  label: string;
  description: string;
  icon: LucideIcon;
}

const STEPS: TimelineStep[] = [
  {
    status: "RECEIVED",
    label: "Reçue",
    description: "Le restaurant a bien reçu votre commande.",
    icon: Receipt,
  },
  {
    status: "PREPARING",
    label: "En préparation",
    description: "Vos plats sont en cours de préparation.",
    icon: ChefHat,
  },
  {
    status: "DELIVERING",
    label: "En livraison",
    description: "Votre livreur est en route.",
    icon: Bike,
  },
  {
    status: "DELIVERED",
    label: "Livrée",
    description: "Bon appétit !",
    icon: PackageCheck,
  },
];

interface OrderStatusTimelineProps {
  status: OrderStatus;
}

/**
 * Vertical timeline of the order lifecycle. A cancelled order (compensated
 * saga: payment refunded) is shown as a red alert instead of the steps.
 */
export function OrderStatusTimeline({ status }: OrderStatusTimelineProps) {
  if (status === "CANCELLED") {
    return (
      <div
        role="alert"
        className="flex items-start gap-3 rounded-lg border border-destructive/40 bg-destructive/5 p-4"
      >
        <XCircle className="mt-0.5 h-6 w-6 shrink-0 text-destructive" aria-hidden="true" />
        <div>
          <p className="font-semibold text-destructive">
            Commande annulée — vous avez été remboursé.
          </p>
          <p className="text-sm text-muted-foreground">
            Le montant débité vous sera recrédité intégralement.
          </p>
        </div>
      </div>
    );
  }

  const currentIndex = STEPS.findIndex((step) => step.status === status);

  return (
    <ol className="space-y-0" aria-label="Progression de la commande">
      {STEPS.map((step, index) => {
        const isDone = index < currentIndex;
        const isCurrent = index === currentIndex;
        const Icon = step.icon;
        return (
          <li
            key={step.status}
            className="relative flex gap-4 pb-8 last:pb-0"
            aria-current={isCurrent ? "step" : undefined}
          >
            {index < STEPS.length - 1 ? (
              <span
                aria-hidden="true"
                className={cn(
                  "absolute left-5 top-10 h-[calc(100%-2.5rem)] w-0.5",
                  isDone ? "bg-success" : "bg-border",
                )}
              />
            ) : null}
            <span
              className={cn(
                "flex h-10 w-10 shrink-0 items-center justify-center rounded-full border-2",
                isDone && "border-success bg-success text-success-foreground",
                isCurrent && "border-primary bg-primary text-primary-foreground",
                !isDone && !isCurrent && "border-border bg-muted text-muted-foreground",
              )}
            >
              <Icon className="h-5 w-5" aria-hidden="true" />
            </span>
            <div className="pt-1">
              <p
                className={cn(
                  "font-medium",
                  !isDone && !isCurrent && "text-muted-foreground",
                  isCurrent && "text-primary",
                )}
              >
                {step.label}
              </p>
              {isCurrent ? (
                <p className="text-sm text-muted-foreground">{step.description}</p>
              ) : null}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
