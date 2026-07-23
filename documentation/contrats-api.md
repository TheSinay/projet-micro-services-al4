# Spécifications et Contrats d'API REST (OpenAPI 3.0) — FitMeal / MiamGo

Ce document formalise les contrats d'API exposés par les **6 microservices** de la plateforme. Chaque service génère dynamiquement sa documentation OpenAPI/Swagger accessible sur sa route `/docs`.

---

## 1. Conventions Générales

### 1.1. Modèle de Réponses HTTP et Erreurs Normalisées
Toutes les réponses d'erreur respectent le format JSON standard FastAPI / RFC 7807 :

```json
{
  "detail": "Description compréhensible de l'erreur métier ou de la contrainte violée"
}
```

- **HTTP 200 / 201** : Succès de la requête.
- **HTTP 400 Bad Request** : Paramètre invalide ou corps de requête malformé.
- **HTTP 401 Unauthorized** : Token JWT absent ou expiré.
- **HTTP 403 Forbidden** : Privilèges insuffisants pour le rôle de l'utilisateur.
- **HTTP 404 Not Found** : Ressource non trouvée.
- **HTTP 409 Conflict** : Conflit métier (ex: cuisine saturée, pas de livreur disponible).
- **HTTP 422 Unprocessable Entity** : Échec de validation Pydantic (champs requis manquants/invalides).
- **HTTP 502 / 503** : Erreur amont ou service tiers indisponible (ex: PSP en panne).

### 1.2. En-têtes HTTP Requis & Propagation
- `Content-Type: application/json`
- `Authorization: Bearer <jwt_token>` (pour les routes protégées)
- `X-Correlation-Id: <uuid>` (propagé entre tous les microservices et dans les logs structlog).

---

## 2. Service Utilisateurs (`service-utilisateurs` — Port 8001)

### 2.1. Authentification
- `POST /api/v1/auth/register` : Inscription d'un nouvel utilisateur.
  - **Body** : `{"name": "str", "email": "str", "password": "str", "phone": "str", "role": "client | restaurant_owner | courier"}`
  - **Réponse 201** : `{"id": "usr_123", "name": "str", "email": "str", "role": "str"}`
- `POST /api/v1/auth/login` : Connexion et génération du token JWT.
  - **Body** : `{"email": "str", "password": "str"}`
  - **Réponse 200** : `{"access_token": "jwt_str", "token_type": "bearer", "user": {"id": "str", "name": "str", "role": "str"}}`

### 2.2. Profil & Adresses Client
- `GET /api/v1/users/me` : Récupère le profil de l'utilisateur connecté.
- `GET /api/v1/users/addresses` : Liste les adresses de livraison enregistrées.
- `POST /api/v1/users/addresses` : Ajoute une nouvelle adresse de livraison.
  - **Body** : `{"label": "Domicile", "street": "15 rue de Paris", "city": "Paris", "lat": 48.8566, "lng": 2.3522}`
  - **Réponse 201** : `Address` object avec ID attribué.

---

## 3. Service Restaurants (`service-restaurants` — Port 8002)

### 3.1. Consultation & Recherche (Catalogue)
- `GET /api/v1/restaurants` : Recherche multi-critères des restaurants.
  - **Query Params** : `q` (nom/plat), `cuisine_type`, `lat`, `lng`, `radius_km`.
  - **Réponse 200** : `Array<Restaurant>`
- `GET /api/v1/restaurants/{id}` : Fiche détaillée d'un restaurant avec son menu.
  - **Réponse 200** : `{"id": "str", "name": "str", "cuisine_type": "str", "address": "str", "menu": Array<MenuItem>}`

### 3.2. Management Restaurateur & Menu
- `POST /api/v1/restaurants` : Création d'un établissement rattaché au compte restaurateur.
- `POST /api/v1/restaurants/{id}/menu-items` : Ajout d'un plat au menu.
- `PUT /api/v1/restaurants/{id}/menu-items/{item_id}` : Modification d'un plat (prix, dispo).
- `DELETE /api/v1/restaurants/{id}/menu-items/{item_id}` : Suppression d'un plat.

### 3.3. SAGA & Tickets Cuisine
- `POST /api/v1/restaurants/{id}/order-validations` (SAGA Étape 2) : Validation synchrone des articles et calcul du sous-total.
  - **Body** : `{"items": [{"menu_item_id": "str", "unit_price": 12.5, "quantity": 2}]}`
  - **Réponse 200** : `{"valid": true, "subtotal": 25.0, "reasons": []}`
- `POST /api/v1/restaurants/{id}/kitchen-tickets` (SAGA Étape 4) : Demande d'acceptation par la cuisine.
  - **Réponse 201** : Ticket créé et accepté.
  - **Réponse 409** : Cuisine saturée (Déclenche la compensation SAGA remboursement).
- `PATCH /api/v1/kitchen-tickets/{ticket_id}` : Mise à jour de l'état de préparation (`PREPARING -> READY`).

---

## 4. Service Commandes (`service-commandes` — Port 8003)

### 4.1. Gestion du Panier (Redis)
- `GET /api/v1/carts/{user_id}` : Obtenir le panier courant de l'utilisateur.
- `POST /api/v1/carts/{user_id}/items` : Ajouter un article au panier.
- `DELETE /api/v1/carts/{user_id}/items/{menu_item_id}` : Supprimer un article.
- `DELETE /api/v1/carts/{user_id}` : Vider le panier.

### 4.2. Passage de Commande & SAGA
- `POST /api/v1/orders` : Déclencher le checkout et lancer la SAGA d'orchestration.
  - **Body** : `{"user_id": "str", "delivery_address": {"label": "Maison", "street": "...", "city": "...", "lat": 48.85, "lng": 2.37}}`
  - **Réponse 201** : `Order` object avec statut initial (`RECEIVED` -> `PREPARING` si succès, ou `CANCELLED` avec `cancellation_reason` en cas d'échec/compensation).
- `GET /api/v1/orders` : Historique des commandes d'un utilisateur (`?user_id=...`).
- `GET /api/v1/orders/{id}` : Suivi en temps réel de l'état de la commande et du `saga_state`.

### 4.3. Évaluations
- `POST /api/v1/orders/{id}/evaluations` : Évaluation du restaurant après livraison (`rating` 1 à 5, `comment`).

---

## 5. Service Paiements (`service-paiements` — Port 8004)

### 5.1. Encaissement & Remboursements
- `POST /api/v1/payments` (SAGA Étape 3) : Idempotent par `order_id`. Capture les fonds via le PSP simulé.
  - **Body** : `{"order_id": "str", "amount": 28.50}`
  - **Réponse 201 / 200** : `{"id": "pay_123", "order_id": "str", "amount": 28.50, "status": "CAPTURED"}`
  - **Réponse 502 / 503** : Échec PSP (Intercepté par le Circuit Breaker `orders`).
- `POST /api/v1/payments/{payment_id}/refunds` (SAGA Compensation) : Remboursement partiel ou total.
  - **Body** : `{"amount": 28.50, "reason": "Annulation cuisine"}`
  - **Réponse 201** : `{"id": "ref_999", "payment_id": "pay_123", "amount": 28.50, "status": "REFUNDED"}`

### 5.2. Test de Résilience (PSP Chaos)
- `POST /api/v1/_chaos` : Endpoint d'injection de pannes à chaud pour les tests QA.
  - **Body** : `{"failure_rate": 0.0 | 1.0}`
  - **Réponse 200** : `{"failure_rate": 1.0}`

---

## 6. Service Livraisons (`service-livraisons` — Port 8005)

### 6.1. Flotte & Profils Livreurs
- `GET /api/v1/couriers` : Liste des livreurs et leurs positions GPS.
- `POST /api/v1/couriers` : Inscription d'un profil livreur.
  - **Body** : `{"name": "Bob", "phone": "+33711223344", "lat": 48.8566, "lng": 2.3522, "available": true}`

### 6.2. Course & Suivi de Livraison
- `POST /api/v1/deliveries` : Assignation d'un livreur disponible le plus proche pour une commande prête.
  - **Body** : `{"order_id": "str", "pickup": {"lat": 48.85, "lng": 2.35}, "dropoff": {"lat": 48.86, "lng": 2.36}}`
  - **Réponse 201** : `Delivery` object (Status: `ASSIGNED`, `courier_id`: "usr_bob").
  - **Réponse 409** : Aucun livreur disponible dans le rayon (Déclenche retry/compensation).
- `GET /api/v1/deliveries` : Obtenir la livraison liée à une commande (`?order_id=...`).
- `PATCH /api/v1/deliveries/{id}` : Mise à jour du statut par le livreur (`ASSIGNED -> PICKED_UP -> DELIVERED`).

---

## 7. Service Notifications (`service-notifications` — Port 8006)

### 7.1. Consommation & Consultation
- `GET /api/v1/notifications` : Historique des notifications envoyées (`?user_id=...`).
  - **Réponse 200** : `Array<Notification>` (Canaux: EMAIL, PUSH, SMS).
