# ADR 0011 — Propagation de `user_id` pour les notifications de livraison

- **Statut** : Accepté
- **Date** : 2026-07-23
- **Décideur** : Équipe Fullstack / Agent Planificateur
- **Branche** : `feat/rbac-role-views`

## Contexte

Le service **notifications** consomme les événements Redis (ADR 0004) et route les notifications client sur la clé **`user_id`** contenue dans les données de l'événement.

Or les événements **`delivery.assigned`** (« votre livreur est en route ») et **`delivery.picked_up`** (« votre commande a été récupérée ») sont émis par le service **`deliveries`**, qui **ne connaît que `order_id`** : il ne dispose pas de `user_id`. Ces événements étaient donc publiés **sans `user_id`**, si bien que le routage échouait silencieusement et que **les notifications client correspondantes étaient perdues**.

Il fallait rendre `user_id` disponible dans ces deux événements **sans introduire de nouveau couplage ni de nouvelle dépendance**.

## Options envisagées

### Option A — `notifications` résout `order_id → user_id`
Le service notifications, en recevant un événement `delivery.*`, appellerait le service `orders` (ou `deliveries`) en HTTP pour retrouver le `user_id` associé à la commande.
- *Avantages* : `deliveries` reste inchangé.
- *Inconvénients* : ajoute un **client HTTP sortant à un service qui est aujourd'hui un pur consommateur d'événements** → nouveau couplage synchrone, nouvelle source de panne, latence, et un ADR de résilience à prévoir. Contraire à l'esprit « notifications = simple consommateur ».

### Option B — `orders` propage `user_id` à la création de livraison, `deliveries` le relaie (retenue)
Le service `orders` connaît déjà `user_id` **et** appelle déjà `deliveries` en HTTP pour l'assignation. Il transmet donc `user_id` au moment de la création de la livraison ; `deliveries` le **stocke** et l'**inclut** dans les événements qu'il publie.
- *Avantages* : **aucun nouvel appel inter-services**, aucune nouvelle dépendance ; réutilise un flux HTTP déjà existant ; `notifications` reste un pur consommateur.
- *Inconvénients* : `deliveries` transporte une donnée (`user_id`) qui ne lui appartient pas métier — donnée simplement relayée, pas exploitée par sa logique.

## Décision

Nous retenons l'**option B** :

- **`orders`** transmet `user_id` à `deliveries` lors de la **création de la livraison** (flux HTTP synchrone déjà en place pour l'assignation).
- **`deliveries`** **stocke** `user_id` sur la livraison et l'**inclut** dans les événements **`delivery.assigned`** et **`delivery.picked_up`**.
- `user_id` est **volontairement omis de `delivery.completed`** : la notification finale au client est déjà portée par l'événement **`order.delivered`** (émis côté `orders`, qui possède le `user_id`). Ajouter `user_id` à `delivery.completed` aurait dupliqué la notification de fin.

## Conséquences

**Positives**
- Les notifications client « livreur en route » et « commande récupérée » sont de nouveau délivrées.
- Aucun couplage HTTP supplémentaire : `notifications` demeure un pur consommateur d'événements ; le graphe d'appels synchrones est inchangé.
- Pas de nouvelle dépendance à introduire (pas d'ADR de stack supplémentaire).

**Négatives / points de vigilance**
- `deliveries` relaie une donnée qui relève du contexte « commandes » (`user_id`) : couplage de données faible, assumé et documenté.
- La cohérence du routage repose sur la présence effective de `user_id` dans les événements : à vérifier lors de tout futur changement de contrat d'événement `delivery.*`.
