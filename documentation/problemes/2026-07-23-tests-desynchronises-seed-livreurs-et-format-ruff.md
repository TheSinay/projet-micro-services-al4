# Problème — Tests désynchronisés (seed livreurs) et dette de format Ruff

- **Date** : 2026-07-23
- **Branche** : `feat/rbac-role-views`
- **Composant** : services `deliveries` et `restaurants` (tests)

Deux problèmes de la chaîne de tests / lint, indépendants mais corrigés dans la même branche.

## 1. Test de seed livreurs désynchronisé

### Symptôme
Le test `test_seed_populates_three_couriers_one_unavailable` échouait.

### Cause racine
Le test (et sa docstring) attendaient **3 livreurs dont 1 indisponible**. Or le commit `650e71d` a porté la **flotte de démonstration à 4 livreurs, tous disponibles** (pour garantir qu'un livreur soit toujours affectable dans les scénarios de démo). Le test n'avait pas été mis à jour en même temps que le seed : c'est le **test qui était périmé**, pas le code.

### Résolution
Mise à jour du test et de sa docstring pour refléter l'état réel du seed (4 livreurs, tous disponibles).

### Prévention
Traiter le seed de démonstration et ses tests comme un couple : toute modification de la flotte de seed doit s'accompagner de la mise à jour des assertions correspondantes dans le même commit.

## 2. Dette de format Ruff préexistante

### Symptôme
`make lint` échouait sur `services/restaurants/tests/test_restaurants.py`.

### Cause racine
Ce fichier de tests **n'avait jamais été formaté par Ruff** et contenait des écarts de format ; la dette était **préexistante** à cette branche et cassait la cible `make lint`.

### Résolution
Reformatage du fichier avec Ruff.

### Prévention
S'assurer que `ruff format` couvre bien les répertoires de tests et que la vérification passe en intégration avant merge dans `qa` (voir dette ouverte sur l'automatisation de la qualité).
