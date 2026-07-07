# service-livraisons (`deliveries`)

Service des livreurs et des livraisons : flotte de livreurs (disponibilité, localisation
simulée), **assignation du livreur disponible le plus proche** (distance haversine) et suivi de
livraison `PROPOSED → ACCEPTED → PICKED_UP → DELIVERED`, avec publication d'événements sur
Redis pub/sub. Structure calquée sur le gabarit `services/users`.

## Endpoints

| Méthode | Chemin | Description | Erreurs |
|---|---|---|---|
| `GET` | `/health` | Health check (hors préfixe `/api/v1`) | — |
| `POST` | `/api/v1/couriers` | Création d'un livreur (`name`, `phone`, `available?`, `location{lat,lng}`) → 201 | 422 payload invalide |
| `GET` | `/api/v1/couriers` | Liste des livreurs | — |
| `GET` | `/api/v1/couriers/{id}` | Détail d'un livreur | 404 |
| `PATCH` | `/api/v1/couriers/{id}` | Mise à jour partielle : `{available?, location?}` (localisation simulée) | 404, 422 |
| `POST` | `/api/v1/deliveries` | Demande d'assignation `{order_id, pickup_address, dropoff_address}` → 201 ; re-POST du même `order_id` actif → **200** (idempotence) | **409 `{"detail": "aucun livreur disponible"}`**, 422 |
| `GET` | `/api/v1/deliveries` | Liste, filtrable par `?order_id=` | — |
| `GET` | `/api/v1/deliveries/{id}` | Détail d'une livraison (statut + historique `events[{status, at}]`) | 404 |
| `PATCH` | `/api/v1/deliveries/{id}` | Transition stricte `{status}` : `ACCEPTED→PICKED_UP→DELIVERED` | 404, **409 transition invalide**, 422 statut inconnu |

Les erreurs sont normalisées au format `{"detail": "..."}`. Chaque réponse porte un header
`X-Correlation-Id` (repris de la requête ou généré), injecté dans les logs JSON (structlog)
et dans les événements publiés.

## Assignation et simulation d'auto-acceptation

`POST /api/v1/deliveries` (appelé par service-commandes quand la commande est prête) :

1. choisit le **livreur disponible le plus proche** du point de retrait (distance haversine) ;
2. crée la livraison en `PROPOSED`, marque le livreur indisponible, publie `delivery.proposed` ;
3. **simulation prototype : le livreur auto-accepte immédiatement** — la livraison passe
   aussitôt à `ACCEPTED` et `delivery.assigned` est publié avec
   `{order_id, delivery_id, courier_id, courier_name}`. Dans une version réelle, l'acceptation
   serait une action asynchrone du livreur (app mobile) ; ici les deux événements sont donc
   publiés dos à dos dans la même requête.

Règles associées :

- **Aucun livreur disponible → 409** `{"detail": "aucun livreur disponible"}` : c'est le
  déclencheur de compensation côté orchestrateur SAGA (service-commandes).
- **Un seul Delivery actif par `order_id`** : re-POST du même `order_id` → 200 avec la livraison
  existante (idempotence). Une fois la livraison `DELIVERED`, un nouveau POST du même `order_id`
  crée une nouvelle livraison.
- `DELIVERED` remet le livreur `available=True`, **positionné au point de dépôt** (dropoff).

## Événements publiés (Redis pub/sub)

Enveloppe commune : `{"event": "<canal>", "correlation_id": "...", "data": {...}}`.

| Canal | Moment | `data` |
|---|---|---|
| `delivery.proposed` | livraison créée (livreur choisi) | `{order_id, delivery_id, courier_id}` |
| `delivery.assigned` | auto-acceptation (simulation) | `{order_id, delivery_id, courier_id, courier_name}` |
| `delivery.picked_up` | PATCH → `PICKED_UP` | `{order_id, delivery_id, courier_id}` |
| `delivery.completed` | PATCH → `DELIVERED` | `{order_id, delivery_id}` |

Le bus d'événements est abstrait derrière un Protocol `EventBus` (`app/events.py`) :
`RedisEventBus` (redis.asyncio, prod, `DELIVERIES_EVENT_BACKEND=redis` par défaut) et
`InMemoryEventBus` (tests, aucun Redis requis — `event_backend="memory"`).

## Données de démonstration (seed)

Au démarrage (si `DELIVERIES_SEED_DATA=true`, défaut), 3 livreurs sont insérés à des positions
différentes de Paris, dont un indisponible (`courier-sofia`). Désactivé dans les tests.

## Lancement local

Depuis la racine du dépôt (venv `.venv` activé) :

```bash
cd services/deliveries
uvicorn app.main:app --reload --port 8005
```

Swagger : <http://localhost:8005/docs>.

## Docker

```bash
docker build -t service-deliveries services/deliveries
docker run --rm -p 8005:8000 service-deliveries
```

Le conteneur écoute sur le port interne 8000 (convention commune à tous les services) et
embarque un `HEALTHCHECK` sur `/health` (via `urllib`, `curl` étant absent de l'image slim).

## Tests et qualité

```bash
cd services/deliveries
python -m ruff check .
python -m ruff format --check .
python -m mypy app
python -m pytest --cov=app --cov-report=term-missing
```

Couverture minimale exigée : 80 % (`fail_under` dans `pyproject.toml`). Les tests sont
hermétiques : aucun Redis ni service externe requis (`InMemoryEventBus`, repositories
in-memory, seed désactivé).

## Architecture

```
app/
├── main.py          # create_app() : instancie l'état, monte routers/middleware/handlers
├── config.py        # pydantic-settings (préfixe env DELIVERIES_)
├── logging.py       # structlog JSON + middleware X-Correlation-Id
├── events.py        # Protocol EventBus + InMemoryEventBus + RedisEventBus + enveloppe
├── seed.py          # 3 livreurs de démo (Settings.seed_data)
├── dependencies.py  # wiring FastAPI : repositories/event bus (app.state) → services → routes
├── routes/          # HTTP uniquement — aucune logique métier
├── services/        # logique métier (assignation, transitions, haversine) + DomainError
├── repositories/    # interfaces Protocol + implémentations in-memory + entités
└── schemas/         # DTO Pydantic v2 (requêtes/réponses)
```

Principes hérités du gabarit `users` : couches strictes `routes → services → repositories`,
exceptions de domaine (`DomainError`) traduites en HTTP par un handler unique, aucun état
global de module (tout sur `app.state`, une app neuve par test), stores in-memory = mock de
base de données (ADR 0005) derrière des interfaces `Protocol`.
