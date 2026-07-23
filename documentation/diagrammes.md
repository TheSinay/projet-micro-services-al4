# Diagrammes d'Architecture et de Séquence — FitMeal / MiamGo

Ce document regroupe l'ensemble des diagrammes techniques formalisant l'architecture microservices de la plateforme de livraison de repas.

---

## 1. Diagramme de Contexte Système (C4 — Niveau 1)

Ce diagramme illustre le système dans son environnement avec ses différents utilisateurs (Clients, Restaurateurs, Livreurs) et le prestataire de paiement externe (PSP).

```mermaid
flowchart TB
    client["👤 Client<br>(Parcourt le catalogue, commande, paie, suit sa commande)"]
    resto["👨‍🍳 Restaurateur<br>(Gère son restaurant, ses plats et valide la préparation)"]
    livreur["🚴 Livreur<br>(Consulte les courses, accepte et confirme la livraison)"]

    subgraph systeme ["Plateforme Microservices MiamGo / FitMeal"]
        plateforme["Système Central Microservices<br>(API Gateway, Catalogue, Commandes, SAGA, Paiements, Livraisons, Notifications)"]
    end

    psp["💳 PSP Externe (Simulé)<br>(Service de Paiement Sécurisé, Flaky / Instable)"]

    client -->|"Recherche, Panier, Commande, Suivi & Évaluation"| plateforme
    resto -->|"Gestion Carte, Validation & Fin Préparation"| plateforme
    livreur -->|"Gestion Disponibilité, Prise en charge & Remise"| plateforme
    plateforme -->|"Autorisation, Capture & Remboursements SAGA"| psp
    plateforme -.->|"Notifications Push / Email / SMS"| client
    plateforme -.->|"Alertes nouvelles commandes"| resto
    plateforme -.->|"Propositions de livraison"| livreur

    classDef acteur fill:#08427b,stroke:#052e56,color:#ffffff
    classDef sys fill:#1168bd,stroke:#0b4884,color:#ffffff
    classDef externe fill:#999999,stroke:#6b6b6b,color:#ffffff
    class client,resto,livreur acteur
    class plateforme sys
    class psp externe
```

---

## 2. Diagramme de Conteneurs (C4 — Niveau 2)

Ce diagramme détaille les 6 microservices FastAPI, l'API Gateway Nginx, le bus de messages Redis et leurs magasins de données autonomes.

```mermaid
flowchart TB
    acteurs["Acteurs & Client Web<br>(Frontend React / TypeScript & Dashboard QA)"]

    subgraph plateforme ["Infrastructure Conteneurisée (docker-compose)"]
        gw["🌐 API Gateway — Nginx (:80 / :8080)<br>Routage /api/v1/*, CORS, X-Correlation-Id"]

        subgraph services ["Microservices FastAPI (Python 3.13)"]
            users["👤 service-utilisateurs (:8001)<br>Auth, Profils, Adresses, RBAC"]
            restaurants["👨‍🍳 service-restaurants (:8002)<br>Catalogue, Menus, Validations, Kitchen Tickets"]
            orders["📦 service-commandes (:8003)<br>Panier, SAGA Orchestrateur, Prix, Évaluations"]
            payments["💳 service-paiements (:8004)<br>Charges, Idempotence, Remboursements, Chaos Mode"]
            deliveries["🚴 service-livraisons (:8005)<br>Flotte livreurs, Geofencing, Attribution, Tracking"]
            notifications["🔔 service-notifications (:8006)<br>Consommateur Événements, Envois simulés"]
        end

        redis[("⚡ Bus Redis Pub/Sub & Caches<br>Événements asynchrones + Paniers & SAGA State")]

        subgraph stores ["Bases de données isolées (Store par service)"]
            db_u[("DB Users")]
            db_r[("DB Restaurants")]
            db_o[("DB Orders")]
            db_p[("DB Payments")]
            db_d[("DB Deliveries")]
            db_n[("DB Notifications")]
        end
    end

    psp["💳 PSP Externe Simulé<br>(Modes Flaky / Failure Rate)"]

    acteurs -->|"REST / HTTP / JSON"| gw
    gw --> users
    gw --> restaurants
    gw --> orders
    gw --> payments
    gw --> deliveries
    gw --> notifications

    orders -->|"1. Validation Commande<br>3. Kitchen Ticket"| restaurants
    orders -->|"2. Charge & Remboursement<br>(Circuit Breaker + Retry)"| payments
    orders -->|"4. Demande Livraison"| deliveries
    payments -->|"Autorisation & Capture"| psp

    orders -.->|"Événements order.confirmed / cancelled"| redis
    restaurants -.->|"Événement order.ready"| redis
    deliveries -.->|"Événements delivery.assigned / completed"| redis
    redis -.->|"Abonnement événements"| orders
    redis -.->|"Abonnement événements"| notifications

    users --- db_u
    restaurants --- db_r
    orders --- db_o
    payments --- db_p
    deliveries --- db_d
    notifications --- db_n

    classDef svc fill:#1168bd,stroke:#0b4884,color:#ffffff
    classDef edge fill:#438dd5,stroke:#2e6295,color:#ffffff
    classDef infra fill:#b45309,stroke:#7c3a06,color:#ffffff
    classDef store fill:#707070,stroke:#4a4a4a,color:#ffffff
    classDef ext fill:#999999,stroke:#6b6b6b,color:#ffffff
    class users,restaurants,orders,payments,deliveries,notifications svc
    class gw edge
    class redis infra
    class db_u,db_r,db_o,db_p,db_d,db_n store
    class acteurs,psp ext
```

---

## 3. Diagrammes de Séquence

### 3.1. SAGA de Passage de Commande Nominale (Orchestration Hybride)

Illustre le déroulement réussi du checkout depuis la validation du panier jusqu'à la préparation en cuisine et la livraison.

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant Frontend as Frontend React
    participant Gateway as API Gateway Nginx
    participant Orders as service-commandes (SAGA)
    participant Resto as service-restaurants
    participant Payments as service-paiements
    participant PSP as PSP Gateway
    participant Bus as Redis Pub/Sub
    participant Notif as service-notifications

    Client->>Frontend: Valide le panier (Checkout)
    Frontend->>Gateway: POST /api/v1/orders
    Gateway->>Orders: POST /api/v1/orders

    Note over Orders: SAGA Étape 1 : Création Commande (Status: RECEIVED)

    Note over Orders,Resto: SAGA Étape 2 : Validation Restaurant
    Orders->>Resto: POST /api/v1/restaurants/{id}/order-validations
    Resto-->>Orders: 200 OK (valid=true, subtotal)

    Note over Orders,Payments: SAGA Étape 3 : Paiement Sécurisé (Circuit Breaker)
    Orders->>Payments: POST /api/v1/payments (order_id, total)
    Payments->>PSP: Charge client
    PSP-->>Payments: Capture OK (payment_id)
    Payments-->>Orders: 201 Created (payment_id)

    Note over Orders,Resto: SAGA Étape 4 : Ticket Cuisine
    Orders->>Resto: POST /api/v1/restaurants/{id}/kitchen-tickets
    Resto-->>Orders: 201 Created (accepted=true)

    Note over Orders: SAGA Étape 5 : Confirmation Commande (Status: PREPARING)
    Orders->>Bus: Publish "order.confirmed"
    Bus-.->Notif: Event "order.confirmed"
    Notif-->>Client: Email/Push Notification "Commande Confirmée"

    Orders-->>Gateway: 201 Created (Order detail)
    Gateway-->>Frontend: 201 Created (Order detail)
    Frontend-->>Client: Redirection vers Suivi de Commande en direct
```

---

### 3.2. SAGA & Pattern de Résilience (Échec Paiement / Circuit Breaker OPEN)

Illustre la résilience de l'orchestrateur lors d'une panne du PSP : retries avec backoff exponentiel, ouverture du Circuit Breaker, et annulation propre sans débit client.

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant Orders as service-commandes (SAGA)
    participant Payments as service-paiements
    participant Breaker as Circuit Breaker
    participant PSP as PSP Gateway (Down)
    participant Bus as Redis Pub/Sub

    Note over Orders: Commande créée en statut RECEIVED
    Orders->>Breaker: Exécuter paiement (Essai 1)
    Breaker->>Payments: POST /api/v1/payments
    Payments->>PSP: Charge client
    PSP--xPayments: 503 Service Unavailable / Timeout
    Payments--xBreaker: 502 Bad Gateway

    Note over Breaker: Backoff exponentiel (0.1s, 0.2s...)
    Orders->>Breaker: Exécuter paiement (Essai 2 & 3)
    Breaker--xOrders: Max retries atteints / CircuitOpenError (Circuit Breaker OPEN)

    Note over Orders: Annulation SAGA sans compensation financière (aucun débit)
    Orders->>Orders: Set Status = CANCELLED (saga_state: CANCELLED_PAYMENT)
    Orders->>Bus: Publish "order.cancelled" (Reason: PSP Indisponible)
    Bus-.->Client: Notification "Commande annulée — Aucun débit effectué"
```

---

### 3.3. SAGA Compensation (Refus Cuisine après Paiement Capturé)

Illustre la transaction compensatoire : le paiement ayant été capturé, un refus du restaurant déclenche un remboursement intégral automatique auprès du PSP.

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant Orders as service-commandes (SAGA)
    participant Payments as service-paiements
    participant Resto as service-restaurants
    participant PSP as PSP Gateway
    participant Bus as Redis Pub/Sub

    Note over Orders: 1. Validation OK & Paiement Capturé (payment_id = pay_123)
    Orders->>Resto: POST /api/v1/restaurants/{id}/kitchen-tickets
    Resto-->>Orders: 409 Conflict (Cuisine saturée / Produit indisponible)

    Note over Orders,Payments: TRANSACTION COMPENSATOIRE (SAGA)
    Orders->>Orders: Set saga_state = COMPENSATING
    Orders->>Payments: POST /api/v1/payments/pay_123/refunds (amount: total)
    Payments->>PSP: Remboursement intégral
    PSP-->>Payments: Refund OK (refund_id)
    Payments-->>Orders: 201 Created (Refund confirmed)

    Orders->>Orders: Set Status = CANCELLED (saga_state: CANCELLED_REFUSED)
    Orders->>Bus: Publish "order.cancelled" (Reason: Refus cuisine, remboursé)
    Bus-.->Client: Notification "Commande annulée par le restaurant — Remboursement intégral effectué"
```

---

### 3.4. Continuation de Livraison (Chorégraphie Événementielle)

Illustre l'étape asynchrone post-préparation : notification cuisine prête, attribution automatique du livreur le plus proche, suivi des statuts et confirmation de livraison.

```mermaid
sequenceDiagram
    autonumber
    actor Resto as Restaurateur
    actor Livreur as Livreur
    actor Client as Client
    participant RestoDashboard as Espace Restaurateur
    participant RestoService as service-restaurants
    participant Bus as Redis Pub/Sub
    participant Orders as service-commandes
    participant Deliveries as service-livraisons
    participant CourierDashboard as Espace Livreur

    Resto->>RestoDashboard: Marque repas "Prêt en Cuisine"
    RestoDashboard->>RestoService: PATCH /api/v1/kitchen-tickets/{id} (status: READY)
    RestoService->>Bus: Publish "order.ready"

    Bus-.->Orders: Consomme "order.ready"
    Note over Orders: Déclenche recherche livreur
    Orders->>Deliveries: POST /api/v1/deliveries (order_id, pickup, dropoff)
    Deliveries->>Deliveries: Recherche livreur le plus proche (Geofencing)
    Deliveries-->>Orders: 201 Created (delivery_id, courier_id)
    Orders->>Orders: Set Status = DELIVERING (saga_state: DELIVERING)

    Deliveries->>Bus: Publish "delivery.assigned"
    Bus-.->CourierDashboard: Notification nouvelle course assignée

    Livreur->>CourierDashboard: Confirme la prise en charge (Prise du repas)
    CourierDashboard->>Deliveries: PATCH /api/v1/deliveries/{id} (status: PICKED_UP)
    Deliveries->>Bus: Publish "delivery.picked_up"

    Livreur->>CourierDashboard: Valide la remises au client
    CourierDashboard->>Deliveries: PATCH /api/v1/deliveries/{id} (status: DELIVERED)
    Deliveries->>Bus: Publish "delivery.completed"

    Bus-.->Orders: Consomme "delivery.completed"
    Orders->>Orders: Set Status = DELIVERED (saga_state: DELIVERED)
    Orders->>Bus: Publish "order.delivered"
    Bus-.->Client: Notification "Votre commande est livrée ! Bon appétit"
```

---

## 4. Modèle de Données & Relations Inter-Services

Ce diagramme Entité-Association récapitule les modèles de données autonomes de chaque microservice et les liens logiques (clés d'agrégat).

```mermaid
erDiagram
    %% Service Users
    USER {
        string id PK
        string email
        string name
        string role
        string phone
    }
    ADDRESS {
        string id PK
        string user_id FK
        string label
        string street
        string city
        float lat
        float lng
    }
    USER ||--o{ ADDRESS : "possède"

    %% Service Restaurants
    RESTAURANT {
        string id PK
        string name
        string cuisine_type
        string address
        float lat
        float lng
        boolean auto_accept
        string owner_id FK
    }
    MENU_ITEM {
        string id PK
        string restaurant_id FK
        string name
        string description
        float price
        boolean available
    }
    KITCHEN_TICKET {
        string id PK
        string order_id FK
        string restaurant_id FK
        string status
    }
    RESTAURANT ||--o{ MENU_ITEM : "propose"
    RESTAURANT ||--o{ KITCHEN_TICKET : "traite"

    %% Service Orders
    CART {
        string user_id PK
        json items
    }
    ORDER {
        string id PK
        string user_id FK
        string restaurant_id FK
        string status
        string saga_state
        float subtotal
        float delivery_fee
        float total
        string payment_id FK
        string delivery_id FK
        string cancellation_reason
    }
    EVALUATION {
        string id PK
        string order_id FK
        string user_id FK
        string restaurant_id FK
        int rating
        string comment
    }
    ORDER ||--o{ EVALUATION : "génère"

    %% Service Payments
    PAYMENT {
        string id PK
        string order_id FK
        float amount
        string status
        string psp_transaction_id
    }
    REFUND {
        string id PK
        string payment_id FK
        float amount
        string reason
    }
    PAYMENT ||--o{ REFUND : "contient"

    %% Service Deliveries
    COURIER {
        string id PK
        string name
        string phone
        boolean available
        float lat
        float lng
    }
    DELIVERY {
        string id PK
        string order_id FK
        string courier_id FK
        string status
        string pickup_address
        string delivery_address
    }
    COURIER ||--o{ DELIVERY : "effectue"

    %% Service Notifications
    NOTIFICATION {
        string id PK
        string user_id FK
        string channel
        string type
        string message
    }
```
