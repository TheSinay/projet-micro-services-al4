# ADR 0001 — Stratégie de découpe microservices par charge

- **Statut** : Accepté
- **Date** : 2026-07-06

## Contexte

L'application est bâtie en architecture microservices. La question fondatrice est : **selon quel critère découper les services ?** Le découpage détermine la scalabilité, la résilience et le coût d'exploitation. Une découpe uniquement par domaine métier (Domain-Driven Design pur) produit souvent des services au dimensionnement homogène, alors que dans la réalité quelques composants concentrent l'essentiel de la charge.

## Options envisagées

### Option A — Découpe purement par domaine métier
- **Avantages** : frontières conceptuelles claires, alignées sur le langage métier ; faible couplage logique.
- **Inconvénients** : ne tient pas compte des différences de charge ; on scale des services entiers pour un seul endpoint chaud ; gaspillage de ressources ; goulots d'étranglement mal isolés.

### Option B — Monolithe modulaire
- **Avantages** : simplicité de déploiement au départ.
- **Inconvénients** : contraire à l'objectif du projet ; scalabilité globale seulement ; couplage fort à terme.

### Option C — Découpe par charge d'utilisation (retenue)
- **Avantages** : les composants fortement sollicités sont isolés et scalés indépendamment ; ressources allouées là où c'est utile ; goulots d'étranglement circonscrits ; compatible avec un affinage par domaine à l'intérieur de chaque service.
- **Inconvénients** : nécessite d'estimer/mesurer la charge avant de découper ; frontières parfois moins « pures » que le DDD ; exige de la discipline (chaque découpe doit être justifiée).

## Décision

Nous adoptons **l'option C : la découpe par charge d'utilisation**, en complément (et non à l'exclusion) des considérations de domaine.

Règles :
1. Tout composant identifié comme **fortement sollicité** (fort trafic, opérations coûteuses, appelé par plusieurs services) est **isolé dans son propre microservice**, avec sa propre base ou son propre schéma si nécessaire.
2. Chaque service est **stateless** ; l'état partagé (sessions, cache) réside dans **Redis**. Objectif : **load balancing horizontal** sans modification de code.
3. Chaque service expose **`/health`** pour les health checks.
4. Communication inter-services en **HTTP/REST** (`httpx` async), ou message broker si un ADR le justifie. **Jamais d'import de code** entre services.
5. **Avant toute création de service**, le planificateur justifie la découpe : charge attendue, couplage, criticité. En cas de doute, on intègre à un service existant et on documente la possibilité d'extraction future.

## Conséquences

**Positives**
- Scalabilité ciblée et économe.
- Résilience : un service chaud saturé n'entraîne pas les autres.
- Prêt pour un reverse proxy (Nginx/Traefik) devant N instances.

**Négatives / points de vigilance**
- Nécessite d'estimer la charge (au besoin par mesure/observabilité).
- Dépendance opérationnelle à Redis pour l'état partagé (SPOF potentiel à traiter : réplication/cluster).
- Plus de surface réseau et de contrats à maintenir → discipline documentaire (ADR + `architecture.md`) indispensable.
