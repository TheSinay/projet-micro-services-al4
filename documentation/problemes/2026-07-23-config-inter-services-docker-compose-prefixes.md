# Problème — Commandes systématiquement annulées : variables inter-services non préfixées

- **Date** : 2026-07-23
- **Branche** : `fix/orders-inter-service-config`
- **Composants** : `docker-compose.yml`, services `orders`, `restaurants`, `deliveries`, `notifications`, `payments`, frontend (`CheckoutPage`, `OrderStatusTimeline`, `OrderTrackingPage`)
- **Gravité** : bloquant (aucune commande ne pouvait aboutir en environnement Docker)

## Symptôme

En passant commande depuis le frontend, la commande était **« automatiquement remboursée / annulée »** quel que soit le restaurant choisi. Aucun parcours nominal n'aboutissait à une commande confirmée.

## Cause racine

Le `docker-compose.yml` injectait des variables d'environnement **non préfixées** (`REDIS_URL`, `RESTAURANTS_SERVICE_URL`, `PAYMENTS_SERVICE_URL`, `DELIVERIES_SERVICE_URL`, `EVENT_BUS`) alors que chaque service définit son propre **`env_prefix` pydantic-settings** distinct : `ORDERS_`, `RESTAURANTS_`, `DELIVERIES_`, `NOTIFICATIONS_`, `USERS_`.

Comme les noms ne correspondaient à aucun réglage attendu, **toutes ces variables étaient silencieusement ignorées** et chaque service retombait sur ses valeurs par défaut. Conséquences en chaîne :

- Le service **`orders`** conservait ses URLs par défaut `http://localhost:8002 / 8004 / 8005`. Depuis un conteneur, `localhost` ne pointe pas vers les autres services → **« All connection attempts failed »** dès l'étape de validation restaurant de la saga → compensation immédiate et **toute commande annulée en `CANCELLED_VALIDATION`**.
- **Tous les services** ignoraient `REDIS_URL` (défaut `localhost`) → le **bus d'événements Redis inter-conteneurs ne fonctionnait pas** : `order.ready`, `delivery.*`, notifications n'étaient plus propagés.
- Piège supplémentaire : le **champ de config du bus d'événements n'a pas le même nom selon les services** — `event_bus_backend` (orders), `event_bus` (restaurants), `event_backend` (deliveries, notifications). Une variable unique `EVENT_BUS` ne pouvait donc pas convenir à tous.

En résumé : divergence entre la **convention de nommage des variables** dans `docker-compose.yml` et les **préfixes / noms de champs** réellement attendus par chaque service.

## Résolution

Préfixage correct de chaque variable dans `docker-compose.yml`, service par service :

- `orders` : `ORDERS_RESTAURANTS_URL=http://restaurants:8000`, `ORDERS_PAYMENTS_URL=...`, `ORDERS_DELIVERIES_URL=...`, `ORDERS_EVENT_BUS_BACKEND=redis`, `ORDERS_CART_STORE_BACKEND=redis` ;
- `restaurants` : `RESTAURANTS_EVENT_BUS=redis` ;
- `deliveries` : `DELIVERIES_EVENT_BACKEND=redis` ;
- `notifications` : `NOTIFICATIONS_EVENT_BACKEND=redis` ;
- Redis, pour chaque service concerné : `<PREFIX>_REDIS_URL=redis://redis:6379/0` (adresse du service Docker, plus `localhost`) ;
- suppression de la variable Redis inutile côté `payments` (le service n'en a pas besoin).

Les URLs inter-services utilisent désormais le **nom de service Docker** et le **port interne 8000**, conformément à l'architecture.

### Vérification de bout en bout

- Commande valide → `PREPARING` / `CONFIRMED` avec paiement capturé ;
- ticket cuisine passé `READY` → événement `order.ready` → affectation d'un livreur → `DELIVERING`.

## Note opérationnelle — redémarrer le gateway après recréation de conteneurs

Après un `docker compose up -d` qui **recrée** des conteneurs backend, il faut **redémarrer le conteneur `gateway`** :

```
docker compose restart gateway
```

En effet, Nginx **résout les IP des upstreams au démarrage** (directives `proxy_pass` avec nom de service) et **conserve des IP périmées** si un conteneur backend a été recréé avec une nouvelle IP → **404 / 502 trompeurs** qui ne reflètent pas un vrai bug applicatif.

## Prévention

- Documenter et standardiser le **préfixe attendu par service** ; idéalement, fournir un `.env` d'exemple par service et vérifier au démarrage que les variables critiques sont bien prises en compte.
- Harmoniser à terme le **nom du champ du bus d'événements** entre services (`event_bus_backend` / `event_bus` / `event_backend`) pour supprimer ce piège.
- **Piste d'amélioration (mériterait un ADR / une entrée d'évolution)** : configurer un **`resolver` Nginx + variables** dans le gateway pour une **résolution DNS dynamique** des upstreams, afin de ne plus dépendre d'un redémarrage manuel après recréation de conteneurs.

## Correctif frontend associé — message d'annulation

La saga renvoie **toujours un HTTP 201**, y compris pour une commande annulée (l'annulation est un état métier, pas une erreur HTTP). Le frontend en déduisait à tort le succès :

- **Symptôme** : « Commande confirmée ! » affiché même pour une commande annulée ; le suivi indiquait « vous avez été remboursé » pour **toute** annulation, y compris sans paiement capturé.
- **Résolution** :
  - `CheckoutPage` branche désormais l'affichage sur **`order.status`** (et non sur le seul code HTTP) ;
  - `OrderStatusTimeline` / `OrderTrackingPage` affichent la **`cancellation_reason`** et ne mentionnent le **remboursement que si un paiement a réellement été capturé** (`payment_id` non `null`).
- **Prévention** : ne jamais déduire le succès métier du seul statut HTTP quand l'API renvoie un état applicatif ; s'appuyer sur le champ de statut du domaine.
