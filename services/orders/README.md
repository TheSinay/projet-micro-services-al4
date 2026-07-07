# service-commandes (`orders`)

Cœur transactionnel de la plateforme de livraison de repas : panier mono-restaurant,
passage de commande (checkout) avec calcul de prix, machine à états stricte et historique.

> **Périmètre T08 (base).** L'orchestrateur SAGA (validation restaurant → paiement →
> kitchen ticket, avec compensations) arrive avec la tâche **T09** : le `POST /orders`
> crée la commande en `RECEIVED` avec `saga_state = "PENDING"` et un `TODO(T09)` marque
> le point de branchement dans `app/services/order_service.py`. L'abstraction `EventBus`
> (`app/events.py`) est câblée mais aucun événement n'est encore émis.

## Endpoints

| Méthode | Chemin | Description | Erreurs |
|---|---|---|---|
| `GET` | `/health` | Health check (hors préfixe `/api/v1`) | — |
| `GET` | `/api/v1/carts/{user_id}` | Panier de l'utilisateur (vide si inexistant) | — |
| `POST` | `/api/v1/carts/{user_id}/items` | Ajout d'un item (`restaurant_id`, `menu_item_id`, `name`, `unit_price`, `quantity`, `options[]`, `restaurant_lat?`, `restaurant_lng?`) → 201. Cumul des quantités si même item + mêmes options | 409 item d'un autre restaurant, 422 payload invalide |
| `DELETE` | `/api/v1/carts/{user_id}/items/{menu_item_id}` | Retire toutes les lignes de cet item (panier vidé ⇒ restaurant délié) | 404 item absent du panier |
| `DELETE` | `/api/v1/carts/{user_id}` | Vide le panier → 204 (idempotent) | — |
| `POST` | `/api/v1/orders` | Checkout depuis le panier (`user_id`, `delivery_address{lat, lng, label?, street?, city?}`, `restaurant_lat?`, `restaurant_lng?`) → 201, panier vidé | 422 panier vide ou payload invalide |
| `GET` | `/api/v1/orders/{id}` | Détail d'une commande | 404 |
| `GET` | `/api/v1/orders?user_id=` | Historique d'un utilisateur, plus récent d'abord | 422 `user_id` manquant |
| `PATCH` | `/api/v1/orders/{id}/status` | Transition d'état (démo/suivi ; la saga T09 utilisera le même service) | 404, 409 transition illégale, 422 statut inconnu |

Les erreurs sont normalisées au format `{"detail": "..."}`. Chaque réponse porte un header
`X-Correlation-Id` (repris de la requête ou généré), injecté dans les logs JSON (structlog).

## Règles métier

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
- Montants en `float` (prototype) : **tout montant calculé est arrondi via `round(x, 2)`**
  pour neutraliser les artefacts binaires (ex. `1.1 × 3`). Une monnaie en centimes entiers
  (ou `Decimal`) serait requise en production.
- Les items de la commande sont un **snapshot du panier, prix figés** : modifier le panier
  (ou le catalogue) après le checkout ne change jamais une commande existante.

### Machine à états stricte

```
RECEIVED ──> PREPARING ──> DELIVERING ──> DELIVERED
    │            │
    └────────────┴──> CANCELLED
```

`CANCELLED` n'est atteignable que depuis `RECEIVED` et `PREPARING`. Toute autre transition
renvoie **409** (`ALLOWED_TRANSITIONS` dans `app/services/order_service.py`).

## Backends (config `ORDERS_*`)

| Variable | Défaut | Rôle |
|---|---|---|
| `ORDERS_CART_STORE_BACKEND` | `memory` | `redis` en prod : panier JSON sous la clé `cart:{user_id}` |
| `ORDERS_EVENT_BUS_BACKEND` | `memory` | `redis` en prod : pub/sub (utilisé par la saga T09) |
| `ORDERS_REDIS_URL` | `redis://localhost:6379/0` | Connexion Redis |
| `ORDERS_BASE_DELIVERY_FEE` | `2.50` | Forfait livraison |
| `ORDERS_DELIVERY_FEE_PER_KM` | `0.50` | Part kilométrique |

Les backends in-memory (défaut) rendent les tests hermétiques : **aucun test n'exige Redis**
(les implémentations Redis sont testées avec un client fake in-memory).

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
├── main.py          # create_app() : sélection des backends, montage routers/middleware
├── config.py        # pydantic-settings (préfixe env ORDERS_)
├── logging.py       # structlog JSON + middleware X-Correlation-Id
├── events.py        # EventBus (Protocol) + InMemoryEventBus / RedisEventBus
├── dependencies.py  # wiring FastAPI : stores (app.state) → services → routes
├── routes/          # HTTP uniquement — aucune logique métier
├── services/        # cart_service, order_service, pricing + exceptions de domaine
├── repositories/    # Protocols (CartStore, OrderRepository), in-memory + RedisCartStore
└── schemas/         # DTO Pydantic v2 (requêtes/réponses)
```

Mêmes principes que le gabarit `services/users` : couches strictes, exceptions de domaine
(`DomainError`) traduites par un handler unique, aucun état global de module (tout sur
`app.state`), stores derrière des `Protocol` pour brancher Redis sans toucher au métier.
