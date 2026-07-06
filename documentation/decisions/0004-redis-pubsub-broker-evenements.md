# ADR 0004 — Redis pub/sub comme broker d'événements du prototype

- **Statut** : Accepté
- **Date** : 2026-07-06

## Contexte

L'architecture retenue ([ADR 0002](0002-decoupage-services-plateforme-livraison.md), [ADR 0003](0003-saga-orchestree-passage-commande.md)) requiert une communication **asynchrone** pour le fan-out d'événements : `order.confirmed`, `order.cancelled`, `order.ready`, `delivery.assigned`, `delivery.picked_up`, `delivery.completed`, `evaluation.created`. Plusieurs consommateurs (notifications, commandes) réagissent au même événement sans que l'émetteur attende de réponse. Il faut choisir le broker, sachant que **Redis est déjà présent** dans la stack (état partagé : panier, `saga_state`) et que le budget prototype est d'environ 15 h.

## Options envisagées

### Option A — Redis pub/sub (retenue)
- **Avantages** : Redis est **déjà dans la stack autorisée** (CLAUDE.md) et déjà déployé dans le compose — zéro conteneur ni dépendance supplémentaire ; API triviale (`publish`/`subscribe` du client `redis` Python) ; latence très faible ; largement suffisant pour démontrer le patron événementiel.
- **Inconvénients** : **aucune persistance** — un message publié sans abonné connecté est perdu ; livraison **at-most-once**, pas d'accusé de réception ni de redelivery ; pas de consumer groups ni de relecture d'historique ; pas d'ordre garanti entre canaux.

### Option B — RabbitMQ
- **Avantages** : broker mature ; files durables, acquittements, redelivery, dead-letter queues ; routage riche (exchanges/topics).
- **Inconvénients** : conteneur supplémentaire à opérer ; nouvelle dépendance (`pika`/`aio-pika`) **hors stack autorisée**, exigeant justification et apprentissage ; surdimensionné pour un prototype dont les événements sont tolérants à la perte.

### Option C — Apache Kafka
- **Avantages** : log distribué persistant, relecture, consumer groups, très haut débit ; standard de fait à grande échelle.
- **Inconvénients** : lourdeur opérationnelle maximale (broker + coordination) ; complexité de configuration sans commune mesure avec le besoin ; hors stack autorisée.

## Décision

Nous retenons **l'option A : Redis pub/sub**, avec les limites **explicitement assumées** pour le prototype :

- Livraison **at-most-once**, pas de persistance : acceptable car les consommateurs sont tolérants à la perte (notifications simulées) ou disposent d'un état de rattrapage (`saga_state` côté commandes).
- La **phase critique de la saga reste synchrone** (ADR 0003) : aucune étape impliquant de l'argent ne dépend du pub/sub.
- Format de message normalisé : `{"event": str, "correlation_id": str, "data": {...}}` sur des canaux nommés (`order.*`, `delivery.*`, `evaluation.*`).
- Le broker est abstrait derrière une interface `EventBus` (`RedisEventBus` en production, `InMemoryEventBus` dans les tests) : les tests n'exigent aucun Redis actif et le broker est **remplaçable sans toucher au code métier**.

**Évolution prévue à l'échelle** : migration vers **Redis Streams** (persistance, consumer groups, `XACK` — sans nouveau conteneur) ou **Kafka** (si volumétrie et relecture d'historique l'exigent). Ce changement fera l'objet d'un nouvel ADR ; grâce à l'interface `EventBus`, il sera localisé dans les implémentations.

## Conséquences

**Positives**
- Aucune infrastructure supplémentaire : compose inchangé, démarrage rapide.
- Patron événementiel démontré (fan-out multi-consommateurs, découplage émetteur/récepteur).
- Testabilité hermétique via `InMemoryEventBus`.
- Chemin de migration clair et localisé (interface `EventBus`).

**Négatives / points de vigilance**
- Un consommateur redémarré **perd les événements émis pendant son absence** : une commande peut rester en attente si `order.ready` est manqué (limitation à mentionner en démo ; atténuation possible : re-publication manuelle ou polling de secours, non implémentés).
- Pas de garantie d'ordre ni de déduplication : les consommateurs doivent être idempotents.
- Redis devient doublement critique (état partagé **et** bus d'événements) — SPOF déjà identifié dans l'ADR 0001, à traiter par réplication en production.
