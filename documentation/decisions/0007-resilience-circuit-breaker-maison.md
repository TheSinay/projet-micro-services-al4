# ADR 0007 — Résilience : timeout, retry et circuit breaker implémentés « maison »

- **Statut** : Accepté
- **Date** : 2026-07-06

## Contexte

L'appel le plus critique de la plateforme est **orders → payments** (étape 3 de la SAGA, [ADR 0003](0003-saga-orchestree-passage-commande.md)) : le service-paiements dépend d'un PSP externe **simulé instable** (variable `FAILURE_RATE`, endpoint chaos). Sans protection, un PSP lent ou en panne bloque l'orchestrateur, accumule les requêtes en attente et propage la panne en cascade — exactement ce que l'isolement du service-paiements ([ADR 0002](0002-decoupage-services-plateforme-livraison.md)) doit circonscrire. Il faut des mécanismes de résilience : timeout, retry et circuit breaker. La question est de savoir s'il faut les **implémenter nous-mêmes** ou adopter une **bibliothèque externe**.

## Options envisagées

### Option A — Bibliothèques externes (tenacity pour le retry, purgatory ou aiobreaker pour le breaker)
- **Avantages** : code éprouvé en production ; riches en options (stratégies de backoff, stockage partagé de l'état du breaker) ; moins de code à écrire.
- **Inconvénients** : dépendances **hors stack autorisée** (CLAUDE.md exige un ADR par dépendance nouvelle) ; il faudrait deux bibliothèques distinctes (aucune ne couvre tout) ; comportement en boîte noire, plus difficile à expliquer en soutenance ; dans un projet **noté d'architecture**, déléguer les patrons de résilience à une bibliothèque en réduit la valeur démonstrative.

### Option B — Implémentation maison dans le service-commandes (retenue)
Un module `resilience.py` interne au service-commandes (jamais importé par un autre service, conformément à la règle de non-partage de code).
- **Avantages** : aucune dépendance nouvelle ; les patrons (backoff exponentiel, machine à états du breaker) sont **écrits, testés et explicables ligne par ligne** — cœur de la valeur pédagogique du projet ; dimensionné exactement au besoin (~100–150 lignes) ; testable finement (horloge injectable) sans réseau.
- **Inconvénients** : risque de bugs subtils (concurrence asyncio, calcul des fenêtres) ; moins de fonctionnalités qu'une bibliothèque mature ; état du breaker **local au processus** (non partagé entre instances).

### Option C — Résilience déléguée à l'infrastructure (service mesh type Istio/Linkerd, ou retries Nginx)
- **Avantages** : aucune logique dans le code applicatif ; politique uniforme.
- **Inconvénients** : totalement disproportionné pour un prototype compose ; les retries au niveau proxy ignorent la sémantique métier (idempotence, compensations de la saga) ; masque les patrons au lieu de les démontrer.

## Décision

Nous retenons **l'option B : implémentation maison** dans `resilience.py` (service-commandes), appliquée aux appels sortants de l'orchestrateur — en priorité **orders → payments**.

Paramètres retenus :
1. **Timeout** : 2,0 s (httpx) sur chaque appel sortant de l'orchestrateur.
2. **Retry** : 3 tentatives maximum, **backoff exponentiel avec jitter**, déclenché **uniquement** sur timeout, erreur réseau ou réponse 5xx — **jamais sur un 4xx** (une erreur client ne se répare pas en réessayant).
3. **Circuit breaker** : machine à états `CLOSED → OPEN → HALF_OPEN` ; ouverture après **5 échecs sur une fenêtre de 30 s** ; en `OPEN`, échec immédiat sans appel réseau ; passage en `HALF_OPEN` après **15 s** — un appel d'essai réussi referme le circuit, un échec le rouvre.
4. **Idempotence** : le service-paiements déduplique par `order_id` — un retry après un timeout dont la requête avait en réalité abouti **ne débite pas deux fois** le client. C'est la condition de sûreté du retry.
5. Circuit ouvert ⇒ échec rapide ⇒ la saga déclenche **immédiatement sa compensation** (ADR 0003) au lieu de laisser le client attendre.

Démonstration : `FAILURE_RATE` (env) et `POST /api/v1/_chaos` (dev) côté payments ; tests unitaires des transitions du breaker et de la politique de retry. Fallback documenté mais non implémenté : catalogue dégradé servi depuis un cache Redis.

## Conséquences

**Positives**
- Panne du PSP circonscrite : pas d'attente en cascade, compensation immédiate, expérience client déterministe.
- Patrons de résilience maîtrisés et démontrables (tests + scénario chaos en démo).
- Zéro dépendance ajoutée ; conformité stricte à CLAUDE.md.
- Le retry est sûr grâce à l'idempotence par `order_id` (pas de double débit).

**Négatives / points de vigilance**
- Code de résilience à maintenir nous-mêmes ; un bug dans le breaker peut soit bloquer des paiements sains (ouverture intempestive), soit laisser passer la cascade (seuils mal calibrés).
- État du breaker en mémoire du processus : avec plusieurs instances du service-commandes, chaque instance découvrirait la panne indépendamment (une version partagée via Redis serait nécessaire à l'échelle).
- Seuils (5 échecs/30 s, réouverture 15 s) fixés a priori pour la démo : en production, ils devraient être calibrés sur des métriques réelles.
- Le module étant non partageable entre services (règle CLAUDE.md), un autre service voulant un breaker devrait le réimplémenter — le jour venu, extraire une bibliothèque transverse versionnée (nouvel ADR).
