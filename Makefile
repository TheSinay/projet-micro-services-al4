# Makefile — commandes transverses du projet microservices.
# Itère sur chaque service backend (services/*) et sur le frontend.

SERVICES := $(wildcard services/*)
FRONTEND := frontend

.DEFAULT_GOAL := help

.PHONY: help test lint run build test-back lint-back test-front lint-front

help: ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

## --- Agrégats ---
test: test-back test-front ## Lance tous les tests (back + front)

lint: lint-back lint-front ## Lint + typage (back + front)

## --- Backend ---
test-back: ## Tests pytest de chaque service backend (couverture)
	@for svc in $(SERVICES); do \
		echo ">> pytest $$svc"; \
		( cd $$svc && pytest --cov --cov-report=term-missing ) || exit 1; \
	done

lint-back: ## ruff + mypy sur chaque service backend
	@for svc in $(SERVICES); do \
		echo ">> lint $$svc"; \
		( cd $$svc && ruff check . && ruff format --check . && mypy . ) || exit 1; \
	done

## --- Frontend ---
test-front: ## Tests Vitest du frontend
	@if [ -f $(FRONTEND)/package.json ]; then cd $(FRONTEND) && npm run test; fi

lint-front: ## ESLint + Prettier du frontend
	@if [ -f $(FRONTEND)/package.json ]; then cd $(FRONTEND) && npm run lint && npm run format:check; fi

## --- Exécution / build ---
run: ## Démarre toute la stack via docker-compose
	docker compose up --build

build: ## Construit toutes les images Docker
	docker compose build
