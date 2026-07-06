# ADR 0008 — Pas de frontend pour le prototype

- **Statut** : Accepté
- **Date** : 2026-07-06

## Contexte

Le projet est **noté sur l'architecture microservices** : découpage, communication sync/async, SAGA, résilience, documentation. Le sujet **n'exige pas de frontend**. Le budget total est d'environ **15 heures**, dont le chemin critique (6 services, gateway, SAGA, résilience, infra compose, démo) consomme déjà l'essentiel. Il faut décider comment **démontrer** le fonctionnement de la plateforme : interface graphique ou démonstration par les API.

## Options envisagées

### Option A — Frontend React (stack CLAUDE.md : Vite, Tailwind, shadcn/ui, react-query…)
- **Avantages** : démonstration visuelle attrayante ; parcours utilisateur incarné (client, restaurateur, livreur) ; exploiterait la stack frontend déjà définie et l'agent dev-front.
- **Inconvénients** : coût minimal réaliste de 8 à 12 h (3 rôles d'utilisateurs, états chargement/erreur/vide, responsive, accessibilité et tests Vitest exigés par CLAUDE.md — qui interdit explicitement le prototype bâclé) : **incompatible avec le budget de 15 h** sans sacrifier la SAGA ou la résilience ; n'apporte **aucun point** sur les critères d'évaluation ; un frontend au rabais violerait les standards de qualité du projet.

### Option B — Démonstration par les API : OpenAPI/Swagger + gateway + script de scénario (retenue)
- **Avantages** : coût quasi nul — Swagger (`/docs`) est généré automatiquement par FastAPI ; un **script de démo** (tâche T14) rejoue les scénarios clés de bout en bout via le gateway avec des sorties lisibles ; met en évidence exactement ce qui est noté (enchaînement de la saga, compensations, ouverture du circuit breaker, événements) — souvent **mieux** qu'une IHM qui masque la mécanique ; reproductible par le correcteur en une commande.
- **Inconvénients** : moins spectaculaire ; le jury doit lire des sorties de terminal et du JSON ; les parcours multi-acteurs sont simulés par le script plutôt qu'incarnés.

### Option C — Frontend minimal statique (page HTML servie par le gateway appelant les API)
- **Avantages** : un peu de visuel pour un coût modéré (2–3 h).
- **Inconvénients** : hors stack (CLAUDE.md impose React + TypeScript + tests pour tout frontend) ; ni la qualité d'un vrai front, ni l'économie de l'option B ; valeur démonstrative faible sur les critères d'architecture.

## Décision

Nous retenons **l'option B : aucun frontend dans le prototype**. La démonstration s'appuie sur :

1. **Swagger UI** (`/docs`) de chaque service FastAPI pour l'exploration interactive des contrats.
2. **L'API Gateway** ([ADR 0006](0006-api-gateway-nginx.md)) comme point d'entrée unique des appels de démonstration.
3. Un **script de scénario** (T14) déroulant : commande nominale, refus restaurant → remboursement, panne paiement → retry puis circuit breaker, remboursement partiel — avec sorties lisibles et états finaux vérifiés.

L'agent **dev-front n'est pas sollicité** pour cette itération. La couche frontend reste prévue par CLAUDE.md et pourra être ajoutée ultérieurement sans impact sur le backend : le gateway et le versionnement `/api/v1` constituent déjà le contrat stable qu'un frontend consommerait.

## Conséquences

**Positives**
- ~10 h réinvesties dans ce qui est évalué : SAGA, résilience, communication, documentation.
- Démonstration reproductible et automatisable (le script sert aussi de test de bout en bout informel).
- Aucun code jetable : tout ce qui est livré (services, gateway, script) reste utile après ajout d'un frontend.

**Négatives / points de vigilance**
- Démo moins visuelle : prévoir un déroulé commenté (slides + sorties du script) pour la soutenance.
- Les enchaînements multi-acteurs (restaurateur qui accepte, livreur qui se déplace) sont simulés — à expliciter pour éviter toute confusion sur ce qui est réel.
- Si un frontend est demandé plus tard, l'auth simplifiée (token opaque) devra probablement être renforcée avant exposition réelle.
