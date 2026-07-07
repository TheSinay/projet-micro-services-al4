# service-notifications (`notifications`)

Consommateur d'événements de la plateforme : il s'abonne aux canaux Redis pub/sub
(`order.*`, `delivery.*`) et « envoie » des notifications **simulées** (email / push / SMS) —
l'envoi est matérialisé par une ligne de log structurée (structlog) et la notification est
persistée in-memory pour la démo et le frontend. Structure calquée sur le gabarit `services/users`.

## Endpoints

| Méthode | Chemin | Description | Erreurs |
|---|---|---|---|
| `GET` | `/health` | Health check (hors préfixe `/api/v1`) | — |
| `GET` | `/api/v1/notifications` | Liste des notifications, **plus récentes d'abord**, filtrable par `?recipient_type=` (`client`/`restaurant`/`courier`), `?recipient_id=`, `?event=` | 422 `recipient_type` inconnu |

Les erreurs sont normalisées au format `{"detail": "..."}`. Chaque réponse porte un header
`X-Correlation-Id` (repris de la requête ou généré), injecté dans les logs JSON.

## Événements consommés et règles de routage

Enveloppe commune (ADR 0004) : `{"event": "<canal>", "correlation_id": "...", "data": {...}}`.
Le `correlation_id` de l'événement est **propagé dans la notification** persistée et dans les
logs d'envoi (traçabilité bout-en-bout).

Table déclarative (`app/services/dispatch.py`, `ROUTING_TABLE`) :

| Événement | Destinataires (clé dans `data`) | Canaux | Sujet |
|---|---|---|---|
| `order.confirmed` | client (`user_id`) | email + push | « Votre commande est confirmée » |
| | restaurant (`restaurant_id`) | push | « Nouvelle commande à préparer » |
| `order.cancelled` | client (`user_id`) | email + push | « Votre commande est annulée » (corps : raison + remboursement via `reason`, `refund_amount`/`refunded`) |
| `order.ready` | — (événement technique, ignoré, log debug) | — | — |
| `delivery.assigned` | client (`user_id`) | push | « Votre livreur est en route vers le restaurant » |
| | courier (`courier_id`) | push | « Nouvelle course assignée » |
| `delivery.picked_up` | client (`user_id`) | push | « Votre commande est en route » |
| `delivery.completed` / `order.delivered` | client (`user_id`) | email + push | « Bon appétit ! » |
| *(inconnu)* | — (ignoré sans crash, log warning) | — | — |

Règles de tolérance :

- **Id destinataire absent du payload** → les destinataires présents sont quand même notifiés,
  un warning `recipient_missing_in_payload` est loggé pour l'absent.
- **Événement inconnu ou enveloppe malformée** (JSON invalide, payload non-objet) → ignoré
  sans crash, log warning.

## Architecture de consommation

- `app/subscriber.py` : boucle `redis.asyncio` pub/sub, démarrée dans le **lifespan** de
  l'application **uniquement si** `NOTIFICATIONS_EVENT_BACKEND=redis`. La boucle est un
  transport mince derrière un Protocol `PubSubClient` : toute la logique vit dans
  `NotificationDispatcher.handle_event`, **fonction pure vis-à-vis de Redis**, appelée
  directement dans les tests avec des payloads dict (et via un faux client pub/sub pour la
  boucle elle-même).
- Défaut `event_backend="memory"` (aucun consumer démarré) → tests hermétiques ; l'image
  Docker force `NOTIFICATIONS_EVENT_BACKEND=redis` (docker-compose fournit `NOTIFICATIONS_REDIS_URL`).
- Persistance derrière le Protocol `NotificationRepository` (implémentation in-memory, ADR 0005).

## Lancement local

Depuis la racine du dépôt (venv `.venv` activé) :

```bash
cd services/notifications
uvicorn app.main:app --reload --port 8006
```

Swagger : <http://localhost:8006/docs>.

## Docker

```bash
docker build -t service-notifications services/notifications
docker run --rm -p 8006:8000 service-notifications
```

Le conteneur écoute sur le port interne 8000 (convention commune), embarque un `HEALTHCHECK`
sur `/health` (via `urllib`, `curl` étant absent de l'image slim) et active le backend Redis.

## Tests et qualité

```bash
cd services/notifications
python -m ruff check .
python -m ruff format --check .
python -m mypy app
python -m pytest --cov=app --cov-report=term-missing
```

Couverture minimale exigée : 80 % (`fail_under` dans `pyproject.toml`). Les tests sont
hermétiques : **aucun Redis requis** (handlers appelés directement, boucle pub/sub testée avec
un faux client ; seul le câblage lifespan vers un Redis réel est exclu de la couverture,
`pragma: no cover` justifié).

## Architecture

```
app/
├── main.py          # create_app() : état sur app.state, lifespan (consumer Redis conditionnel)
├── config.py        # pydantic-settings (préfixe env NOTIFICATIONS_, event_backend=memory)
├── logging.py       # structlog JSON + middleware X-Correlation-Id
├── subscriber.py    # boucle pub/sub (Protocol PubSubClient) + décodage des messages
├── dependencies.py  # wiring FastAPI : repository (app.state) → service → routes
├── routes/          # HTTP uniquement — aucune logique métier
├── services/        # dispatch.py (table de routage + dispatcher), notification_service.py, DomainError
├── repositories/    # Protocol NotificationRepository + implémentation in-memory + entités
└── schemas/         # DTO Pydantic v2 (réponses)
```

Principes hérités du gabarit `users` : couches strictes `routes → services → repositories`,
exceptions de domaine (`DomainError`) traduites en HTTP par un handler unique, aucun état
global de module (tout sur `app.state`, une app neuve par test), store in-memory = mock de
base de données (ADR 0005) derrière une interface `Protocol`.
