# ADR 0010 — Contrôle d'accès par rôle (RBAC) porté par le service utilisateurs

- **Statut** : Accepté
- **Date** : 2026-07-23
- **Décideur** : Équipe Fullstack / Agent Planificateur
- **Branche** : `feat/rbac-role-views`

## Contexte

La plateforme met en relation trois types d'acteurs (client, restaurateur, livreur) et expose des vues dédiées : tableau de bord restaurateur, tableau de bord livreur, panier / checkout / commandes côté client, et une vue Testeur (QA).

Jusqu'ici, il n'existait **aucun véritable système de rôles** :

- Le rôle de l'utilisateur était **deviné côté frontend par correspondance d'adresse e-mail** (heuristique fragile : dépendante d'un motif d'e-mail, non fiable, impossible à faire évoluer proprement).
- Les vues restaurateur, livreur et testeur étaient **accessibles à tout le monde par simple saisie de l'URL** : aucune restriction réelle. Un client pouvait ouvrir le tableau de bord restaurateur.

Le besoin : disposer d'une **source de vérité serveur** sur le rôle d'un compte et cloisonner les vues du frontend en fonction de ce rôle.

## Options envisagées

### Option A — Conserver l'heuristique par e-mail (statu quo)
- *Avantages* : aucun changement backend, aucune migration de données.
- *Inconvénients* : fragile (couplée à un motif d'e-mail), **ne corrige pas la faille de fond** (les vues restent ouvertes par URL), logique de sécurité côté client uniquement, impossible à auditer.

### Option B — Choix du rôle par l'utilisateur au moment de l'inscription
- *Avantages* : self-service, pas de provisioning manuel.
- *Inconvénients* : n'importe qui pourrait se déclarer restaurateur ou livreur — les comptes non-client doivent être **contrôlés** (rattachés à un établissement réel, à une flotte). Ouvre une surface d'abus injustifiée pour un prototype.

### Option C — Rôle porté par le service `users` comme source de vérité (retenue)
- *Avantages* : source de vérité unique et serveur ; rôle exposé dans le profil (`UserRead`) et consommé par tous les clients ; l'inscription reste sûre (toujours `client`) ; les comptes privilégiés sont créés de façon contrôlée (seed / futur back-office admin).
- *Inconvénients* : nécessite d'ajouter un champ au modèle utilisateur et d'introduire un garde de route côté frontend ; l'attribution d'un rôle non-client passe par un canal d'administration (seed pour l'instant).

## Décision

Nous retenons l'**option C**.

- Le service **`users`** porte un champ **`role`** de type énuméré : `client` | `restaurant_owner` | `courier`, **valeur par défaut `client`**. C'est la **source de vérité**.
- Le champ `role` est **exposé dans `UserRead`** (profil utilisateur), donc disponible après authentification.
- **L'inscription force systématiquement `role = client`** : aucun moyen de s'auto-attribuer un rôle privilégié. Les comptes restaurateur / livreur sont créés par **seed** (et, à terme, par un back-office administrateur).
- Le **frontend lit `user.role`** issu du profil et n'infère plus jamais le rôle depuis l'e-mail.

### Conséquences côté frontend

- Nouveau garde **`RequireRole`** : combine authentification **et** vérification du rôle.
- **Routes cloisonnées** :
  - tableau de bord restaurateur → `restaurant_owner` ;
  - tableau de bord livreur → `courier` ;
  - panier / commandes / checkout → `client` ;
  - `/tester` reste **public** (outil QA).
- **Navigation du Header pilotée par le rôle** : chaque acteur ne voit que les entrées qui le concernent.
- **Redirection post-connexion** et **page d'accueil** adaptées au rôle de l'utilisateur.

## Conséquences

**Positives**
- Faille de fond corrigée : les vues privilégiées ne sont plus atteignables par un simple accès URL par un compte non habilité.
- Source de vérité serveur, auditable et évolutive (ajout futur de rôles, back-office).
- Fin de l'heuristique d'e-mail : plus de dépendance à un motif d'adresse.

**Négatives / points de vigilance**
- Le cloisonnement décrit est **côté frontend** (UX). Le durcissement de l'autorisation **côté API** (vérification du rôle sur chaque endpoint sensible, idéalement au niveau du gateway — voir ADR 0006, responsabilités futures) reste à formaliser : le rôle est aujourd'hui la source de vérité, mais son application par les services backend n'est pas encore généralisée.
- L'attribution d'un rôle non-client dépend du seed tant qu'aucun back-office administrateur n'existe.
