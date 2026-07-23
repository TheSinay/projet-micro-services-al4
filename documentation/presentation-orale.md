# Support de Présentation Orale & Guide de Soutenance — FitMeal / MiamGo

**Durée totale** : 15 minutes maximum  
**Format** : Diaporama + Démonstration Live + Script Orateur + Préparation Q&R Jury  

---

## 1. Trame du Diaporama (Slide Deck Outline)

### Slide 1 : Titre & Introduction
- **Titre** : Conception & Implémentation d'une Architecture Microservices pour une Plateforme de Livraison de Repas (FitMeal / MiamGo)
- **Présentateurs** : Équipe de Développement
- **Sous-titre** : Microservices FastAPI, Gateway Nginx, Bus Redis, Pattern SAGA Orchestré, Circuit Breaker et Frontend React/TypeScript

### Slide 2 : Contexte Métier & Enjeux Architecturaux
- **Mise en relation tripartie** : Clients, Restaurateurs et Livreurs Indépendants.
- **Problématiques clés** :
  - Trafic asymétrique (forte consultation du catalogue vs transactions d'achats).
  - Criticité du paiement et de la prise de commande.
  - Résilience indispensable face aux défaillances des services tiers (PSP, livreurs).

### Slide 3 : Analyse du Domaine (DDD & Bounded Contexts)
- **Découpage Domain-Driven Design** :
  - *Identité & Comptes* (`service-utilisateurs`)
  - *Restaurants & Catalogue* (`service-restaurants`)
  - *Commandes & Checkout* (`service-commandes`)
  - *Paiements & PSP* (`service-paiements`)
  - *Livraisons & Flotte* (`service-livraisons`)
  - *Notifications* (`service-notifications`)
- **Justification de la Découpe par Charge (ADR 0001 & ADR 0002)** : Isolement des services critiques et fusions pragmatiques pour le prototype.

### Slide 4 : Architecture Générale (C4 Niveau 1 & 2)
- **Composants** :
  - **API Gateway Nginx** (Port 80/8080) : Point d'entrée unique, CORS, traçabilité `X-Correlation-Id`.
  - **6 Microservices FastAPI** autonomes et découplés avec leurs propres bases de données.
  - **Redis** : Bus de messages Pub/Sub pour la chorégraphie événementielle + Caching des paniers & SAGA State.

### Slide 5 : Pattern SAGA Orchestré (Transaction Distribuée)
- **Problème** : Pas de transaction ACID distribuée entre microservices.
- **Solution** : **Orchestrateur Hybride SAGA** rattaché au `service-commandes` (ADR 0003).
- **Étapes critiques synchrones** :
  1. `RECEIVED` -> 2. Validation Restaurant -> 3. Capture Paiement -> 4. Kitchen Ticket Cuisine.
- **Transactions Compensatoires** : Remboursement intégral automatique auprès du PSP en cas de refus du restaurant.

### Slide 6 : Patterns de Résilience (Circuit Breaker, Retry & Idempotence)
- **Problème** : Flaky PSP / Pannes réseau lors du paiement.
- **Solution (ADR 0007)** :
  - **Timeout** (2.0s par appel).
  - **Retry** (x3 avec backoff exponentiel + jitter).
  - **Circuit Breaker** (États `CLOSED`, `OPEN`, `HALF_OPEN` avec seuil de 5 échecs).
  - **Idempotence** garantie par `order_id` côté service-paiements.

### Slide 7 : Architecture Frontend & Vues Dédiées
- **Stack** : React, TypeScript, Vite, TailwindCSS, TanStack Query.
- **Interfaces Exclusives par Rôle (ADR 0010 - RBAC)** :
  - *Vue Client* : Catalogue, Panier, Checkout, Suivi en direct.
  - *Espace Restaurateur* : Création d'établissement, gestion de carte, suivi des tickets de préparation.
  - *Espace Livreur* : Flotte, acceptation de courses, confirmation de livraison au client.
  - *Dashboard QA Testeur* : Santé des 6 microservices, injection PSP Chaos à chaud, comptes de test automatiques.

### Slide 8 : Démonstration Live du Prototype
- *Scénario 1* : Parcours nominal complet (Client -> Commande -> Restaurant accepte -> Livreur livre).
- *Scénario 2* : Simulation de panne PSP (Activation du Mode Chaos 100% échec -> Ouverture Circuit Breaker -> Commande annulée sans débit).

### Slide 9 : Bilan & Perspectives d'Évolution
- **Forces de la solution** :
  - Couverture de tests > 95% backend (Pytest) et frontend (Vitest).
  - Robustesse SAGA et zéro anomalie technique.
  - Conformité 100% aux exigences du cahier des charges.
- **Évolutions futures** : Migration vers Apache Kafka (Event Sourcing) et persistance PostgreSQL.

---

## 2. Script d'Orateur & Minutage Détaillé (15 Minutes)

| Temps | Diapositive | Script de Présentation & Intervenant |
|---|---|---|
| **00:00 - 01:30** | Slide 1 & 2 | *"Bonjour à tous. Nous allons vous présenter l'architecture microservices de FitMeal/MiamGo. Notre objectif a été de concevoir une plateforme hautement disponible et résiliente pour mettre en relation clients, restaurateurs et livreurs. Nous avons découpé le système en 6 microservices indépendants en appliquant la méthodologie Domain-Driven Design."* |
| **01:30 - 04:00** | Slide 3 & 4 | *"Pour découper le domaine, nous avons appliqué le principe de découpe par charge (ADR 0001). Le service-restaurants gère la consultation intensive des menus, tandis que le service-commandes isole la logique critique de checkout. L'ensemble passe par une API Gateway Nginx sur le port 80, qui gère le routage et propage l'en-tête de traçabilité X-Correlation-Id."* |
| **04:00 - 07:00** | Slide 5 & 6 | *"Le cœur de notre architecture réside dans la gestion des transactions distribuées. Pour éviter d'invoquer une BDD partagée, nous avons implémenté le pattern SAGA orchestrait dans le service-commandes. Si le paiement réussit mais que le restaurant refuse le ticket de cuisine, la SAGA déclenche automatiquement une compensation de remboursement auprès du PSP. De plus, notre Circuit Breaker sur mesure protège le système en ouvrant le circuit dès 5 échecs PSP consécutifs."* |
| **07:00 - 11:30** | Slide 7 & 8 | *"Passons maintenant à la Démonstration Live de notre prototype fullstack Docker Compose... [Lancer le scénario de démo en direct sur http://localhost:5173/tester : 1. Connexion Client, 2. Commande, 3. Espace Restaurateur, 4. Espace Livreur, 5. Mode Chaos PSP]."* |
| **11:30 - 13:30** | Slide 9 | *"En résumé, notre prototype valide l'intégralité des choix d'architecture avec plus de 300 tests automatisés. Nous avons documenté l'ensemble des décisions d'architecture sous forme d'ADRs (Architecture Decision Records) consultables dans le dépôt."* |
| **13:30 - 15:00** | Conclusion | *"Nous vous remercions pour votre attention et sommes à votre disposition pour vos questions."* |

---

## 3. Guide de Démonstration Pas-à-Pas (Pour la Soutenance)

1. **Lancement de l'Infrastructure** :
   ```bash
   docker compose up --build
   ```
2. **Étape 1 : Vue Testeur QA (`/tester`)** :
   - Montrer les **health checks** au vert pour les 6 microservices.
   - Cliquer sur le compte prédéfini **"Alice (Client)"** (Connexion instantanée).
3. **Étape 2 : Parcours Client** :
   - Parcourir les restaurants, choisir *La Bella Napoli*.
   - Ajouter la *Pizza Margherita* au panier, lancer le checkout.
   - Valider la commande et montrer la redirection vers la page de suivi en direct.
4. **Étape 3 : Espace Restaurateur (`/restaurant/dashboard`)** :
   - Se connecter avec le compte testeur **"Restaurateur (Le Chef)"**.
   - Voir le ticket de cuisine reçu et changer son statut en **"Prêt en Cuisine"**.
5. **Étape 4 : Espace Livreur (`/courier/dashboard`)** :
   - Se connecter avec le compte testeur **"Bob (Livreur Rapide)"**.
   - Voir la course assignée, cliquer sur **"Prise en charge"** puis **"Valider la livraison au client"**.
6. **Étape 5 : Test de Résilience (PSP Chaos)** :
   - Retourner sur `/tester`, cliquer sur **"Simuler Pannes PSP (100% échec)"**.
   - Tenter de passer une commande côté client.
   - Constater le message explicite : *"Commande annulée sans débit (Circuit Breaker)"*.

---

## 4. Préparation à la Session de Questions / Réponses (Q&R Jury)

### Q1 : Pourquoi avoir choisi une SAGA orchestrée plutôt qu'une SAGA chorégraphiée pour le passage de commande ?
**Réponse** : La phase initiale du checkout (validation -> paiement -> ticket cuisine) requiert des décisions synchrones immédiates pour donner un feedback direct au client au moment du clic. Une SAGA orchestrée dans `service-commandes` offre une vision centralisée du statut de la transaction, facilite l'implémentation des compensations (ex: remboursement) et évite le phénomène d'éparpillement de la logique métier (spaghetti événementiel). En revanche, la suite du processus (préparation, livraison, notifications) est entièrement chorégraphiée via Redis Pub/Sub.

### Q2 : Comment garantissez-vous l'idempotence des paiements en cas de retries ?
**Réponse** : Le `service-paiements` stocke un index d'idempotence basé sur l'identifiant unique de la commande (`order_id`). Lorsqu'un retry est émis suite à un timeout réseau amont, le service paiements détecte si la transaction avait déjà été capturée et renvoie la réponse `200 OK` d'origine avec l'identifiant de paiement existant, sans débiter le client une seconde fois.

### Q3 : Pourquoi Nginx comme API Gateway plutôt que Kong ou Traefik ?
**Réponse** : Pour le scope de notre MVP, Nginx offre une empreinte mémoire minimale, un temps de démarrage ultra-rapide et une configuration déclarative simple pour le routage par préfixe (`/api/v1/*`), la gestion des en-têtes CORS et la propagation du `X-Correlation-Id` (ADR 0006).

### Q4 : Que se passe-t-il si Redis tombe en panne ?
**Réponse** : Les microservices FastAPI sont conçus pour isoler l'impact : les requêtes HTTP directes restent fonctionnelles. Toutefois, les événements asynchrones et la gestion partagée des paniers reposent sur Redis. Dans un déploiement de production, Redis serait déployé en mode Cluster / Sentinel avec réplication et basculement automatique.
