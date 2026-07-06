# Architecture

Vue d'ensemble de l'application en architecture microservices.
Ce document est maintenu par l'agent **documentaliste** et doit refléter l'état réel des services.

## Principes directeurs

- **Découpe par charge** : un composant fortement sollicité est isolé dans son propre microservice (voir [ADR 0001](decisions/0001-strategie-decoupe-microservices-par-charge.md)).
- **Stateless** : aucun état en mémoire locale ; sessions/cache/état partagé dans **Redis** → services load-balançables horizontalement.
- **Communication** : HTTP/REST entre services via `httpx` (async). Message broker uniquement si justifié par un ADR. Jamais d'import de code d'un service à l'autre.
- **Santé** : chaque service expose `/health`.
- **Reverse proxy** (futur) : Nginx/Traefik devant N instances de chaque service.

## Stack

- **Backend** : Python 3.12+, FastAPI, Pydantic, SQLAlchemy + Alembic, httpx, Redis, structlog. Tests : pytest.
- **Frontend** : React + TypeScript, Vite, Tailwind + shadcn/ui, react-query, react-hook-form + zod, axios. Tests : Vitest.
- **Infra** : Docker + docker-compose ; Redis partagé ; bases par service selon besoin.

## Schéma des services

```
                         ┌──────────────────────┐
                         │   Frontend (React)   │
                         └──────────┬───────────┘
                                    │ HTTP/REST (axios, couche api/)
                    ┌───────────────┴────────────────┐
                    │      Reverse proxy (futur)      │
                    │        Nginx / Traefik          │
                    └───────────────┬────────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
      (aucun service défini pour l'instant — à compléter)
              │                     │                     │
              └─────────────────────┴─────────────────────┘
                                    │
                          ┌─────────┴─────────┐
                          │   Redis (état     │
                          │  partagé / cache) │
                          └───────────────────┘
```

## Inventaire des services

| Service | Rôle | Charge | Base/Schéma | Statut |
|---------|------|--------|-------------|--------|
| _(aucun)_ | — | — | — | À définir |

> Ce tableau est mis à jour à chaque création de service, avec un ADR justifiant la découpe.

## Conventions inter-services

- Contrats d'API documentés (OpenAPI généré par FastAPI, exposé sur `/docs`).
- Erreurs normalisées (code, message, détails) — le frontend ne montre jamais l'erreur brute.
- Identifiants de corrélation propagés dans les en-têtes pour le traçage (logs `structlog`).
