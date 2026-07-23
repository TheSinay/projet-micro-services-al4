# Journal d'évolution — 2026-07-23 : Contrôle d'accès par rôle, notifications de livraison et suivi cuisine

**Auteur** : Équipe Fullstack / Agent Documentaliste
**Branche** : `feat/rbac-role-views`

## Fonctionnalités livrées

### 1. Contrôle d'accès par rôle (RBAC) — [ADR 0010](../decisions/0010-controle-acces-par-role-rbac.md)
- Ajout d'un champ **`role`** (`client` | `restaurant_owner` | `courier`, défaut `client`) au service **`users`**, exposé dans `UserRead` : c'est désormais la **source de vérité** du rôle.
- L'inscription force toujours `role = client` ; les comptes restaurateur / livreur passent par le seed.
- Frontend : nouveau garde **`RequireRole`** (auth + rôle), routes cloisonnées (dashboard restaurateur → `restaurant_owner`, dashboard livreur → `courier`, panier / commandes / checkout → `client`, `/tester` public), navigation du Header pilotée par le rôle, redirection post-connexion et page d'accueil adaptées.
- Remplace l'ancienne heuristique fragile d'inférence du rôle par l'e-mail et ferme la faille d'accès aux vues privilégiées par URL.

### 2. Notifications de livraison rétablies — [ADR 0011](../decisions/0011-propagation-user-id-notifications-livraison.md)
- `orders` propage `user_id` à `deliveries` à la création de la livraison ; `deliveries` le stocke et l'inclut dans **`delivery.assigned`** et **`delivery.picked_up`**.
- `user_id` volontairement omis de `delivery.completed` (notification finale déjà portée par `order.delivered`).
- Correction : les notifications client « livreur en route » et « commande récupérée » étaient auparavant perdues faute de `user_id` dans l'événement.

### 3. Suivi des tickets cuisine (restaurateur)
- Backend `restaurants` : nouvel endpoint **`GET /restaurants/{id}/kitchen-tickets`** (+ `list_by_restaurant` au niveau repository et service).
- Frontend : section **« Suivi cuisine »** dans l'espace restaurateur — liste auto-rafraîchie, actions `ACCEPTED → PREPARING → READY`, libellés et couleurs en français.
- Débloque le cycle de vie de la commande : sans le passage `PREPARING → READY`, l'événement `order.ready` n'était jamais émis et aucun livreur n'était affecté. Aucun endpoint de liste des tickets n'existait auparavant.

## Correctifs

- Alignement des types frontend `Delivery` / `Courier` sur le schéma réel du service `deliveries` (statuts, adresses objets, `dropoff_address`, `location`) — voir [problème dédié](../problemes/2026-07-23-contrat-frontend-delivery-courier-divergent.md).
- Mise à jour du test de seed livreurs (4 livreurs disponibles) et reformatage Ruff de `test_restaurants.py` — voir [problème dédié](../problemes/2026-07-23-tests-desynchronises-seed-livreurs-et-format-ruff.md).

## Dettes techniques et points ouverts

- **Couverture frontend très basse (~15 %, préexistant)** : la plupart des pages ne sont pas testées. Le seuil projet de 80 % n'est **pas atteint au global** côté frontend. Une tâche de rattrapage des tests est recommandée.
- **`@vitest/coverage-v8` absent du projet** : utilisé en `--no-save` pour produire le rapport de couverture. Le rendre durable (ajout au `package.json`) nécessite un ADR de dépendance.
- **`failure_rate` du PSP (mode Chaos) stocké en mémoire locale** : non partagé via Redis, donc **non stateless**. Acceptable en mono-instance de démo, à revoir pour un déploiement multi-répliques.
- **`useQuery` dans un `.map` (`TesterDashboardPage`)** : anti-pattern vis-à-vis des rules-of-hooks, toléré tant que la liste `SERVICES` reste constante. À refactorer si la liste devient dynamique.
- **Autorisation par rôle côté API** non généralisée : le rôle est la source de vérité, mais son application par les services backend (et idéalement au gateway) reste à formaliser (voir ADR 0010).
