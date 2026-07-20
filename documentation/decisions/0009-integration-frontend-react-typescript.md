# ADR 0009 — Intégration de l'application frontend React / TypeScript et de la Vue Testeur (QA)

- **Statut** : Accepté
- **Date** : 2026-07-20
- **Décideur** : Équipe Fullstack / Agent Planificateur

## Contexte

Dans le cadre du prototype de démonstration de l'architecture microservices FitMeal, les services backend fournissent les endpoints REST OpenAPI pour l'ensemble des cas d'utilisation (authentification, catalogue, panier, saga de commande, paiement, livraison, notifications). Initialement, l'ADR 0008 prévoyait de limiter les tests à Swagger et à des scripts. Cependant, pour répondre pleinement aux exigences de l'énoncé ([enonce.md](../../enonce.md)) et du framework de gouvernance (`CLAUDE.md` + règles de projet), une interface utilisateur web monopage (SPA) en **React 18 + TypeScript + Vite + Tailwind CSS** a été intégrée et conteneurisée. De plus, une **Vue Testeur (Tester Dashboard)** est requise pour piloter les scénarios QA et valider visuellement la plateforme.

## Options envisagées

1. **Pas de frontend (conserver l'ADR 0008)** :
   - *Avantages* : Moins de code d'interface à maintenir.
   - *Inconvénients* : Expérience utilisateur absente, démonstration limitée aux appels cURL/Swagger, non-respect du framework fullstack.

2. **Frontend React / TypeScript dédié avec Nginx & Vue Testeur (Option Retenue)** :
   - *Avantages* : Interface réactive, moderne et accessible ; typage strict TypeScript ; consommation centralisée de la Gateway API (`/api/v1/*`) ; présence de la Vue Testeur (`/tester`) pour simuler le basculement PSP Chaos, réinitialiser le cache local et suivre la santé des services.
   - *Inconvénients* : Légère augmentation de la surface de test (Vitest) et ajout du service `frontend` au `docker-compose.yml`.

## Décision

Nous adoptons l'**Option 2** :
- L'application frontend est développée sous `frontend/` avec React 18, TypeScript, Vite, Tailwind CSS, TanStack Query, React Router v6, Axios et Sonner.
- Une **Vue Testeur (Tester Dashboard)** est exposée sur la route `/tester` pour la validation QA (santé des services, simulation Chaos PSP, gestion des sessions de test).
- L'application est conteneurisée via un build multi-stage Node/Nginx (`frontend/Dockerfile`) et intégrée à `docker-compose.yml`.

## Conséquences

- **Positives** :
  - Démonstration fluide de l'ensemble du parcours utilisateur (recherche, panier, checkout, suivi SAGA en temps réel).
  - Validation QA facilitée par le Dashboard de test intégré.
  - Architecture fullstack conteneurisée clé en main via `docker compose up --build`.
- **Négatives** :
  - Nécessite d'exécuter `npm run test` (Vitest) et `npm run lint` pour garantir la couverture ≥ 80% côté frontend.
