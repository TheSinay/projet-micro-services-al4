# ADR 0005 — Persistance en mémoire derrière des interfaces repository

- **Statut** : Accepté
- **Date** : 2026-07-06

## Contexte

Chaque service possède son propre store de données ([ADR 0002](0002-decoupage-services-plateforme-livraison.md)). La stack autorisée (CLAUDE.md) prévoit SQLAlchemy + Alembic, mais le sujet du projet **autorise explicitement le mock de la persistance** pour le prototype. Mettre en place 6 bases PostgreSQL (modèles ORM, migrations Alembic, fixtures de test, conteneurs) représente plusieurs heures par service, dans un budget total d'environ 15 h dont l'essentiel doit aller aux patrons d'architecture (SAGA, résilience, communication) — le cœur de l'évaluation.

## Options envisagées

### Option A — Vraie base de données par service (PostgreSQL + SQLAlchemy + Alembic)
- **Avantages** : réalisme production ; contraintes d'intégrité, transactions et requêtes réelles ; démontre la maîtrise de l'ORM et des migrations ; données survivant au redémarrage.
- **Inconvénients** : coût estimé de 4 à 6 h sur les 15 h du budget (modèles, migrations, sessions async, fixtures, 6 conteneurs de plus) ; complexifie les tests (base de test ou testcontainers) ; n'apporte **aucune valeur** sur les critères évalués (découpage, SAGA, résilience, sync/async).

### Option B — Stores in-memory derrière des interfaces repository (retenue)
Dictionnaires Python encapsulés dans des classes repository respectant une interface (protocole typé), injectées dans la couche service.
- **Avantages** : autorisé par le sujet ; mise en œuvre immédiate ; tests rapides et hermétiques (aucune infrastructure requise) ; la **séparation routes / services / repositories imposée par CLAUDE.md est respectée à l'identique** — le code métier ignore la nature du stockage ; migration future = écrire une implémentation SQLAlchemy de chaque interface, sans toucher aux routes ni aux services.
- **Inconvénients** : données perdues au redémarrage du service ; pas de contraintes d'intégrité ni de transactions ; **incompatible avec plusieurs instances load-balancées** d'un même service (l'état vivrait dans la mémoire de chaque instance) — en contradiction temporaire avec le principe stateless de l'ADR 0001.

### Option C — SQLite fichier par service
- **Avantages** : persistance réelle à coût modéré ; SQLAlchemy utilisable.
- **Inconvénients** : coût ORM/migrations presque identique à l'option A pour un réalisme moindre ; verrous d'écriture pénalisants ; ni la simplicité de B, ni le réalisme de A.

## Décision

Nous retenons **l'option B : persistance in-memory derrière des interfaces repository**, pour tous les services du prototype.

Règles d'implémentation :
1. Chaque agrégat a une **interface repository** (protocole typé) déclarant ses opérations ; l'implémentation `InMemory*Repository` est un détail d'infrastructure injecté au démarrage.
2. **Aucun accès direct** aux dictionnaires depuis les routes ou les services.
3. L'état qui doit réellement être partagé ou survivre (panier, `saga_state`) est placé dans **Redis**, pas dans les stores in-memory.
4. La migration vers PostgreSQL/SQLAlchemy (déjà dans la stack autorisée) se fera service par service en ajoutant une implémentation `Sql*Repository` — nouvel ADR non requis, la stack étant déjà validée ; seul le compose et la configuration changeront.

## Conséquences

**Positives**
- Budget préservé pour la SAGA, la résilience et la communication inter-services.
- Tests unitaires ultra-rapides et hermétiques : aucune base ni conteneur requis, couverture ≥ 80 % atteignable sans usine à fixtures.
- Frontière propre : le jour de la migration, seules les implémentations repository changent.

**Négatives / points de vigilance**
- Données volatiles : chaque redémarrage repart des seeds — comportement à annoncer en démo.
- **Une seule instance par service** tant que la persistance est en mémoire : le load balancing horizontal promis par l'ADR 0001 n'est démontrable qu'après migration vers une vraie base (limitation explicitement assumée et documentée).
- Pas de contraintes d'unicité/intégrité automatiques : les invariants (email unique, cumul des remboursements ≤ montant capturé) doivent être vérifiés dans le code des services — et testés.
