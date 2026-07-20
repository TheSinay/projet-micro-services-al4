# service-commandes (`orders`)

Cœur transactionnel de la plateforme de livraison de repas : panier mono-restaurant,
passage de commande (checkout) avec calcul de prix, machine à états stricte, historique,
**orchestrateur SAGA** (T09), **résilience maison** (T10) et **continuation événementielle**
de la livraison (T12).

## Endpoints

| Méthode | Chemin | Description | Erreurs |
|---|---|---|---|
| `GET` | `/health` | Health check (hors préfixe `/api/v1`) | — |
| `GET` | `/api/v1/carts/{user_id}` | Panier de l'utilisateur (vide si inexistant) | — |
| `POST` | `/api/v1/carts/{user_id}/items` | Ajout d'un item (`restaurant_id`, `menu_item_id`, `name`, `unit_price`, `quantity`, `options[]`, `restaurant_lat?`, `restaurant_lng?`) → 201. Cumul des quantités si même item + mêmes options | 409 item d'un autre restaurant, 422 payload invalide |
| `DELETE` | `/api/v1/carts/{user_id}/items/{menu_item_id}` | Retire toutes les lignes de cet item (panier vidé ⇒ restaurant délié) | 404 item absent du panier |
| `DELETE` | `/api/v1/carts/{user_id}` | Vide le panier → 204 (idempotent) | — |
| `POST` | `/api/v1/orders` | Checkout : crée la commande **puis exécute la saga** → **toujours 201** (voir ci-dessous) | 422 panier vide ou payload invalide |
| `GET` | `/api/v1/orders/{id}` | Détail d'une commande (`status`, `saga_state`, `cancellation_reason`, `payment_id`, `delivery_id`) | 404 |
| `GET` | `/api/v1/orders?user_id=` | Historique d'un utilisateur, plus récent d'abord | 422 `user_id` manquant |
| `PATCH` | `/api/v1/orders/{id}/status` | Transition d'état (démo/suivi) | 404, 409 transition illégale, 422 statut inconnu |

Les erreurs sont normalisées au format `{"detail": "..."}`. Chaque réponse porte un header
`X-Correlation-Id` (repris de la requête ou généré), injecté dans les logs JSON (structlog)
et **propagé à tous les appels sortants** de l'orchestrateur.

## SAGA `PLACE_ORDER` (T09, ADR 0003)

Orchestration synchrone dans `app/services/saga.py`, déclenchée par `POST /orders` :

| Étape | Action | `saga_state` | Compensation si échec |
|---|---|---|---|
| 1 | Commande créée `RECEIVED` (prix figés) | `PENDING` | — |
| 2 | `POST restaurants …/order-validations` | `VALIDATING` | `CANCELLED` + event `order.cancelled` (rien à rembourser) |
| 3 | `POST payments /payments` — **breaker + retry + timeout** | `PAYING` | `CANCELLED` + `order.cancelled` (paiement non abouti, rien à rembourser) |
| 4 | `POST restaurants …/kitchen-tickets` | `REQUESTING_ACCEPT` | **Remboursement total** (`POST payments/{id}/refunds`, montant = total) puis `CANCELLED` + `order.cancelled` |
| 5 | `PREPARING` + event `order.confirmed` | `CONFIRMED` | — fin nominale |

- `saga_state` est **persisté à chaque étape** ; états finaux : `CONFIRMED`,
  `CANCELLED_VALIDATION`, `CANCELLED_PAYMENT`, `CANCELLED_REFUSED`,
  `CANCELLED_NO_COURIER`, `REFUND_FAILED`, `DELIVERING`, `DELIVERED`.
- **Le panier n'est vidé que si la saga atteint `PREPARING`** : après un checkout annulé,
  le client conserve son panier et peut simplement réessayer.
- Si le **remboursement échoue** (compensation impossible) : log structuré **CRITICAL**
  (`refund_failed`) + `saga_state = REFUND_FAILED` — dette assumée du prototype, une
  intervention manuelle est requise (pas de file de compensation asynchrone).

### Choix « 201 avec commande CANCELLED »

Un checkout refusé par la saga (restaurant fermé, PSP en panne, cuisine qui refuse)
répond quand même **201 Created** : la commande **a bien été créée**, son état final
est `CANCELLED` et le champ `cancellation_reason` porte la raison lisible
(ex. « refusée par le restaurant, remboursement effectué »). Le client découvre l'issue
en consultant la commande retournée (ou via `GET /orders/{id}`). Ce choix évite de
transformer un échec **métier** de la saga en erreur **HTTP** ambiguë : la ressource
existe, elle est consultable et auditable ; c'est cohérent avec une future exécution
asynchrone de la saga (202/201 puis polling), sans changer le contrat.

### Continuation événementielle (T12, chorégraphie)

`app/subscriber.py` s'abonne à Redis pub/sub (canaux `order.ready` et
`delivery.completed`) — **uniquement** quand `ORDERS_EVENT_BUS_BACKEND=redis`
(démarrage/arrêt dans le lifespan FastAPI) :

- **`order.ready`** (publié par restaurants quand le ticket passe `READY`) →
  `POST deliveries /deliveries` (pickup = coordonnées du restaurant connues au checkout,
  dropoff = adresse de livraison de la commande) → succès : `DELIVERING` + `delivery_id`.
  **409 aucun livreur** : nouvelles tentatives différées (`ORDERS_DELIVERY_ASSIGN_ATTEMPTS`
  × `ORDERS_DELIVERY_ASSIGN_RETRY_DELAY`) ; échec définitif → **compensation tardive** :
  remboursement total puis `CANCELLED` (+ `order.cancelled`).
- **`delivery.completed`** → `DELIVERED` + event `order.delivered`.

Limite documentée : si les coordonnées du restaurant sont inconnues au checkout
(champ optionnel), le point de pickup retombe sur les coordonnées de livraison.

### Machine à états

```
RECEIVED ──> PREPARING ──> DELIVERING ──> DELIVERED
    │            │
    └────────────┴──> CANCELLED
```

`CANCELLED` est atteignable depuis `RECEIVED` (échecs de la phase critique) **et depuis
`PREPARING`** — requis par la compensation tardive « aucun livreur ». En revanche
**`DELIVERING → CANCELLED` reste interdit** : une fois le plat en route, la commande ne
peut plus être annulée (toute autre transition renvoie 409).

## Résilience (T10, ADR 0007) — `app/services/resilience.py`

Module maison, interne au service (jamais importé par un autre service) :

- **Timeout** : `2.0 s` (httpx, `ORDERS_HTTP_TIMEOUT`) sur **tous** les appels sortants.
- **Retry** : 3 tentatives max (`ORDERS_RETRY_ATTEMPTS`), backoff exponentiel **avec
  jitter**, déclenché **uniquement** sur timeout / erreur réseau / 5xx — **jamais sur un
  4xx**. `sleep` et `rng` injectables (tests déterministes). Le retry du paiement est sûr
  car payments est **idempotent par `order_id`** (jamais de double débit).
- **Circuit breaker** (`CLOSED → OPEN → HALF_OPEN`) sur l'appel **paiement** :
  ouverture après 5 échecs sur une fenêtre glissante de 30 s
  (`ORDERS_BREAKER_FAILURE_THRESHOLD` / `ORDERS_BREAKER_WINDOW_SECONDS`) ; en `OPEN`,
  **échec immédiat sans appel réseau** → compensation immédiate de la saga ; passage en
  `HALF_OPEN` après 15 s (`ORDERS_BREAKER_RECOVERY_TIMEOUT`) : **un seul** appel d'essai
  (succès → `CLOSED`, échec → `OPEN`). Horloge injectable ; seuls les échecs transitoires
  comptent (un 4xx n'ouvre jamais le circuit). État local au processus (limite ADR 0007).
- Les appels restaurants/deliveries sont protégés par **timeout + retry sans breaker** :
  seule la dépendance payments repose sur un PSP externe réputé instable ; un breaker par
  cible ajouterait de l'état sans bénéfice démontrable ici (choix documenté, facile à
  étendre puisque `CircuitBreaker` est générique).

## Événements (Redis pub/sub, enveloppe `{"event", "correlation_id", "data"}`)

| Sens | Canal | Payload `data` |
|---|---|---|
| émis | `order.confirmed` | `{order_id, user_id, restaurant_id, total}` |
| émis | `order.cancelled` | `{order_id, user_id, reason}` |
| émis | `order.delivered` | `{order_id, user_id}` |
| consommé | `order.ready` | `{order_id, restaurant_id, pickup_address}` |
| consommé | `delivery.completed` | `{order_id, delivery_id}` |

## Règles métier (panier, prix)

### Panier mono-restaurant
Un panier ne référence qu'un seul restaurant : ajouter un item d'un autre restaurant renvoie
**409** (il faut d'abord vider le panier). Un panier vidé (item par item ou en bloc) est délié
de son restaurant et peut repartir sur un autre.

### Calcul de prix
- `subtotal = Σ (unit_price + Σ price_delta des options) × quantity`
- `delivery_fee = 2.50 + 0.50 × distance_km` — distance haversine entre le restaurant et
  l'adresse de livraison quand les coordonnées du restaurant sont connues (fournies au
  checkout ou enregistrées sur le panier), sinon **forfait seul (2.50)**.
- `total = subtotal + delivery_fee`
- Montants en `float` (prototype) : **tout montant calculé est arrondi via `round(x, 2)`**.
  Une monnaie en centimes entiers (ou `Decimal`) serait requise en production.
- Les items de la commande sont un **snapshot du panier, prix figés**.

## Configuration (`ORDERS_*`)

| Variable | Défaut | Rôle |
|---|---|---|
| `ORDERS_CART_STORE_BACKEND` | `memory` | `redis` en prod : panier JSON sous la clé `cart:{user_id}` |
| `ORDERS_EVENT_BUS_BACKEND` | `memory` | `redis` en prod : pub/sub + **subscriber T12** |
| `ORDERS_REDIS_URL` | `redis://localhost:6379/0` | Connexion Redis |
| `ORDERS_BASE_DELIVERY_FEE` | `2.50` | Forfait livraison |
| `ORDERS_DELIVERY_FEE_PER_KM` | `0.50` | Part kilométrique |
| `ORDERS_RESTAURANTS_URL` | `http://localhost:8002` | Base URL service-restaurants |
| `ORDERS_PAYMENTS_URL` | `http://localhost:8004` | Base URL service-paiements |
| `ORDERS_DELIVERIES_URL` | `http://localhost:8005` | Base URL service-livraisons |
| `ORDERS_HTTP_TIMEOUT` | `2.0` | Timeout httpx (s) de tous les appels sortants |
| `ORDERS_RETRY_ATTEMPTS` | `3` | Tentatives max (retry) |
| `ORDERS_RETRY_BASE_DELAY` | `0.1` | Base (s) du backoff exponentiel |
| `ORDERS_BREAKER_FAILURE_THRESHOLD` | `5` | Échecs avant ouverture du circuit |
| `ORDERS_BREAKER_WINDOW_SECONDS` | `30.0` | Fenêtre glissante des échecs (s) |
| `ORDERS_BREAKER_RECOVERY_TIMEOUT` | `15.0` | Délai avant `HALF_OPEN` (s) |
| `ORDERS_DELIVERY_ASSIGN_ATTEMPTS` | `3` | Tentatives d'assignation livreur (T12) |
| `ORDERS_DELIVERY_ASSIGN_RETRY_DELAY` | `2.0` | Délai (s) entre tentatives différées |

Les backends in-memory (défaut) rendent les tests hermétiques : **aucun test n'exige Redis
ni un service aval qui tourne** (aval simulé via `httpx.MockTransport`, Redis via des fakes).

## Lancement local

Depuis la racine du dépôt (venv `.venv` activé) :

```bash
cd services/orders
uvicorn app.main:app --reload --port 8003
```

Swagger : <http://localhost:8003/docs>.

## Docker

```bash
docker build -t service-orders services/orders
docker run --rm -p 8003:8000 service-orders
```

Le conteneur écoute sur le port interne 8000 (convention commune) et embarque un
`HEALTHCHECK` sur `/health` (via `urllib`, `curl` étant absent de l'image slim).

## Tests et qualité

```bash
cd services/orders
python -m ruff check .
python -m ruff format --check .
python -m mypy app
python -m pytest --cov=app --cov-report=term-missing
```

Couverture minimale exigée : 80 % (`fail_under` dans `pyproject.toml`).

## Architecture

```
app/
├── main.py          # create_app() : backends, clients httpx, breaker, saga, lifespan
├── config.py        # pydantic-settings (préfixe env ORDERS_)
├── logging.py       # structlog JSON + middleware X-Correlation-Id
├── events.py        # EventBus (Protocol) + InMemoryEventBus / RedisEventBus
├── subscriber.py    # abonnement Redis pub/sub (order.ready, delivery.completed)
├── dependencies.py  # wiring FastAPI : stores (app.state) → services → routes
├── clients/         # clients httpx async : restaurants, payments, deliveries
├── routes/          # HTTP uniquement — aucune logique métier
├── services/        # cart/order services, pricing, saga (T09), resilience (T10)
├── repositories/    # Protocols (CartStore, OrderRepository), in-memory + RedisCartStore
└── schemas/         # DTO Pydantic v2 (requêtes/réponses)
```

Mêmes principes que le gabarit `services/users` : couches strictes, exceptions de domaine
(`DomainError`) traduites par un handler unique, aucun état global de module (tout sur
`app.state`), stores et clients derrière des interfaces pour brancher les implémentations
réelles sans toucher au métier.
