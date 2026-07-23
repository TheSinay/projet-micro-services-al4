# 📑 LIVRABLE 1 : DOCUMENTATION D'ARCHITECTURE COMPLÈTE — FITMEAL / MIAMGO

---

## 1. Description Générale du Système

La plateforme **FitMeal / MiamGo** est une application web et mobile de livraison de repas conçue selon une **architecture microservices**. Elle orchestre les interactions entre trois catégories d'utilisateurs aux besoins distincts :
1. **Les Clients** : recherchent des établissements, parcourent les cartes, composent des paniers, effectuent le paiement sécurisé et suivent la livraison en temps réel.
2. **Les Restaurateurs** : gèrent la fiche de leur établissement, leur carte (plats, prix, options), et valident puis préparent les commandes en cuisine.
3. **Les Livreurs** : gèrent leur disponibilité, reçoivent les propositions de course géolocalisées, prennent en charge les commandes prêtes et confirment la remise au client.

L'application repose sur un ensemble de **6 microservices autonomes**, une **API Gateway Nginx** centralisée, un **bus de messages et cache Redis**, et une application **Frontend React 18 / TypeScript** proposant des interfaces dédiées par rôle ainsi qu'un **Dashboard QA Testeur**.

---

## 2. Analyse du Domaine & Découpage Microservices (DDD)

### 2.1. Identification des Bounded Contexts
En appliquant la démarche **Domain-Driven Design (DDD)**, nous avons identifié 9 bounded contexts fondamentaux :
- **Identité & Comptes** : Inscription, authentification JWT, gestion des profils et adresses.
- **Restaurants** : Informations sur les établissements et horaires d'ouverture.
- **Catalogue** : Consultation des plats, options, catégories et tarifs.
- **Commandes & Checkout** : Panier, création de la commande, calcul des coûts (sous-total + livraison).
- **Paiement** : Interaction avec le Prestataire de Services de Paiement (PSP), capture des fonds et remboursements.
- **Livraisons** : Attribution des courses, calcul de trajet et suivi d'état.
- **Livreurs** : Inscription de la flotte, position GPS et statut de disponibilité.
- **Notifications** : Alertes Push, Emails et SMS simulés.
- **Évaluations** : Notes et avis clients sur les repas et prestations.

### 2.2. Justification de la Découpe par Charge (ADR 0001 & ADR 0002)
Pour éviter un découpage excessif (nanoservices) tout en garantissant l'indépendance de déploiement et la montée en charge des composants critiques, nous avons appliqué une **découpe par profil de charge** :

1. **Isolation du Catalogue & Recherche (`service-restaurants`)** :
   - *Motif* : Le trafic de consultation des cartes est 50x à 100x supérieur au trafic de commande. Isoler ce service permet de le répliquer horizontalement ou d'y adosser un cache Redis de lecture sans impacter le processus de paiement.
2. **Isolation du Checkout & Transaction Distribuée (`service-commandes`)** :
   - *Motif* : Cœur métier à forte exigence de cohérence. Il agit en tant qu'**Orchestrateur SAGA**.
3. **Isolation du Paiement & Intégration PSP (`service-paiements`)** :
   - *Motif* : Service à haute sécurité et criticité maximale. Protégé par des mécanismes de résilience (Circuit Breaker) et d'idempotence pour prévenir tout double débit.
4. **Fusions Pragmatiques pour le Prototype (ADR 0002)** :
   - *Catalogue ➔ service-restaurants* (fusion provisoire ; extraction prévue vers `catalogue-service` si la recherche vectorielle/Elasticsearch devient nécessaire).
   - *Livreurs ➔ service-livraisons* (gestion de la flotte et des courses dans le même composant pour optimiser les requêtes spatiales).
   - *Évaluations ➔ service-commandes* (faible volume, directement rattaché au cycle de vie de la commande livrée).

---

## 3. Inventaire des Microservices

| Service | Bounded Context(s) | Responsabilités Principales | Modèle de Données (Agrégats) | Port Interne |
|---|---|---|---|---|
| **`gateway` (Nginx)** | Edge / Infrastructure | Routage `/api/v1/*`, gestion des en-têtes CORS, propagation du `X-Correlation-Id`. | Aucun (Stateless) | 80 / 8080 |
| **`users`** | Identité & Comptes | Inscription, Login JWT, gestion des adresses et Rôle (RBAC : `client`, `restaurant_owner`, `courier`). | `User`, `Address` | 8001 |
| **`restaurants`** | Restaurants + Catalogue | Fiche établissement, cartes (plats, prix), validation de commande et tickets de cuisine (`PREPARING -> READY`). | `Restaurant`, `MenuItem`, `KitchenTicket` | 8002 |
| **`orders`** | Commandes + Checkout + Évaluations | Panier Redis, Orchestrateur SAGA, calcul de tarification (sous-total + livraison GPS), évaluations. | `Cart`, `Order`, `Evaluation` | 8003 |
| **`payments`** | Paiement | Encaissement via PSP simulé, garantie d'idempotence par `order_id`, remboursements SAGA, PSP Chaos Mode. | `Payment`, `Refund` | 8004 |
| **`deliveries`** | Livraisons + Livreurs | Inscription flotte, disponibilité, geofencing (livreur le plus proche), cycle de livraison (`ASSIGNED -> PICKED_UP -> DELIVERED`). | `Courier`, `Delivery` | 8005 |
| **`notifications`** | Notifications | Consommation des événements Redis Pub/Sub, envoi simulé (Email, Push, SMS) et historique. | `Notification` | 8006 |

---

## 4. Transaction Distribuée : Pattern SAGA Orchestré (ADR 0003)

Ne pouvant recourir à une transaction ACID distribuée (qui créerait un couplage fort et des verrous bloquants inter-services), nous avons implémenté un **Pattern SAGA à Orchestration Hybride** :

### 4.1. SAGA Phase Critique (Orchestrée Synchroniquement)
Le service `orders` orchestre le processus de paiement et de validation en direct :
1. **Création Commande** : Commande enregistrée en statut `RECEIVED` avec son `saga_state = VALIDATING`.
2. **Validation Restaurant** : Appel synchrone `POST /order-validations`. Si refusé ➔ Annulation immédiate sans débit (`saga_state = CANCELLED_VALIDATION`).
3. **Paiement Sécurisé (Circuit Breaker)** : Appel synchrone `POST /payments` protégé par Retry/Circuit Breaker. Si échec ➔ Annulation sans débit (`saga_state = CANCELLED_PAYMENT`).
4. **Ticket Cuisine** : Appel synchrone `POST /kitchen-tickets`. 
   - Si **Accepté** ➔ Commande confirmée (`PREPARING`, `saga_state = CONFIRMED`) + Événement `order.confirmed`.
   - Si **Refusé (409)** ➔ **Compensation Automatique** : Émission d'un remboursement immédiat auprès du PSP (`POST /payments/{id}/refunds`), passage en statut `CANCELLED` avec motif explicite (`saga_state = CANCELLED_REFUSED`).

### 4.2. SAGA Phase Aval (Chorégraphiée par Événements)
1. Le restaurant passe le repas en `READY` ➔ Événement `order.ready` publié sur Redis Pub/Sub.
2. Le service `orders` consomme l'événement et demande une livraison au service `deliveries`.
3. Le service `deliveries` trouve le livreur le plus proche ➔ Événement `delivery.assigned`.
4. Le livreur valide la livraison au client ➔ Événement `delivery.completed`.
5. Le service `orders` met à jour la commande en `DELIVERED` et émet `order.delivered`.

---

## 5. Patterns de Résilience & Fault Tolerance (ADR 0007)

Les appels sortants de l'orchestrateur SAGA vers le service de paiement sont protégés par un **composant de résilience sur mesure** (`resilience.py`) :

1. **Timeout Policy** : Chaque appel HTTP sortant est limité à 2,0 secondes pour éviter le blocage des threads de l'API.
2. **Retry Policy avec Backoff Exponentiel & Jitter** : En cas d'erreur réseau temporaire (502, 503, timeout), l'appel est retenté jusqu'à 3 fois avec des délais progressifs (0.1s, 0.2s, 0.4s + bruit aléatoire). Les erreurs 4xx ne sont jamais retentées.
3. **Circuit Breaker (`CLOSED -> OPEN -> HALF_OPEN`)** :
   - *Seuil de déclenchement* : 5 échecs consécutifs sur une fenêtre de 30 secondes.
   - *Mode OPEN* : Le circuit s'ouvre. Tout nouvel appel échoue immédiatement sans contacter le PSP, permettant d'annuler la commande proprement sans surcharger le PSP défaillant.
   - *Mode HALF_OPEN* : Après un délai de récupération de 15 secondes, un appel de test est autorisé pour vérifier le rétablissement du PSP.
4. **Garantie d'Idempotence** : Le service `payments` utilise `order_id` comme clé d'idempotence. Un retry ayant réussi amont ne crédite jamais deux fois le PSP.

---

## 6. Communication Inter-Services & Traçabilité

- **Communication Synchrones (REST / HTTP Async avec `httpx`)** : Utilisée exclusivement pour les étapes bloquantes de la SAGA nécessitant un verdict immédiat (Validation, Paiement, Kitchen Ticket).
- **Communication Asynchrone (Redis Pub/Sub)** : Utilisée pour le découplage des événements métriques et informatifs (`order.confirmed`, `order.ready`, `delivery.assigned`, `delivery.completed`).
- **Traçabilité & Correlation ID** : Chaque requête entrante sur l'API Gateway reçoit un en-tête `X-Correlation-Id` unique (UUIDv4). Cet en-tête est propagé dans tous les appels HTTP inter-services et injecté dans chaque événement Redis et chaque log structuré JSON (structlog).

---

## 7. Isolation des Données & Gestion des Caches (ADR 0005)

- **Aucune Base de Données Partagée** : Chaque microservice possède son propre magasin de données exclusif. Aucun service n'accède directement à la table ou au store d'un autre service.
- **Snapshot des Prix (Découplage Catalogue/Commande)** : Lors du checkout, `Order.items` enregistre un instantané (snapshot) des noms et prix unitaires des plats. Toute modification ultérieure de la carte par le restaurateur n'altère pas l'historique de la commande.
- **Cache & État Transitoire (Redis)** :
  - Les paniers utilisateurs sont conservés dans Redis sous la clé `cart:{user_id}`.
  - L'avancement des transactions SAGA est tracé en temps réel dans Redis (`saga_state`).
