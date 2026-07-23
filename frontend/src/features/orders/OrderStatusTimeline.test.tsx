import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { OrderStatusTimeline } from "./OrderStatusTimeline";

describe("OrderStatusTimeline", () => {
  it("affiche la timeline normale pour une commande en cours", () => {
    render(<OrderStatusTimeline status="PREPARING" />);

    expect(screen.getByRole("list", { name: /progression de la commande/i })).toBeInTheDocument();
    expect(screen.getByText("En préparation")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("annulée avec paiement capturé : affiche la raison et le remboursement", () => {
    render(
      <OrderStatusTimeline
        status="CANCELLED"
        cancellationReason="aucun livreur disponible, remboursement effectué"
        refunded
      />,
    );

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("aucun livreur disponible, remboursement effectué");
    expect(alert).toHaveTextContent(/recrédité intégralement/i);
    expect(alert).not.toHaveTextContent(/aucun montant n'a été débité/i);
  });

  it("annulée sans paiement : affiche la raison et l'absence de débit", () => {
    render(
      <OrderStatusTimeline
        status="CANCELLED"
        cancellationReason="paiement refusé (PSP indisponible), commande annulée sans débit"
        refunded={false}
      />,
    );

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent(
      "paiement refusé (PSP indisponible), commande annulée sans débit",
    );
    expect(alert).toHaveTextContent(/aucun montant n'a été débité/i);
    expect(alert).not.toHaveTextContent(/recrédité intégralement/i);
  });

  it("annulée sans raison fournie : repli sur un message générique", () => {
    render(<OrderStatusTimeline status="CANCELLED" cancellationReason={null} refunded={false} />);

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent(/votre commande a été annulée/i);
    expect(alert).toHaveTextContent(/aucun montant n'a été débité/i);
  });
});
