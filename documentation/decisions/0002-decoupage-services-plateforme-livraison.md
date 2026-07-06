# ADR 0002 — Découpage en services de la plateforme de livraison de repas

- **Statut** : Accepté
- **Date** : 2026-07-06

## Contexte

La première demande fonctionnelle du projet est une **plateforme de livraison de repas** (type Uber Eats) : des clients commandent des plats auprès de restaurants, paient en ligne, et des livreurs assurent la livraison. Il faut décider **combien de services créer et où placer les frontières**, en appliquant la stratégie de découpe par charge décidée dans l'[ADR 0001](0001-strategie-decoupe-microservices-par-charge.md), dans un budget de prototype d'environ 15 heures.

L'analyse du domaine (Domain-Driven Design) fait ressortir les bounded contexts suivants : identité & comptes, restaurants, catalogue de plats, commandes & checkout, paiement, livreurs, livraisons, notifications, évaluations. La question est de savoir lesquels méritent leur propre service **dès maintenant** au regard de la charge et de la criticité, et lesquels peuvent être fusionnés dans un service voisin en attendant.

## Options envisagées

### Option A — Un service par bounded context (9 services + gateway)
- **Avantages** : frontières DDD « pures » ; chaque contexte évolue et se déploie indépendamment ; pas de refactoring d'extraction plus tard.
- **Inconvénients** : irréaliste dans le budget imparti (9 services × gabarit + tests + Docker) ; plusieurs contextes (catalogue, évaluations, livreurs) n'ont ni la charge ni la criticité justifiant un isolement immédiat selon l'ADR 0001 ; surface réseau et contrats multipliés sans bénéfice mesurable au stade prototype.

### Option B — Découpe minimale (2–3 services : « front-office », « back-office », paiement)
- **Avantages** : très rapide à livrer ; peu de contrats inter-services.
- **Inconvénients** : mélange des profils de charge (la recherche de restaurants, très chaude en lecture, cohabiterait avec l'orchestration de commandes, critique en écriture) ; contraire à l'ADR 0001 ; ne démontre ni la découpe par charge ni les patrons attendus (SAGA, résilience, asynchrone) de façon convaincante.

### Option C — 6 services + gateway, alignés charge × domaine (retenue)
Un service par regroupement de bounded contexts au **profil de charge homogène**, avec fusions explicites et réversibles pour les contextes à faible volume.
- **Avantages** : chaque frontière est justifiée par la charge et la criticité (règle 5 de l'ADR 0001) ; volume de travail tenable ; les fusions sont documentées avec leurs déclencheurs d'extraction, donc réversibles sans dette cachée.
- **Inconvénients** : certains services portent deux contextes (frontières moins « pures ») ; l'extraction future imposera une migration de données et de contrats.

## Décision

Nous retenons **l'option C : 6 services métier + 1 gateway**, chacun avec **son propre store de données** (aucune donnée partagée entre services) :

| # | Service | Bounded context(s) | Justification charge/criticité |
|---|---|---|---|
| G | **gateway** (Nginx, 8080) | edge | Point d'entrée unique, routage `/api/v1/<domaine>/*`, propagation `X-Correlation-Id` |
| 1 | **service-utilisateurs** (8001) | Identité & comptes | Charge modérée mais **criticité auth** : tous les parcours en dépendent → isolé |
| 2 | **service-restaurants** (8002) | Restaurants + catalogue | Service le **plus chaud en lecture** (~80 % du trafic : recherche, consultation de menus) → isolé par charge (ADR 0001) |
| 3 | **service-commandes** (8003) | Commandes & checkout + évaluations | Cœur critique en écriture, **orchestrateur de la SAGA**, vérité sur l'état des commandes |
| 4 | **service-paiements** (8004) | Paiement | **Criticité maximale** + dépendance à un PSP externe instable → isolement pour circonscrire les pannes (cible du circuit breaker) |
| 5 | **service-livraisons** (8005) | Livraisons + livreurs | Assignation et suivi ; profil de charge distinct des commandes |
| 6 | **service-notifications** (8006) | Notifications | Fan-out purement asynchrone, tolérant à la perte, zéro couplage → service dédié consommateur d'événements |

### Fusions assumées pour le prototype (et déclencheurs d'extraction)

Conformément à la règle « en cas de doute, intégrer et documenter l'extraction future » de l'ADR 0001 :

| Fusion | Hébergé dans | Pourquoi fusionner maintenant | Déclencheur d'extraction future |
|---|---|---|---|
| **Catalogue** (menus, plats, prix) | service-restaurants | Le catalogue est consulté conjointement au profil restaurant ; même profil lecture-intensive | Si le trafic de **recherche/consultation du catalogue** domine et diverge du reste (ex. > 10× le trafic d'écriture, ou besoin d'un index de recherche dédié type Elasticsearch), extraire un **catalogue-service en lecture seule**, alimenté par les événements du service-restaurants (CQRS) |
| **Évaluations** | service-commandes | Faible volume (au plus une évaluation par commande livrée) ; fortement liée au cycle de vie de la commande | Si les évaluations deviennent un flux à part entière (modération, agrégats de notes, anti-fraude) ou pèsent sur les performances du service-commandes, extraire un **evaluations-service** consommant `order.delivered` |
| **Livreurs** (profils, disponibilité, position) | service-livraisons | Le matching livreur↔livraison est central et les deux données sont co-consultées | Si le **tracking GPS temps réel** est mis en place (charge d'écriture massive et continue, très différente du CRUD livraisons), extraire un **courier-service** dédié à la position/disponibilité |

### Règles associées

- Une base (store) **par service** ; les commandes conservent un **snapshot des prix** dans `Order.items` → découplage du catalogue, cohérence éventuelle assumée.
- Communication synchrone REST là où une réponse est requise (validation, paiement, assignation), asynchrone via événements Redis pour le fan-out (voir [ADR 0003](0003-saga-orchestree-passage-commande.md) et [ADR 0004](0004-redis-pubsub-broker-evenements.md)).

## Conséquences

**Positives**
- Découpage entièrement justifiable devant un jury : chaque frontière découle d'un profil de charge ou d'une criticité, en cohérence avec l'ADR 0001.
- Volume de travail compatible avec le budget de 15 h, sans sacrifier les patrons attendus (SAGA, résilience, sync/async).
- Les fusions sont **réversibles** : interfaces repository et événements déjà en place, déclencheurs d'extraction documentés — pas de dette cachée.
- Aucune donnée partagée : chaque service peut changer de technologie de persistance indépendamment (voir [ADR 0005](0005-persistance-memoire-prototype.md)).

**Négatives / points de vigilance**
- Le service-restaurants et le service-commandes portent chacun deux contextes : la discipline de séparation interne (modules distincts) doit être maintenue pour que l'extraction future reste peu coûteuse.
- L'extraction d'un catalogue-service imposera une migration de contrats côté gateway et clients.
- Le snapshot des prix implique qu'un changement de prix ne se répercute pas sur les commandes en cours — comportement voulu, mais à expliquer (cohérence éventuelle).
- 7 conteneurs à orchestrer (compose, healthchecks) : coût d'infrastructure non négligeable pour un prototype.
