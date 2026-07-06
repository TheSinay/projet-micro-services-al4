# ADR 0003 — SAGA orchestrée pour le passage de commande

- **Statut** : Accepté
- **Date** : 2026-07-06

## Contexte

Le passage de commande (`PLACE_ORDER`) est une transaction métier qui traverse **quatre services** : service-commandes (création et état de la commande), service-restaurants (validation puis acceptation en cuisine), service-paiements (autorisation/capture) et service-livraisons (assignation d'un livreur). Chaque service possède son propre store ([ADR 0002](0002-decoupage-services-plateforme-livraison.md)) : une transaction ACID distribuée est impossible. Il faut garantir qu'en cas d'échec à n'importe quelle étape (restaurant fermé, paiement refusé, cuisine qui refuse, aucun livreur), le système revienne à un état cohérent — notamment **rembourser le client si le paiement a été capturé** avant l'échec.

Le patron SAGA s'impose ; reste à choisir entre **orchestration** et **chorégraphie**.

## Options envisagées

### Option A — Chorégraphie (événements en cascade, sans coordinateur)
Chaque service réagit aux événements des autres : `order.created` → restaurants valide et publie → payments paie et publie → etc.
- **Avantages** : couplage faible entre services ; pas de point de coordination central ; ajout d'un consommateur sans toucher aux autres.
- **Inconvénients** : la séquence globale n'est visible **nulle part** dans le code — difficile à comprendre, à tester et à présenter ; les compensations sont dispersées dans chaque service ; le diagnostic d'une saga bloquée exige de corréler les logs de 4 services ; avec Redis pub/sub sans persistance ([ADR 0004](0004-redis-pubsub-broker-evenements.md)), un événement perdu laisse la saga dans un état indéterminé sans responsable clair.

### Option B — Orchestration par le service-commandes (retenue pour la phase critique)
Le service-commandes pilote explicitement la séquence par des appels REST synchrones et déclenche lui-même les compensations.
- **Avantages** : la commande est la **donnée pivot** et son service est le propriétaire naturel de l'état (`Order.status`, `saga_state`) ; séquence lisible en un seul endroit ; compensations explicites et testables unitairement ; c'est là que se concentrent les mécanismes de résilience ([ADR 0007](0007-resilience-circuit-breaker-maison.md)).
- **Inconvénients** : le service-commandes connaît les API de 3 services (couplage plus fort) ; il devient un point critique ; risque de dérive vers un « orchestrateur dieu » si on y ajoute trop de logique.

### Option C — Hybride : orchestration de la phase critique, chorégraphie en aval (retenue)
- **Avantages** : combine la lisibilité de l'orchestration là où l'argent est en jeu, et le découplage de la chorégraphie là où aucune réponse n'est attendue (notifications, suivi de livraison).
- **Inconvénients** : deux styles de communication à documenter et à maîtriser.

## Décision

Nous retenons **l'option C** : une **SAGA orchestrée par le service-commandes** pour la phase critique du passage de commande, prolongée par une **chorégraphie événementielle** en aval.

### Étapes et compensations

| Étape | Action (synchrone, pilotée par service-commandes) | Compensation si échec |
|---|---|---|
| 1 | Créer `Order` en statut `RECEIVED`, calcul du total | — |
| 2 | `POST restaurants /api/v1/restaurants/{id}/order-validations` (ouvert, plats disponibles, prix conformes) | Order → `CANCELLED`, événement `order.cancelled` |
| 3 | `POST payments /api/v1/payments` — protégé par **circuit breaker + retry + timeout** (ADR 0007) | Order → `CANCELLED` (rien à rembourser, paiement non abouti) |
| 4 | `POST restaurants /.../kitchen-tickets` (acceptation cuisine ; refus paramétrable) | **Remboursement total** (`POST payments/{id}/refunds`) puis Order → `CANCELLED` |
| 5 | Order → `PREPARING`, événement `order.confirmed` | — fin nominale |

### Continuation chorégraphiée (aval)

- `order.ready` (publié par restaurants) → le service-commandes appelle `POST deliveries /api/v1/deliveries` ; si **aucun livreur** disponible : retry différé, puis **remboursement total + CANCELLED**.
- `delivery.assigned` → Order → `DELIVERING` ; `delivery.completed` → Order → `DELIVERED`.
- service-notifications consomme `order.*` et `delivery.*` sans participer à la saga.

L'avancement est tracé dans `Order.saga_state` (Redis), ce qui rend l'état de chaque saga observable.

## Conséquences

**Positives**
- Cohérence garantie par compensations explicites : aucun client débité pour une commande annulée.
- Séquence et compensations testables unitairement dans le service-commandes (services aval mockés).
- Diagnostic simple : `saga_state` + `X-Correlation-Id` suffisent à suivre une commande de bout en bout.
- Les mécanismes de résilience sont concentrés au bon endroit (l'orchestrateur).

**Négatives / points de vigilance**
- Le service-commandes est couplé aux contrats de 3 services : tout changement d'API aval l'impacte.
- Disponibilité : si le service-commandes tombe en pleine saga, la reprise repose sur `saga_state` — pas de reprise automatique implémentée dans le prototype (limitation documentée).
- Les compensations doivent être **idempotentes** (remboursement par `order_id`) pour tolérer les retries.
- La partie chorégraphiée hérite des limites de Redis pub/sub (perte possible d'événements, ADR 0004).
