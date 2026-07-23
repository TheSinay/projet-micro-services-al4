# 2026-07-06 — Initialisation du projet

- Mise en place de la structure du dépôt (services/, frontend/, documentation/, .claude/).
- Création des 5 agents Claude Code : planificateur, dev-back, dev-front, testeur, documentaliste.
- Rédaction des règles globales (`CLAUDE.md`) et de la stack technique autorisée.
- **ADR 0001** : stratégie de découpe microservices par charge (accepté).
- Ajout du `Makefile` (test, lint, run, build) et du `docker-compose.yml` (Redis initial).
- Hooks Claude Code configurés pour lancer lint/test après modification de fichiers.

**Aucun service métier ni écran frontend n'est encore défini** — en attente de la première demande fonctionnelle, qui sera traitée par le planificateur.
