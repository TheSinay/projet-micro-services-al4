# 2026-07-06 — Lancement de la plateforme de livraison de repas

Première demande fonctionnelle du projet : une plateforme de livraison de repas (type Uber Eats) reliant clients, restaurateurs et livreurs. Le planificateur a produit le plan d'architecture et d'exécution (budget ~15 h) ; la phase de conception est documentée.

## Découpage décidé

**6 microservices + 1 API Gateway** ([ADR 0002](../decisions/0002-decoupage-services-plateforme-livraison.md)), en application de la découpe par charge (ADR 0001) :

- **gateway** (Nginx, 8080) — point d'entrée unique, routage `/api/v1/*` ;
- **service-utilisateurs** (8001) — comptes, auth, adresses ;
- **service-restaurants** (8002) — profils, catalogue, recherche, validation, kitchen tickets (service le plus chaud en lecture) ;
- **service-commandes** (8003) — panier, commandes, orchestrateur SAGA, évaluations ;
- **service-paiements** (8004) — paiements/remboursements, PSP simulé instable, cible du circuit breaker ;
- **service-livraisons** (8005) — livreurs, assignation, suivi ;
- **service-notifications** (8006) — consommateur d'événements, envois simulés.

Fusions prototype documentées avec déclencheurs d'extraction : catalogue→restaurants, évaluations→commandes, livreurs→livraisons.

## ADRs acceptés (0002 → 0008)

- **0002** — Découpage en 6 services + gateway (bounded contexts DDD × charge).
- **0003** — SAGA orchestrée par le service-commandes pour le passage de commande (hybride : chorégraphie en aval).
- **0004** — Redis pub/sub comme broker d'événements du prototype (limites at-most-once assumées ; évolution Redis Streams/Kafka).
- **0005** — Persistance in-memory derrière interfaces repository (migration PostgreSQL facilitée).
- **0006** — Nginx comme API Gateway (routage, corrélation ; futur : auth, rate limiting, TLS).
- **0007** — Résilience maison dans le service-commandes : timeout 2 s, retry ×3 backoff+jitter, circuit breaker CLOSED/OPEN/HALF_OPEN (5 échecs/30 s, réouverture 15 s), idempotence par `order_id`.
- **0008** — Pas de frontend pour le prototype (démo via OpenAPI, gateway, script de scénario).

## Documentation mise à jour

- `architecture.md` réécrit : analyse du domaine, inventaire des 6 services + gateway, principes, communication sync/async, gestion des données, gateway, résilience, SAGA, et **diagrammes C4 Mermaid** (contexte niveau 1, conteneurs niveau 2).

**Prochaine étape** : implémentation par dev-back en commençant par le gabarit de référence (service-utilisateurs, T04), puis les autres services, la SAGA, la résilience et l'infrastructure compose.
