# Problème — Contrat frontend `Delivery` / `Courier` divergent du schéma backend

- **Date** : 2026-07-23
- **Branche** : `feat/rbac-role-views`
- **Composant** : frontend (`frontend/src/api/orders.ts`), service `deliveries`

## Symptôme

Le suivi de livraison côté frontend affichait des données incohérentes et, dans certains cas, **plantait le rendu React** au moment d'afficher une adresse de livraison.

## Contexte

Les types TypeScript `Delivery` et `Courier` définis dans `api/orders.ts` avaient été écrits **sans être alignés sur le schéma réel** exposé par le service `deliveries`. Plusieurs écarts se cumulaient.

## Cause racine

Divergences de contrat entre le frontend et le backend `deliveries` :

1. **Statut `ASSIGNED` inexistant** côté backend : le cycle de vie réel d'une livraison est `PROPOSED → ACCEPTED → PICKED_UP → DELIVERED`. Le frontend s'appuyait sur un statut `ASSIGNED` jamais émis.
2. **Adresses traitées comme des chaînes de caractères** alors que le backend renvoie des **objets** `{ label, lat, lng }`. Le rendu direct de l'objet comme texte provoquait un crash React (« objects are not valid as a React child »).
3. **Mauvais nom de champ** : le frontend lisait `delivery_address` là où le backend expose **`dropoff_address`**.
4. **`createCourier`** envoyait la position sous forme de champs `lat` / `lng` **à plat**, alors que le backend attend un objet imbriqué **`location: { lat, lng }`**.

## Résolution

- Alignement des types `Delivery` / `Courier` sur le schéma réel du service `deliveries`.
- Prise en compte du statut réel **`ACCEPTED`** (et du cycle complet `PROPOSED → ACCEPTED → PICKED_UP → DELIVERED`) à la place de `ASSIGNED`.
- **Formatage des adresses** : lecture du champ `dropoff_address` et rendu à partir de l'objet `{ label, lat, lng }` (affichage du `label`), plus jamais de rendu direct de l'objet.
- Correction de `createCourier` pour envoyer `location: { lat, lng }`.

## Prévention

- Générer / dériver les types frontend à partir du contrat OpenAPI des services plutôt que de les réécrire à la main (piste d'amélioration).
- Tester le rendu des composants de suivi de livraison avec des données conformes au schéma backend.
