# ADR 0006 — Nginx comme API Gateway

- **Statut** : Accepté
- **Date** : 2026-07-06

## Contexte

Avec 6 services exposant chacun leur API, les clients (Swagger, script de démo, futur frontend) ne doivent pas connaître 6 adresses ni gérer 6 points d'entrée. Il faut un **point d'entrée unique** qui route les requêtes vers le bon service selon le chemin (`/api/v1/<domaine>/*`), propage l'identifiant de corrélation `X-Correlation-Id`, et pourra porter à terme les préoccupations transverses (authentification centralisée, rate limiting, TLS). CLAUDE.md prévoit déjà Nginx/Traefik comme reverse proxy devant les services.

## Options envisagées

### Option A — Nginx (retenue)
- **Avantages** : **déjà prévu par CLAUDE.md** (aucune dépendance nouvelle à justifier) ; configuration déclarative de quelques dizaines de lignes pour du routage par préfixe ; extrêmement éprouvé et performant ; image Docker officielle légère ; prépare directement le rôle de load balancer (`upstream` avec N instances) promis par l'ADR 0001 ; aucune ligne de code à écrire ni à tester.
- **Inconvénients** : logique dynamique limitée sans modules (Lua/njs) ; pas d'auth applicative native — devra déléguer (`auth_request`) le jour venu ; configuration à maintenir en parallèle des services.

### Option B — Gateway FastAPI « maison »
- **Avantages** : pleine maîtrise en Python ; logique arbitraire (auth, agrégation de réponses, transformation) ; homogène avec le reste de la stack.
- **Inconvénients** : c'est un **7e service à développer, typer, tester (couverture ≥ 80 %) et maintenir** pour réinventer du proxying que Nginx fait nativement ; performances moindres ; le gateway devient un goulot applicatif et une surface de bugs sur le chemin de 100 % du trafic.

### Option C — Kong (ou équivalent : Traefik, KrakenD)
- **Avantages** : gateway « clé en main » avec plugins (auth, rate limiting, observabilité) ; administrable par API.
- **Inconvénients** : hors stack autorisée ; conteneur (voire base de données) supplémentaire ; courbe d'apprentissage disproportionnée pour du simple routage par préfixe dans un prototype.

## Décision

Nous retenons **l'option A : Nginx**, en conteneur Docker exposé sur le **port 8080**, seul composant publié à l'extérieur du réseau compose.

Rôle dans le prototype :
1. **Point d'entrée unique** : les clients n'appellent que le gateway.
2. **Routage par préfixe** : `/api/v1/users/*` → service-utilisateurs, `/api/v1/restaurants/*` → service-restaurants, `/api/v1/orders/*` → service-commandes, `/api/v1/payments/*` → service-paiements, `/api/v1/deliveries/*` → service-livraisons, `/api/v1/notifications/*` → service-notifications.
3. **Propagation de `X-Correlation-Id`** : transmis s'il est présent (les services le génèrent s'il manque), pour le traçage de bout en bout dans les logs structlog.
4. Les services restent joignables directement sur leurs ports (8001–8006) **uniquement pour le développement et la démo Swagger** ; le chemin nominal passe par le gateway.

Responsabilités **futures** (documentées, non implémentées) : authentification centralisée (`auth_request` vers service-utilisateurs), rate limiting (`limit_req`), terminaison TLS, load balancing de N instances par service (`upstream`).

## Conséquences

**Positives**
- Zéro code applicatif à tester : le gateway est de la configuration versionnée.
- Découplage clients/topologie : on peut déplacer, découper ou dupliquer un service sans changer les URL publiques (utile pour les extractions futures de l'ADR 0002).
- Chemin tout tracé vers le load balancing horizontal et les préoccupations transverses.

**Négatives / points de vigilance**
- Chaque nouveau service ou changement de préfixe exige une mise à jour de la configuration Nginx — à garder synchronisée avec `architecture.md`.
- Pas d'authentification au gateway dans le prototype : chaque service vérifie le token lui-même (limitation assumée, cohérente avec l'auth simplifiée du projet).
- Point de passage unique : la panne du gateway rend tout inaccessible — en production, il faudra le répliquer.
