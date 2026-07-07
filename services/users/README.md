# service-utilisateurs (`users`)

Service d'identité de la plateforme de livraison de repas : inscription, authentification par
token opaque, profil et carnet d'adresses. **Premier service du prototype, il sert de gabarit
structurel aux autres services.**

## Endpoints

| Méthode | Chemin | Description | Erreurs |
|---|---|---|---|
| `GET` | `/health` | Health check (hors préfixe `/api/v1`) | — |
| `POST` | `/api/v1/users` | Inscription (`email`, `password`, `name`, `phone`) → 201 | 409 email déjà utilisé, 422 payload invalide |
| `POST` | `/api/v1/auth/login` | Login → token opaque (`access_token`) | 401 identifiants invalides |
| `GET` | `/api/v1/users/me` | Profil de l'utilisateur authentifié | 401 token invalide |
| `PUT` | `/api/v1/users/me` | Mise à jour du profil (`name`, `phone`) | 401 |
| `GET` | `/api/v1/users/me/addresses` | Liste des adresses | 401 |
| `POST` | `/api/v1/users/me/addresses` | Création d'adresse (`label`, `street`, `city`, `lat`, `lng`) → 201 | 401, 422 |
| `PUT` | `/api/v1/users/me/addresses/{id}` | Remplacement d'une adresse | 401, 404 adresse inconnue |
| `DELETE` | `/api/v1/users/me/addresses/{id}` | Suppression → 204 | 401, 404 |

Authentification : header `Authorization: Bearer <token>`. Les erreurs sont normalisées au
format `{"detail": "..."}` avec le code HTTP approprié.

Chaque réponse porte un header `X-Correlation-Id` (repris de la requête ou généré), également
injecté dans les logs JSON (structlog).

## Lancement local

Depuis la racine du dépôt (venv `.venv` activé) :

```bash
cd services/users
uvicorn app.main:app --reload --port 8001
```

Swagger : <http://localhost:8001/docs>.

## Docker

```bash
docker build -t service-users services/users
docker run --rm -p 8001:8000 service-users
```

Le conteneur écoute sur le port interne 8000 (convention commune à tous les services) et
embarque un `HEALTHCHECK` sur `/health` (via `urllib`, `curl` étant absent de l'image slim).

## Tests et qualité

```bash
cd services/users
python -m ruff check .
python -m ruff format --check .
python -m mypy app
python -m pytest --cov=app --cov-report=term-missing
```

Couverture minimale exigée : 80 % (`fail_under` dans `pyproject.toml`). Les tests sont
hermétiques : aucun Redis ni service externe requis.

## Architecture (gabarit pour les autres services)

```
app/
├── main.py          # create_app() : instancie l'état, monte routers/middleware/handlers
├── config.py        # pydantic-settings (préfixe env USERS_)
├── logging.py       # structlog JSON + middleware X-Correlation-Id
├── dependencies.py  # wiring FastAPI : repositories (app.state) → services → routes
├── routes/          # HTTP uniquement — aucune logique métier
├── services/        # logique métier + exceptions de domaine (mappées en HTTP dans main.py)
├── repositories/    # interfaces Protocol + implémentations in-memory + entités
└── schemas/         # DTO Pydantic v2 (requêtes/réponses)
```

Principes :

- **Couches strictes** : `routes → services → repositories`. Les routes ne contiennent aucune
  logique ; les services lèvent des exceptions de domaine (`DomainError`) traduites en réponses
  HTTP normalisées par un exception handler unique.
- **Pas d'état global de module** : les stores sont instanciés dans `create_app()` et portés par
  `app.state`. Chaque test construit une application neuve → état vierge garanti.
- **Store in-memory = mock de base de données** (ADR 0005). Les repositories sont définis par des
  interfaces `Protocol` : brancher une vraie base (SQLAlchemy) ou Redis ne touche ni les services
  ni les routes.
- **Service stateless par design** : en production, le store de tokens (`TokenStore`) serait
  Redis afin de pouvoir load-balancer plusieurs instances ; l'implémentation in-memory n'est
  valable que pour le prototype mono-instance.
- **Mots de passe** : hash PBKDF2-SHA256 salé via `hashlib` (stdlib), jamais de plaintext stocké,
  comparaison en temps constant.
