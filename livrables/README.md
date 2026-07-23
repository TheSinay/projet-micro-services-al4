# 📦 DOSSIER DES LIVRABLES OFFICIELS — FITMEAL / MIAMGO

> **Projet Architecture Microservices — Plateforme de Livraison de Repas**  
> Dépôt officiel des livrables de conception, diagrammes, contrats d'API et support de présentation.

---

## 📋 Table des Livrables Organisés

Ce dossier réunit l'intégralité des livrables exigés par le sujet ([enonce.md](../enonce.md)) pour l'évaluation et la soutenance :

| Document | Titre & Description | Liens Directs |
|---|---|---|
| 📑 **Livrable 1** | **Documentation d'Architecture**<br>*Description générale, analyse DDD, découpe par charge, SAGA, résilience & principes.* | [1_documentation_architecture.md](1_documentation_architecture.md) |
| 📐 **Livrable 2** | **Diagrammes Techniques (C4 & Séquences)**<br>*Diagrammes C4 Niveau 1 & 2, Séquence SAGA Nominale, Résilience Circuit Breaker, Compensations & ERD.* | [2_diagrammes_architecture.md](2_diagrammes_architecture.md) |
| 📜 **Livrable 3** | **Spécifications & Contrats d'API REST**<br>*Contrats OpenAPI 3.0 normalisés pour l'ensemble des 6 microservices.* | [3_contrats_api_openapi.md](3_contrats_api_openapi.md) |
| 🎬 **Livrable 4** | **Support de Présentation (Slides & Démo)**<br>*Diaporama complet (Marp/Markdown), script d'oral 15 min, scénario de démo live & Q&R Jury.* | [4_slides_presentation.md](4_slides_presentation.md) |
| 🏛️ **Livrable 5** | **Recueil des Décisions d'Architecture (ADRs)**<br>*Compilation intégrale des ADRs 0001 à 0011 formalisant chaque choix technique.* | [5_recueil_decisions_adr.md](5_recueil_decisions_adr.md) |

---

## ⚡ Résumé Rapide de l'Architecture & du Prototype

- **Microservices FastAPI** (6 services autonomes : `users`, `restaurants`, `orders`, `payments`, `deliveries`, `notifications`).
- **API Gateway Nginx** (Routage centralisé `/api/v1/*`, CORS, traçabilité `X-Correlation-Id`).
- **Bus Redis Pub/Sub & Caching** (Chorégraphie événementielle, panier & gestion d'état SAGA).
- **Frontend React 18 / TypeScript / Vite** (Vues dédiées par rôle : Client, Restaurateur, Livreur et Dashboard QA).
- **Résilience & Fault Tolerance** : Circuit Breaker (5 échecs ➔ OPEN), Retry x3 avec backoff exponentiel, Timeouts (2s) et Idempotence paiements.

---

## 🛠️ Exécution Rapide du Prototype

```bash
# Démarrage de l'infrastructure Docker Compose
docker compose up --build

# Exécution de la suite de tests automatisés (300+ tests backend + frontend)
make test
```

- **Frontend & Dashboard QA** : `http://localhost` (ou `http://localhost:5173`)
- **Documentation API Interactive (Swagger)** :
  - Users: `http://localhost:8001/docs`
  - Restaurants: `http://localhost:8002/docs`
  - Orders: `http://localhost:8003/docs`
  - Payments: `http://localhost:8004/docs`
  - Deliveries: `http://localhost:8005/docs`
  - Notifications: `http://localhost:8006/docs`
