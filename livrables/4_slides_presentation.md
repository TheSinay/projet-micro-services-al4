---
marp: true
theme: default
paginate: true
header: "FitMeal / MiamGo — Architecture Microservices"
footer: "Soutenance de Projet Microservices | 2026"
---

# 🍱 FitMeal / MiamGo
## Architecture Microservices & Application Fullstack

**Conception et réalisation d'une plateforme résiliente de livraison de repas**

- **Équipe de développement**
- **Architecture** : FastAPI, Gateway Nginx, Redis Pub/Sub, SAGA Orchestrée, Circuit Breaker & React/TypeScript
- **Date** : 2026

---

# 🎯 1. Contexte Métier & Problématique

### Enjeux de la Livraison de Repas
- **Trois acteurs clés aux besoins divergents** :
  - **Clients** : recherche rapide, commande fluide, suivi en temps réel.
  - **Restaurateurs** : gestion du menu, validation et cadence de cuisine.
  - **Livreurs** : affectation géolocalisée et confirmation de course.

### Défis Techniques
- **Forte asymétrie de charge** : Consultation intensive du catalogue vs Transactions d'achat critiques.
- **Transactions Distribuées** : Pas de BDD unique ➔ Nécessité de gérer la cohérence entre services sans verrou ACID.
- **Résilience** : Risque de pannes des services externes (PSP, réseau).

---

# 🧩 2. Analyse du Domaine & Découpage (DDD)

### Découpe par Charge & Responsabilités (ADR 0001 & ADR 0002)

| Service Microservice | Bounded Context(s) | Motif du Découpage |
|---|---|---|
| **`service-utilisateurs`** | Identité & Comptes | Source de vérité RBAC (`client`, `restaurant_owner`, `courier`). |
| **`service-restaurants`** | Catalogue & Menus | **Forte consultation** isolée des écritures de commande. |
| **`service-commandes`** | Checkout & Panier | **Orchestrateur SAGA** et état de commande. |
| **`service-paiements`** | Paiement & PSP | Criticité maximale, idempotence et Circuit Breaker. |
| **`service-livraisons`** | Flotte & Tracking | Geofencing et calcul d'attribution livreurs. |
| **`service-notifications`** | Notifications | Consommation asynchrone d'événements. |

---

# 🌐 3. Architecture Globale (C4 Niveau 2)

```
                            ┌─────────────────────────┐
                            │   Frontend React 18     │
                            │ (Client / QA / Dashboard)│
                            └────────────┬────────────┘
                                         │ REST
                            ┌────────────▼────────────┐
                            │   API Gateway Nginx     │
                            │   (Port 80 / 8080)      │
                            └────────────┬────────────┘
                                         │
     ┌──────────────┬──────────────┬─────┴────────┬──────────────┬──────────────┐
┌────▼────┐    ┌────▼────┐    ┌────▼────┐    ┌────▼────┐    ┌────▼────┐    ┌────▼────┐
│  users  │    │resto-cat│    │ orders  │    │ payments│    │deliveries│    │ notifs  │
└────┬────┘    └────┬────┘    └────┬────┘    └────┬────┘    └────┬────┘    └────┬────┘
     └──────────────┴──────────────┼──────────────┴──────────────┴──────────────┘
                                   │ Pub/Sub & Caches
                            ┌──────▼──────┐
                            │    Redis    │
                            └─────────────┘
```

---

# 🔄 4. Transaction Distribuée : Pattern SAGA Orchestré

### Orchestration Hybride (ADR 0003)

1. **Étape 1 : Création Commande** ➔ Statut `RECEIVED` (saga_state: `VALIDATING`).
2. **Étape 2 : Validation Restaurant** ➔ Vérification synchrone du sous-total et des plats.
3. **Étape 3 : Capture Paiement** ➔ Appel idempotent au service paiements.
4. **Étape 4 : Ticket Cuisine** ➔ Inscription de la commande en cuisine.
5. **Étape 5 : Confirmation** ➔ Passage en `PREPARING` + Événement `order.confirmed`.

### 🛡️ Transactions Compensatoires
- En cas de **Refus Cuisine (409)** après capture bancaire :
  ➔ **La SAGA déclenche automatiquement un remboursement intégral** auprès du PSP et annule la commande (`CANCELLED_REFUSED`).

---

# 🛡️ 5. Pattern de Résilience & PSP Chaos

### Protection contre les pannes du PSP (ADR 0007)

- **Timeout Policy** : Limitée à **2,0s** sur chaque appel HTTP amont.
- **Retry Policy** : **3 tentatives** avec backoff exponentiel et jitter (0.1s, 0.2s, 0.4s).
- **Circuit Breaker (`CLOSED ➔ OPEN ➔ HALF_OPEN`)** :
  - Déclenchement à **5 échecs consécutifs** sur 30 secondes.
  - Mode `OPEN` : Échec immédiat sans contacter le PSP ➔ Annulation propre de la SAGA sans surcharger le PSP défaillant.
- **Idempotence Paiement** : Index basée sur `order_id` pour prévenir tout double débit.
- **PSP Chaos Mode** : Endpoint `POST /_chaos` permettant de simuler des pannes à chaud pour les tests QA.

---

# ⚡ 6. Communication Event-Driven & Isolation

### Découplage par Événements Redis Pub/Sub

- **Flux Asynchrones** :
  - `order.ready` (Restaurants ➔ Orders : déclenche l'attribution de livreur).
  - `delivery.assigned` / `picked_up` / `completed` (Deliveries ➔ Orders & Notifications).
  - `order.confirmed` / `cancelled` (Orders ➔ Notifications).

### Principles d'Isolation des Données (ADR 0005)
- **Store exclusif par service** (Aucune table ou BDD partagée).
- **Snapshot des Prix** : Copie des tarifs au moment de la commande pour découpler l'historique des modifications de carte ultérieures.
- **Traçabilité** : Propagation systématique du `X-Correlation-Id` dans chaque log JSON structlog et événement.

---

# 💻 7. Application Fullstack & Interfaces par Rôle

### Architecture Frontend (React 18 / TypeScript / Vite / Tailwind)

- 🛒 **Vue Client** : Catalogue, recherche par filtres, gestion du panier Redis, checkout GPS, suivi de commande en direct.
- 👨‍🍳 **Espace Restaurateur (`/restaurant/dashboard`)** : Création d'établissement, gestion dynamique de la carte et avancement des tickets de cuisine (`PREPARING ➔ READY`).
- 🚴 **Espace Livreur (`/courier/dashboard`)** : Flotte géolocalisée, acceptation de courses et validation de la remise au client (`PICKED_UP ➔ DELIVERED`).
- 🧪 **Dashboard QA Testeur (`/tester`)** : Monitoring santé des 6 microservices, simulation de pannes PSP Chaos et connexion instantanée aux comptes de test.

---

# 🎬 8. Démonstration Live du Prototype

### Scénario de Démo 1 : Parcours Nominal Complet
1. *Connexion Client (Alice)* ➔ Sélection du restaurant *La Bella Napoli* ➔ Validation du panier.
2. *Passage de commande (SAGA)* ➔ Suivi en direct du statut `PREPARING`.
3. *Espace Restaurateur* ➔ Passage du repas en `READY`.
4. *Espace Livreur* ➔ Attribution automatique, prise en charge et confirmation de livraison `DELIVERED`.

### Scénario de Démo 2 : Test de Résilience (PSP Chaos)
1. *Dashboard QA Testeur* ➔ Activation du **Mode Chaos PSP (100% échec)**.
2. *Client* ➔ Tentative de commande.
3. *Constat* ➔ Ouverture du **Circuit Breaker** et annulation propre de la commande avec motif : *"Paiement refusé — aucun débit effectué"*.

---

# 📊 9. Bilan Qualité & Couverture de Tests

### Rigueur de Développement & Intégration Continue

- 🧪 **Couverture Backend Pytest** : **> 95% de couverture** sur l'ensemble des 6 microservices (plus de 310 tests automatisés passés).
- 🔍 **Analyse Statique & Typage** : Validé à 100% sans erreur avec `ruff` (linter/formatter) et `mypy` (typage strict Python).
- ⚛️ **Frontend Quality** : Validé avec `ESLint`, `Prettier` et `Vitest`.
- 🐳 **Conteneurisation Clean** : Orchestration `docker-compose` avec healthchecks sur tous les services.

---

# 🔮 10. Perspectives d'Évolution (Feuille de Route)

### Extensions & Améliorations Futures

1. **Messagerie Événementielle Avancée (Apache Kafka)** : Remplacement de Redis Pub/Sub par Kafka pour garantir la persistance des événements et la relecture de stream (Event Sourcing).
2. **CQRS / Separate Read Model** : Découplage de la base de lecture du catalogue pour optimiser les requêtes de recherche complexe (Elasticsearch).
3. **Persistance PostgreSQL & Migrations** : Migration des stores in-memory vers des bases PostgreSQL autonomes avec migrations Alembic.
4. **Hardening Sécurité** : Migration des tokens opaques vers des clés publiques/privées RS256 JWT avec validation au niveau de l'API Gateway.

---

# ❓ 11. Questions & Réponses (Q&R Jury)

### Merci pour votre attention !

- **Dépôt Git & Documentation** : Fichiers `README.md`, `architecture.md`, `diagrammes.md`, `contrats-api.md`.
- Nous sommes prêts à répondre à vos questions.
