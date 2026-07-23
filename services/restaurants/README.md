# service-restaurants (`restaurants`)

Service catalogue de la plateforme de livraison de repas : profils restaurants (horaires
d'ouverture inclus), menus (plats, prix, options, disponibilité), **recherche** (cuisine, texte,
distance), **validation de commande** (appelée par la saga du service commandes) et **kitchen
tickets** (acceptation/refus, préparation). Service le plus sollicité en lecture (ADR 0001/0002).

## Endpoints

| Méthode | Chemin | Description | Erreurs |
|---|---|---|---|
| `GET` | `/health` | Health check (hors préfixe `/api/v1`) | — |
| `GET` | `/api/v1/restaurants?cuisine=&q=&lat=&lng=&radius_km=` | Recherche (filtres combinables, cf. ci-dessous) | 422 lat sans lng |
| `POST` | `/api/v1/restaurants` | Création d'un restaurant (horaires inclus) → 201 | 422 payload invalide |
| `GET` | `/api/v1/restaurants/{id}` | Profil **avec menu détaillé** | 404 |
| `PUT` | `/api/v1/restaurants/{id}` | Remplacement du profil (horaires, `auto_accept`) | 404, 422 |
| `POST` | `/api/v1/restaurants/{id}/menu-items` | Création d'un plat → 201 | 404, 422 |
| `PUT` | `/api/v1/restaurants/{id}/menu-items/{itemId}` | Remplacement d'un plat (disponibilité incluse) | 404, 422 |
| `DELETE` | `/api/v1/restaurants/{id}/menu-items/{itemId}` | Suppression → 204 | 404 |
| `POST` | `/api/v1/restaurants/{id}/order-validations` | Validation de commande (saga, étape 2) → **toujours 200** avec verdict | 404 restaurant inconnu, 422 |
| `POST` | `/api/v1/restaurants/{id}/kitchen-tickets` | Ticket cuisine : 201 `ACCEPTED` si `auto_accept`, sinon **409** | 404, 409 refus, 422 |
| `PATCH` | `/api/v1/kitchen-tickets/{id}` | Transition `ACCEPTED→PREPARING→READY` | 404, 409 transition invalide, 422 |

Les erreurs sont normalisées au format `{"detail": "..."}`. Chaque réponse porte un header
`X-Correlation-Id` (repris de la requête ou généré), injecté dans les logs JSON (structlog).

### Recherche

Filtres combinables de `GET /api/v1/restaurants` :

- `cuisine=` : égalité insensible à la casse sur `cuisine_type` ;
- `q=` : sous-chaîne insensible à la casse sur le **nom du restaurant OU le nom d'un plat** ;
- `lat=&lng=&radius_km=` : distance haversine simple, rayon par défaut **5 km**. `lat` et `lng`
  doivent être fournis ensemble (sinon 422).

### Horaires d'ouverture

`opening_hours` est une liste de créneaux `{day, open, close}` : `day` suit la convention Python
(**0 = lundi … 6 = dimanche**), `open`/`close` au format `"HH:MM"` avec `open < close` (pas de
créneau passant minuit dans le prototype). Un restaurant sans créneau est considéré fermé.

### Validation de commande (choix de conception)

`POST /order-validations` répond **toujours 200** avec le verdict :

- `{"valid": true, "subtotal": 31.0}` si le restaurant est **ouvert** à l'instant demandé
  (`at` optionnel, défaut : maintenant), tous les plats **disponibles** et les **prix concordants**
  (comparés au prix catalogue) ;
- `{"valid": false, "reasons": [...]}` sinon (raisons cumulées).

Choix assumé : une commande invalide n'est pas une erreur HTTP mais un résultat métier — cela
simplifie l'orchestrateur SAGA (une seule branche « appel réussi », le verdict pilote la
compensation). Le 404 reste réservé au restaurant inexistant. Le `subtotal` est calculé à partir
des prix **catalogue** (hors options, les prix des options étant portés par le service commandes
dans le snapshot de la commande).

### Kitchen tickets et événement `order.ready`

- `POST /restaurants/{id}/kitchen-tickets` : si `auto_accept` est vrai → 201, statut `ACCEPTED` ;
  sinon → **409** `{"detail": "commande refusée par le restaurant"}` (le ticket est tout de même
  enregistré en statut `REFUSED` pour l'audit). Le refus paramétrable sert à la démo de
  **compensation SAGA** (remboursement puis annulation côté commandes).
- `PATCH /kitchen-tickets/{id}` : transitions **strictes** `ACCEPTED→PREPARING→READY` ; toute
  autre transition → 409. Les lignes du ticket ne sont pas revalidées ici : la commande a déjà été
  validée à l'étape 2 de la saga.
- Au passage à `READY`, l'événement `order.ready` est publié sur le bus :

```json
{"event": "order.ready", "correlation_id": "…", "data": {"order_id": "…", "restaurant_id": "…", "pickup_address": "…"}}
```

### EventBus

`app/events.py` définit un Protocol `EventBus` avec deux implémentations, choisies dans
`create_app()` via `Settings.event_bus` (portées par `app.state`, jamais en global de module) :

- `InMemoryEventBus` (défaut) : enregistre les événements en mémoire — utilisé par les tests pour
  asserter les publications, **aucun Redis requis** ;
- `RedisEventBus` (`RESTAURANTS_EVENT_BUS=redis`, prod/docker-compose) : publie le payload JSON
  sur le canal Redis pub/sub (`redis.asyncio`, connexion paresseuse).

### Seed de démonstration

Au démarrage (flag `RESTAURANTS_SEED_DATA`, défaut `true`, désactivé dans les tests),
`app/seed.py` insère 3 restaurants réalistes avec des ids stables :

| Id | Nom | Cuisine | Particularité |
|---|---|---|---|
| `resto-bella-napoli` | La Bella Napoli | italian | 5 plats avec options |
| `resto-sakura-sushi` | Sakura Sushi | japanese | 5 plats avec options |
| `resto-chez-refus` | Chez Refus | french | **`auto_accept=false`** → refuse les tickets (démo compensation SAGA), fermé le dimanche |

## Configuration (préfixe env `RESTAURANTS_`)

| Variable | Défaut | Rôle |
|---|---|---|
| `RESTAURANTS_LOG_LEVEL` | `INFO` | Niveau de log structlog |
| `RESTAURANTS_EVENT_BUS` | `memory` | `memory` ou `redis` |
| `RESTAURANTS_REDIS_URL` | `redis://localhost:6379/0` | URL Redis (si `event_bus=redis`) |
| `RESTAURANTS_SEED_DATA` | `true` | Seed du catalogue de démo au démarrage |

## Lancement local

Depuis la racine du dépôt (venv `.venv` activé) :

```bash
cd services/restaurants
uvicorn app.main:app --reload --port 8002
```

Swagger : <http://localhost:8002/docs>.

## Docker

```bash
docker build -t service-restaurants services/restaurants
docker run --rm -p 8002:8000 service-restaurants
```

Le conteneur écoute sur le port interne 8000 (convention commune à tous les services) et
embarque un `HEALTHCHECK` sur `/health` (via `urllib`, `curl` étant absent de l'image slim).

## Tests et qualité

```bash
cd services/restaurants
python -m ruff check .
python -m ruff format --check .
python -m mypy app
python -m pytest --cov=app --cov-report=term-missing
```

Couverture minimale exigée : 80 % (`fail_under` dans `pyproject.toml`). Les tests sont
hermétiques : aucun Redis ni service externe requis (bus in-memory, repositories in-memory).

## Architecture

Structure identique au gabarit `services/users` : couches strictes
`routes → services → repositories`, exceptions de domaine (`DomainError`) traduites par un
handler unique, stores et bus d'événements instanciés dans `create_app()` et portés par
`app.state` (état vierge par test), interfaces `Protocol` pour les repositories et l'`EventBus`,
DTO Pydantic v2, dataclasses pour les entités. Les prix sont des `float` arrondis à 2 décimales
(cohérent dans tout le service) ; une vraie monnaie décimale viendrait avec la vraie base.
