# service-paiements (`payments`)

Service de paiement de la plateforme de livraison de repas : il simule un **PSP externe
instable** (taux d'échec paramétrable), garantit l'**idempotence par `order_id`** (jamais de
double débit) et gère les **remboursements partiels et totaux**. C'est la cible du circuit
breaker de l'orchestrateur SAGA (service-commandes). Structure calquée sur le gabarit
`services/users`.

## Modèle

`Payment(id, order_id, amount, currency, status, refunds[], created_at)` avec
`status ∈ {AUTHORIZED, CAPTURED, FAILED, REFUNDED, PARTIALLY_REFUNDED}`.

**Simplification prototype** : un paiement accepté passe directement
`AUTHORIZED → CAPTURED` (capture immédiate simulée par le faux PSP). `AUTHORIZED` est donc
un état transitoire jamais observable via l'API.

## Endpoints

| Méthode | Chemin | Description | Erreurs |
|---|---|---|---|
| `GET` | `/health` | Health check (hors préfixe `/api/v1`) | — |
| `POST` | `/api/v1/payments` | Débit d'une commande (`order_id`, `amount`, `currency` défaut `EUR`) → 201 ; **rejeu idempotent** : si un paiement encore capturé existe pour `order_id`, il est renvoyé tel quel avec **200** | 422 `amount ≤ 0` / payload invalide, **502 `{"detail": "PSP indisponible"}`** si le PSP simulé échoue (tentative enregistrée `FAILED`, rejouable) |
| `GET` | `/api/v1/payments` | Liste des paiements, filtre optionnel `?order_id=` (toutes les tentatives, `FAILED` incluses) | — |
| `GET` | `/api/v1/payments/{id}` | Détail d'un paiement | 404 |
| `POST` | `/api/v1/payments/{id}/refunds` | Remboursement (`amount` optionnel — défaut : **restant remboursable** → remboursement total ; `reason`) → 201, paiement mis à jour | 404, 409 paiement non `CAPTURED`/`PARTIALLY_REFUNDED`, 422 cumul > montant capturé ou `amount ≤ 0` |
| `POST` | `/api/v1/_chaos` | **Dev/démo uniquement** : modifie à chaud le taux d'échec du PSP (`{"failure_rate": 0.0–1.0}`) — sert à déclencher le circuit breaker pendant la démo résilience | 422 hors bornes |

Les erreurs sont normalisées au format `{"detail": "..."}`. Chaque réponse porte un header
`X-Correlation-Id` (repris de la requête ou généré), injecté dans les logs JSON (structlog).

### Règles métier

- **Idempotence par `order_id`** : un `POST /payments` alors qu'un paiement `CAPTURED` ou
  `PARTIALLY_REFUNDED` existe déjà pour la commande renvoie ce paiement (200), sans nouveau
  débit. Une tentative `FAILED` ne bloque pas : le POST suivant retente auprès du PSP.
  Un paiement intégralement remboursé (`REFUNDED`) ne bloque pas non plus (l'argent a été
  rendu, un nouveau débit est légitime).
- **Remboursements cumulables** : partiels et totaux, tant que le cumul ne dépasse pas le
  montant capturé (sinon 422). Statut : `PARTIALLY_REFUNDED` si cumul < capturé,
  `REFUNDED` si cumul == capturé. Montants arrondis au centime.
- **PSP simulé** : la création échoue avec la probabilité `failure_rate`
  (env `PAYMENTS_FAILURE_RATE`, défaut `0.0`, ou `POST /_chaos` à chaud). La source
  aléatoire est **injectée** (callable sur `app.state.psp_gateway`) : les tests la
  remplacent par un stub déterministe — aucun `random.random()` câblé en dur.

## Configuration (env, préfixe `PAYMENTS_`)

| Variable | Défaut | Rôle |
|---|---|---|
| `PAYMENTS_FAILURE_RATE` | `0.0` | Probabilité d'échec du PSP simulé (0.0–1.0) |
| `PAYMENTS_LOG_LEVEL` | `INFO` | Niveau de log structlog |

## Lancement local

Depuis la racine du dépôt (venv `.venv` activé) :

```bash
cd services/payments
uvicorn app.main:app --reload --port 8004
```

Swagger : <http://localhost:8004/docs>.

## Docker

```bash
docker build -t service-payments services/payments
docker run --rm -p 8004:8000 -e PAYMENTS_FAILURE_RATE=0.3 service-payments
```

Le conteneur écoute sur le port interne 8000 (convention commune à tous les services) et
embarque un `HEALTHCHECK` sur `/health` (via `urllib`, `curl` étant absent de l'image slim).

## Tests et qualité

```bash
cd services/payments
python -m ruff check .
python -m ruff format --check .
python -m mypy app
python -m pytest --cov=app --cov-report=term-missing
```

Couverture minimale exigée : 80 % (`fail_under` dans `pyproject.toml`). Les tests sont
hermétiques : aucun Redis ni service externe requis ; le PSP est piloté par un stub
aléatoire déterministe (`tests/conftest.py::StubRng`).

## Architecture (conforme au gabarit `services/users`)

```
app/
├── main.py          # create_app() : instancie l'état, monte routers/middleware/handlers
├── config.py        # pydantic-settings (préfixe env PAYMENTS_)
├── logging.py       # structlog JSON + middleware X-Correlation-Id
├── dependencies.py  # wiring FastAPI : repository + gateway (app.state) → services → routes
├── routes/          # HTTP uniquement — aucune logique métier
├── services/        # logique métier, exceptions de domaine, PSP simulé (psp.py)
├── repositories/    # interface Protocol + implémentation in-memory + entités
└── schemas/         # DTO Pydantic v2 (requêtes/réponses)
```

Principes : couches strictes `routes → services → repositories` ; exceptions de domaine
(`DomainError`) traduites en HTTP par un handler unique ; **pas d'état global de module**
(stores et gateway instanciés dans `create_app()`, portés par `app.state`) ; store
in-memory = mock de base de données (ADR 0005) derrière une interface `Protocol`.
