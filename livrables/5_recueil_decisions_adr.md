# 🏛️ LIVRABLE 5 : RECUEIL DES DÉCISIONS D'ARCHITECTURE (ADR) — FITMEAL / MIAMGO

---

## Sommaire des ADRs (Architecture Decision Records)

1. **[ADR 0001]** Strategie de découpe des microservices par profil de charge
2. **[ADR 0002]** Découpage des microservices et fusions pragmatiques
3. **[ADR 0003]** Pattern SAGA d'Orchestration pour le passage de commande
4. **[ADR 0004]** Utilisation de Redis Pub/Sub comme bus d'événements
5. **[ADR 0005]** Persistance en mémoire isolée pour le prototype
6. **[ADR 0006]** Choix d'Nginx comme API Gateway centralisée
7. **[ADR 0007]** Implémentation du pattern de résilience (Circuit Breaker & Retry)
8. **[ADR 0008]** Absence initiale de frontend (Remplacé par ADR 0009)
9. **[ADR 0009]** Intégration du Frontend React 18, TypeScript et Vite
10. **[ADR 0010]** Contrôle d'accès basé sur les rôles (RBAC)
11. **[ADR 0011]** Propagation du `user_id` et traçabilité des notifications de livraison

---

## Details des ADRs

### ADR 0001 — Stratégie de découpe des microservices par profil de charge
- **Statut** : Accepté
- **Contexte** : Dans une application de livraison de repas, le trafic de consultation (parcourir les cartes, chercher un plat) est 50 à 100 fois supérieur au trafic de commande et de paiement.
- **Décision** : Séparer les services selon leur profil de charge. Isoler le service de recherche et catalogue (`service-restaurants`) du service de paiement et de checkout (`service-commandes`).
- **Conséquences** : Possibilité de passer le service restaurants en cache agressif ou répliqués sans impacter la cohérence des écritures de commandes.

### ADR 0002 — Découpage des microservices et fusions pragmatiques
- **Statut** : Accepté
- **Contexte** : Le découpage DDD théorique produit 9 bounded contexts. Créer 9 microservices distincts pour un prototype court engendrerait une surcomplexité d'infrastructure.
- **Décision** : Réduire le scope à **6 microservices autonomes** en opérant 3 fusions justifiées :
  - Catalogue ➔ `service-restaurants`
  - Livreurs ➔ `service-livraisons`
  - Évaluations ➔ `service-commandes`
- **Conséquences** : Simplification du prototype tout en maintenant des frontières de domaine claires.

### ADR 0003 — Pattern SAGA d'Orchestration pour le passage de commande
- **Statut** : Accepté
- **Contexte** : La validation d'une commande requiert l'intervention de 3 microservices (Commandes, Restaurants, Paiements) sans transaction ACID distribuée.
- **Décision** : Implémenter le pattern **SAGA Orchestré** dans le `service-commandes`. L'orchestrateur exécute la séquence synchrone et émet des transactions compensatoires (ex: remboursement automatique) si le restaurant refuse la commande après débit.
- **Conséquences** : Cohérence garantie sans verrous distribués.

### ADR 0004 — Utilisation de Redis Pub/Sub comme bus d'événements
- **Statut** : Accepté
- **Contexte** : Besoin d'une communication événementielle asynchrone légère pour relayer les statuts (`order.ready`, `delivery.assigned`).
- **Décision** : Utiliser Redis Pub/Sub avec une abstraction d'interface `EventBus` (`RedisEventBus` en prod, `InMemoryEventBus` pour les tests).
- **Conséquences** : Faible empreinte mémoire et déploiement instantané dans Docker.

### ADR 0005 — Persistance en mémoire isolée pour le prototype
- **Statut** : Accepté
- **Contexte** : Valider les choix d'architecture et les contrats d'API sans alourdir les tests par l'administration de bases SQL.
- **Décision** : Utiliser des repositories en mémoire isolés par service derrière des interfaces génériques Python.
- **Conséquences** : Exécution des tests en moins de 3 secondes. Migration future vers PostgreSQL transparente.

### ADR 0006 — Choix d'Nginx comme API Gateway centralisée
- **Statut** : Accepté
- **Contexte** : Nécessité d'offrir un point d'accès unifié (`http://localhost/api/v1/*`) et de gérer les en-têtes CORS.
- **Décision** : Déployer un conteneur Nginx agissant comme reverse-proxy et injectant l'en-tête de traçabilité `X-Correlation-Id`.
- **Conséquences** : Routage performant et isolation du réseau interne des conteneurs.

### ADR 0007 — Implémentation du pattern de résilience (Circuit Breaker & Retry)
- **Statut** : Accepté
- **Contexte** : Le PSP (prestataire de paiement) simulé présente un taux de panne configurable. Il faut éviter l'épuisement des ressources en cas de panne PSP.
- **Décision** : Développer un composant de résilience dans `orders` combinant Timeout (2s), Retry Policy (x3 backoff exponentiel) et Circuit Breaker (ouverture après 5 échecs).
- **Conséquences** : Isolation des pannes PSP et annulation immédiate de la SAGA en mode OPEN.

### ADR 0008 — Absence initiale de frontend
- **Statut** : Obsolet (Remplacé par ADR 0009)

### ADR 0009 — Intégration du Frontend React 18, TypeScript et Vite
- **Statut** : Accepté
- **Contexte** : Faciliter la démonstration live pour les différents profils d'utilisateurs et le jury.
- **Décision** : Développer une application SPA moderne en React 18 / TypeScript / Vite avec Tailwind CSS, comprenant des vues exclusives (Client, Restaurateur, Livreur) et un Dashboard QA Testeur.
- **Conséquences** : Expérience utilisateur complète et démonstration visuelle immédiate des flux SAGA.

### ADR 0010 — Contrôle d'accès basé sur les rôles (RBAC)
- **Statut** : Accepté
- **Contexte** : Sécuriser les accès selon le profil connecté (`client`, `restaurant_owner`, `courier`).
- **Décision** : Définir le champ `role` du `service-utilisateurs` comme source de vérité et implémenter des gardes de routage côté frontend (`RequireRole`) et backend.
- **Conséquences** : Étanchéité garantie entre les rôles utilisateurs.

### ADR 0011 — Propagation du `user_id` et traçabilité des notifications
- **Statut** : Accepté
- **Contexte** : Le service notifications doit transmettre les alertes de livraison au bon client final.
- **Décision** : Propager systématiquement le `user_id` dans les événements de livraison (`delivery.assigned`, `delivery.picked_up`).
- **Conséquences** : Routage précis des notifications Push/Email sans couplage direct entre le service de livraison et le service de compte.
