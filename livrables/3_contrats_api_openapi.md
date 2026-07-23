# 📜 LIVRABLE 3 : SPÉCIFICATIONS & CONTRATS D'API REST — FITMEAL / MIAMGO

---

## 1. Normalisation & Standards Inter-Services

Toutes les API exposées par les microservices respectent les standards RESTful modernes et la norme **OpenAPI 3.0**.

### 1.1. Format des Réponses d'Erreurs (RFC 7807)
En cas d'erreur métier ou de validation, tous les services retournent un objet JSON unifié :

```json
{
  "detail": "Description textuelle explicite de l'erreur ou de la contrainte violée"
}
```

### 1.2. Codes de Statut HTTP Utilisés
- **`200 OK`** : Succès de la lecture ou mise à jour.
- **`201 Created`** : Création réussie d'une ressource (Commande, Utilisateur, Ticket, Paiement).
- **`204 No Content`** : Suppression effectuée ou requête OPTIONS CORS traitée.
- **`400 Bad Request`** : Données d'entrée invalides.
- **`401 Unauthorized`** : Token JWT manquant ou invalide.
- **`403 Forbidden`** : Accès refusé pour le rôle attribué.
- **`404 Not Found`** : Ressource non trouvée.
- **`409 Conflict`** : Conflit métier (ex: cuisine refusant la commande).
- **`422 Unprocessable Entity`** : Validation Pydantic échouée.
- **`502 / 503`** : Service tiers défaillant (ex: PSP en panne).

### 1.3. En-têtes HTTP Obligatoires & Propagation
- `Content-Type: application/json`
- `Authorization: Bearer <jwt_token>` (pour les routes protégées)
- `X-Correlation-Id: <uuid_v4>` (propagé à travers la Gateway et tous les microservices).

---

## 2. Contrats d'API par Microservice

### 2.1. `service-utilisateurs` (Port 8001)

#### Inscription
- **Route** : `POST /api/v1/auth/register`
- **Request Body** :
  ```json
  {
    "name": "Alice Martin",
    "email": "alice@example.com",
    "password": "Password123!",
    "phone": "+33612345678",
    "role": "client"
  }
  ```
- **Response 201 Created** :
  ```json
  {
    "id": "usr_alice",
    "name": "Alice Martin",
    "email": "alice@example.com",
    "role": "client"
  }
  ```

#### Connexion JWT
- **Route** : `POST /api/v1/auth/login`
- **Request Body** : `{"email": "alice@example.com", "password": "Password123!"}`
- **Response 200 OK** :
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "token_type": "bearer",
    "user": {
      "id": "usr_alice",
      "name": "Alice Martin",
      "role": "client"
    }
  }
  ```

#### Adresses de Livraison
- **`GET /api/v1/users/addresses`** : Restitue la liste des adresses du client.
- **`POST /api/v1/users/addresses`** :
  - **Request Body** :
    ```json
    {
      "label": "Domicile",
      "street": "15 rue de la Roquette",
      "city": "Paris",
      "lat": 48.8550,
      "lng": 2.3720
    }
    ```
  - **Response 201 Created** : Objet `Address` enrichi d'un ID.

---

### 2.2. `service-restaurants` (Port 8002)

#### Catalogue & Recherche
- **`GET /api/v1/restaurants`** : Recherche multi-critères (`?q=pizza&cuisine_type=italian&lat=48.85&lng=2.35`).
  - **Response 200 OK** : `Array<Restaurant>`
- **`GET /api/v1/restaurants/{id}`** : Détail d'un restaurant avec sa carte complète.
  - **Response 200 OK** :
    ```json
    {
      "id": "resto-bella-napoli",
      "name": "La Bella Napoli",
      "cuisine_type": "italian",
      "address": "12 rue de la Paix, Paris",
      "lat": 48.8566,
      "lng": 2.3522,
      "menu": [
        {
          "id": "dish-margherita",
          "name": "Pizza Margherita",
          "description": "Sauce tomate San Marzano, mozzarella fior di latte, basilic frais",
          "price": 12.50,
          "available": true
        }
      ]
    }
    ```

#### SAGA Validations & Kitchen Tickets
- **`POST /api/v1/restaurants/{id}/order-validations`** (SAGA Étape 2) :
  - **Request Body** :
    ```json
    {
      "items": [
        {"menu_item_id": "dish-margherita", "unit_price": 12.50, "quantity": 2}
      ]
    }
    ```
  - **Response 200 OK** : `{"valid": true, "subtotal": 25.00, "reasons": []}`
- **`POST /api/v1/restaurants/{id}/kitchen-tickets`** (SAGA Étape 4) :
  - **Request Body** :
    ```json
    {
      "order_id": "ord_999",
      "items": [{"menu_item_id": "dish-margherita", "quantity": 2}]
    }
    ```
  - **Response 201 Created** : Ticket accepté.
  - **Response 409 Conflict** : Cuisine saturée (Déclenche la compensation SAGA).
- **`PATCH /api/v1/kitchen-tickets/{ticket_id}`** :
  - **Request Body** : `{"status": "PREPARING" | "READY"}`

---

### 2.3. `service-commandes` (Port 8003)

#### Panier Redis
- **`GET /api/v1/carts/{user_id}`** : Récupère le panier courant.
- **`POST /api/v1/carts/{user_id}/items`** : Ajoute un plat au panier.
  - **Request Body** : `{"menu_item_id": "dish-margherita", "name": "Pizza Margherita", "unit_price": 12.50, "quantity": 1, "restaurant_id": "resto-bella-napoli"}`
- **`DELETE /api/v1/carts/{user_id}`** : Vide le panier.

#### Checkout & SAGA
- **`POST /api/v1/orders`** : Déclenche la création de commande et la SAGA.
  - **Request Body** :
    ```json
    {
      "user_id": "usr_alice",
      "delivery_address": {
        "label": "Domicile",
        "street": "15 rue de la Roquette",
        "city": "Paris",
        "lat": 48.8550,
        "lng": 2.3720
      }
    }
    ```
  - **Response 201 Created** :
    ```json
    {
      "id": "ord_888",
      "user_id": "usr_alice",
      "restaurant_id": "resto-bella-napoli",
      "status": "PREPARING",
      "saga_state": "CONFIRMED",
      "subtotal": 12.50,
      "delivery_fee": 3.00,
      "total": 15.50,
      "payment_id": "pay_777",
      "created_at": "2026-07-23T15:00:00Z"
    }
    ```
- **`GET /api/v1/orders/{id}`** : Restitue la commande et son état de suivi.

---

### 2.4. `service-paiements` (Port 8004)

#### Paiement Idempotent
- **`POST /api/v1/payments`** (SAGA Étape 3) :
  - **Request Body** : `{"order_id": "ord_888", "amount": 15.50}`
  - **Response 201 Created / 200 OK** : `{"id": "pay_777", "order_id": "ord_888", "amount": 15.50, "status": "CAPTURED"}`
  - **Response 502 / 503** : Panne PSP (intercepté par Circuit Breaker).

#### Remboursement Compensatoire SAGA
- **`POST /api/v1/payments/{payment_id}/refunds`** :
  - **Request Body** : `{"amount": 15.50, "reason": "Annulation cuisine"}`
  - **Response 201 Created** : `{"id": "ref_111", "payment_id": "pay_777", "amount": 15.50, "status": "REFUNDED"}`

#### Controller Chaos PSP (QA)
- **`POST /api/v1/_chaos`** : Injection de panne PSP à chaud.
  - **Request Body** : `{"failure_rate": 0.0 | 1.0}`

---

### 2.5. `service-livraisons` (Port 8005)

#### Attribution & Gestion Course
- **`POST /api/v1/deliveries`** : Demande d'attribution de livreur.
  - **Request Body** :
    ```json
    {
      "order_id": "ord_888",
      "pickup": {"lat": 48.8566, "lng": 2.3522},
      "dropoff": {"lat": 48.8550, "lng": 2.3720}
    }
    ```
  - **Response 201 Created** : `{"id": "del_555", "order_id": "ord_888", "courier_id": "usr_bob", "status": "ASSIGNED"}`
- **`PATCH /api/v1/deliveries/{id}`** : Mise à jour par le livreur (`ASSIGNED -> PICKED_UP -> DELIVERED`).

---

### 2.6. `service-notifications` (Port 8006)

- **`GET /api/v1/notifications`** : Consultation de l'historique des alertes (`?user_id=usr_alice`).
  - **Response 200 OK** : `Array<Notification>` (Canaux PUSH, EMAIL, SMS).
