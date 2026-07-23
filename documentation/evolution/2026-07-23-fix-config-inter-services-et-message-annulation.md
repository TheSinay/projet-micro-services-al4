# Journal d'évolution — 2026-07-23 : Câblage inter-services (Docker) et message d'annulation frontend

**Auteur** : Équipe Fullstack / Agent Documentaliste
**Branche** : `fix/orders-inter-service-config`

## Contexte

En environnement Docker, **toute commande était systématiquement annulée / remboursée**, rendant le parcours nominal inutilisable. Correctif majeur portant sur la configuration inter-services et la restitution de l'annulation côté frontend.

## Correctifs livrés

### 1. Variables d'environnement inter-services correctement préfixées

Le `docker-compose.yml` fournissait des variables **non préfixées** (`REDIS_URL`, `RESTAURANTS_SERVICE_URL`, `PAYMENTS_SERVICE_URL`, `DELIVERIES_SERVICE_URL`, `EVENT_BUS`), ignorées par les services qui attendent chacun un **`env_prefix` pydantic-settings** propre (`ORDERS_`, `RESTAURANTS_`, `DELIVERIES_`, `NOTIFICATIONS_`, `USERS_`). Résultat : URLs inter-services par défaut (`localhost`) et bus Redis inopérant entre conteneurs.

Correction : préfixage service par service (`ORDERS_RESTAURANTS_URL=http://restaurants:8000`, `ORDERS_EVENT_BUS_BACKEND=redis`, `ORDERS_CART_STORE_BACKEND=redis`, `RESTAURANTS_EVENT_BUS=redis`, `DELIVERIES_EVENT_BACKEND=redis`, `NOTIFICATIONS_EVENT_BACKEND=redis`, `<PREFIX>_REDIS_URL=redis://redis:6379/0`), URLs pointant sur les **noms de service Docker** / port interne **8000**, et suppression de la variable Redis inutile de `payments`. Détail et cause racine : [problème dédié](../problemes/2026-07-23-config-inter-services-docker-compose-prefixes.md).

Vérifié de bout en bout : commande valide → `PREPARING` / `CONFIRMED` (paiement capturé) ; ticket cuisine `READY` → `order.ready` → affectation livreur → `DELIVERING`.

### 2. Message d'annulation fidèle côté frontend

La saga renvoie toujours un **HTTP 201**, même pour une commande annulée. Le frontend affichait « Commande confirmée ! » à tort et annonçait un remboursement pour toute annulation. Corrigé : `CheckoutPage` s'appuie sur **`order.status`** ; `OrderStatusTimeline` / `OrderTrackingPage` affichent la **`cancellation_reason`** et ne mentionnent le remboursement que si un **paiement a été capturé** (`payment_id` non `null`).

## Point d'exploitation

Après un `docker compose up -d` qui **recrée** des conteneurs backend, redémarrer le gateway : `docker compose restart gateway`. Nginx résout les IP des upstreams au démarrage et conserve sinon des IP périmées → 404 / 502 trompeurs.

## Dettes techniques et pistes ouvertes

- **Résolution DNS statique du gateway Nginx** : les `proxy_pass` par nom de service figent l'IP au démarrage. Piste : `resolver` Nginx + variables pour une résolution dynamique des upstreams, supprimant le redémarrage manuel du gateway. Mériterait un **ADR / une entrée d'évolution** dédiés.
- **Noms de champ du bus d'événements hétérogènes** entre services (`event_bus_backend` orders, `event_bus` restaurants, `event_backend` deliveries / notifications) : source d'erreurs de configuration, à harmoniser.
- **Fins de ligne CRLF sous Windows** : le working tree local est en **CRLF** (Git stocke en **LF** via `autocrlf`), ce qui met **`prettier --check` en rouge localement** (~17 fichiers) **sans impact en CI**. Normalisation **LF via `.gitattributes`** recommandée dans une branche dédiée.
