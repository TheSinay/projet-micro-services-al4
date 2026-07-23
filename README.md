# 🍱 FitMeal / MiamGo — Architecture Microservices & Application Fullstack

> **Projet d'Architecture Microservices — Plateforme de Livraison de Repas**  
> MVP Fullstack avec 6 Microservices FastAPI, Gateway Nginx, Bus Redis Pub/Sub, SAGA Orchestrée, Circuit Breaker et Frontend React / TypeScript.

---

## 📌 Livrables du Projet

Conformément au cahier des charges et aux exigences de l'énoncé ([enonce.md](enonce.md)), l'ensemble des livrables attendus est formalisé et disponible dans le dépôt :

| Livrable Attendu | Emplacement & Description |
|---|---|
| 📑 **1. Documentation d'Architecture** | [documentation/architecture.md](documentation/architecture.md) — Analyse DDD, Bounded Contexts, Responsabilités, Modèles de données & ADRs (0001 à 0011). |
| 📐 **2. Diagrammes Techniques** | [documentation/diagrammes.md](documentation/diagrammes.md) — Diagrammes C4 Niveau 1 & 2, Diagrammes de Séquence SAGA, Circuit Breaker, Compensations et ERD. |
| 📜 **3. Contrats d'API REST** | [documentation/contrats-api.md](documentation/contrats-api.md) — Spécifications OpenAPI 3.0 de l'ensemble des endpoints des 6 microservices. |
| 💻 **4. Prototype Minimal & Code** | Code source complet des 6 services (`/services`), Gateway (`/gateway`), Frontend (`/frontend`), `docker-compose.yml` & `Makefile`. |
| 🎤 **5. Support de Présentation Orale** | [documentation/presentation-orale.md](documentation/presentation-orale.md) — Trame de 10 slides, script d'oral chrono 15 min, guide de démo pas-à-pas & Q&R Jury. |

---

## 🏗️ Architecture Globale

L'application est structurée selon les principes du **Domain-Driven Design (DDD)** et de la **découpe par charge** :

```
                               ┌─────────────────────────┐
                               │   Frontend React 18     │
                               │   (Client / QA / Dashboard)│
                               └────────────┬────────────┘
                                            │ HTTP / REST
                               ┌────────────▼────────────┐
                               │   API Gateway Nginx     │
                               │   (Port 80 / 8080)      │
                               └────────────┬────────────┘
                                            │
        ┌──────────────┬──────────────┬─────┴────────┬──────────────┬──────────────┐
        │              │              │              │              │              │
 ┌──────▼──────┐┌──────▼──────┐┌──────▼──────┐┌──────▼──────┐┌──────▼──────┐┌──────▼──────┐
 │  users      ││ restaurants ││ orders      ││ payments    ││ deliveries  ││notifications│
 │  (:8001)    ││ (:8002)     ││ (:8003)     ││ (:8004)     ││ (:8005)     ││ (:8006)     │
 └──────┬──────┘└──────┬──────┘└──────┬──────┘└──────┬──────┘└──────┬──────┘└──────┬──────┘
        │              │              │              │              │              │
        └──────────────┴──────────────┼──────────────┴──────────────┴──────────────┘
                                      │ Pub/Sub & Caches
                               ┌──────▼──────┐
                               │    Redis    │
                               └─────────────┘
```

### Inventaire des Microservices
1. **`service-utilisateurs` (`users` - :8001)** : Auth JWT, profils, adresses, RBAC (`client`, `restaurant_owner`, `courier`).
2. **`service-restaurants` (`restaurants` - :8002)** : Établissements, catalogue menus, validation de commande, kitchen tickets.
3. **`service-commandes` (`orders` - :8003)** : Panier Redis, **Orchestrateur SAGA**, calcul prix, évaluations.
4. **`service-paiements` (`payments` - :8004)** : Encaissement via PSP simulé, idempotence par `order_id`, remboursements, PSP Chaos Mode.
5. **`service-livraisons` (`deliveries` - :8005)** : Flotte livreurs, geofencing, attribution de courses, tracking.
6. **`service-notifications` (`notifications` - :8006)** : Consommation d'événements Redis Pub/Sub, envois simulés (Email/Push/SMS).

---

## ⚡ Patterns Clés Implémentés

1. **Transaction Distribuée SAGA (Orchestration Hybride)** :
   - Orchestration synchrone de la phase critique : *Validation Restaurant* ➔ *Capture Paiement* ➔ *Kitchen Ticket Cuisine*.
   - **Compensations Automatiques** : Si la cuisine refuse après paiement capturé, la SAGA déclenche un **remboursement intégral** immédiat auprès du PSP.
2. **Résilience & Fault Tolerance** :
   - **Timeout** (2.0s par appel HTTP sortant).
   - **Retry Policy** (x3 avec backoff exponentiel + jitter).
   - **Circuit Breaker** (`CLOSED` ➔ `OPEN` ➔ `HALF_OPEN`) sur l'appel PSP pour réagir instantanément en cas d'indisponibilité.
3. **Chorégraphie Événementielle** :
   - Communication asynchrone sur Redis Pub/Sub (`order.confirmed`, `order.ready`, `delivery.assigned`, `delivery.completed`).

---

## 🚀 Démarrage Rapide (Docker Compose)

### Prérequis
- Docker Desktop et Docker Compose v2.

### Lancer l'application
```bash
docker compose up --build
```

L'application sera accessible sur :
- 🌐 **Frontend App & Dashboard QA** : [http://localhost](http://localhost) (ou `http://localhost:5173` en dev)
- ⚙️ **API Gateway Nginx** : [http://localhost:8080/health](http://localhost:8080/health)

### Swagger / Documentation OpenAPI interactive des microservices
- **Users** : [http://localhost:8001/docs](http://localhost:8001/docs)
- **Restaurants** : [http://localhost:8002/docs](http://localhost:8002/docs)
- **Orders** : [http://localhost:8003/docs](http://localhost:8003/docs)
- **Payments** : [http://localhost:8004/docs](http://localhost:8004/docs)
- **Deliveries** : [http://localhost:8005/docs](http://localhost:8005/docs)
- **Notifications** : [http://localhost:8006/docs](http://localhost:8006/docs)

---

## 🧪 Exécution des Tests Automatisés

Le projet garantit une couverture de tests supérieure à 95% avec zéro anomalie.

### Tests Backend (Pytest, Coverage, Ruff, Mypy)
```bash
# Tests unitaires & couverture backend
make test
# ou individuellement :
pytest services/orders --cov=app
pytest services/restaurants --cov=app
```

### Tests Frontend (Vitest & ESLint)
```bash
cd frontend
npm run test -- --run
npm run lint
```

---

## 📁 Structure du Dépôt

```
.
├── documentation/             # 📑 Documentation complète et livrables
│   ├── architecture.md        # Architecture globale et choix DDD
│   ├── diagrammes.md          # Diagrammes C4, SAGA & Séquences Mermaid
│   ├── contrats-api.md        # Spécifications REST / OpenAPI
│   ├── presentation-orale.md  # Trame d'oral 15 min & Q&R Jury
│   └── decisions/             # ADRs 0001 à 0011 (Records de décisions)
├── services/                  # ⚙️ 6 Microservices FastAPI
│   ├── users/
│   ├── restaurants/
│   ├── orders/
│   ├── payments/
│   ├── deliveries/
│   └── notifications/
├── gateway/                   # 🌐 Proxy Nginx (API Gateway)
├── frontend/                  # 💻 App Web React 18 / Vite / Tailwind
├── docker-compose.yml         # 🐳 Orchestration des conteneurs
├── Makefile                   # 🛠️ Commandes utilitaires (`make test`, `make run`)
└── enonce.md                  # 📜 Cahier des charges initial
```
