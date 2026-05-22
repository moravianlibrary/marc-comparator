COMPOSE_FILE := deploy/docker-compose/docker-compose.yml
COMPOSE := docker compose -f $(COMPOSE_FILE)
DOCKER ?= $(shell which podman 2>/dev/null || which docker 2>/dev/null)
VERSION := $(shell cat VERSION)

REGISTRY ?=

REG_PREFIX := $(if $(REGISTRY),$(REGISTRY)/,)
APP_IMAGE := $(REG_PREFIX)marc-comparator-app:$(VERSION)
WORKER_IMAGE := $(REG_PREFIX)marc-comparator-worker:$(VERSION)
CLIENT_IMAGE := $(REG_PREFIX)marc-comparator-client:$(VERSION)

SYSTEM_VERSION := $(VERSION)
SYSTEM_COMMIT := $(shell git rev-parse --short HEAD 2>/dev/null)

# Python
PYTHON_BASE := python3.12
SDK_VENV := sdk/.venv
SDK_PIP := $(SDK_VENV)/bin/pip
APP_VENV := app/.venv
APP_PYTHON := $(APP_VENV)/bin/python
APP_PIP := $(APP_VENV)/bin/pip
APP_TEST_LIBS := coverage testcontainers mypy pytest pytest-asyncio pytest_mock
APP_TEST_DIR := app/tests
APP_TEST_TARGET ?= not _smoke

.PHONY: help \
        build push build-push \
        up down restart logs \
        logs-app logs-worker logs-client logs-db \
        up-infra dev-client \
        open-client open-api \
        psql \
        sdk-env sdk-env-clean sdk-env-reset \
        app-env app-env-clean app-env-reset \
        test test-integration test-integration-verbose coverage-report \
        dev-sdk dev-app dev-worker dev-beat \
        clean clean-images clean-volumes clean-all

# ─── Help ────────────────────────────────────────────────────────────────────

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-26s\033[0m %s\n", $$1, $$2}'

# ─── Build images ────────────────────────────────────────────────────────────

build: ## Build all container images
	$(DOCKER) build \
		--build-arg SYSTEM_VERSION=$(SYSTEM_VERSION) \
		--build-arg SYSTEM_COMMIT=$(SYSTEM_COMMIT) \
		-t $(APP_IMAGE) \
		-f app/app.Containerfile .
	$(DOCKER) build -t $(WORKER_IMAGE) -f app/worker.Containerfile .
	$(DOCKER) build -t $(CLIENT_IMAGE) -f client/Containerfile client/

push: ## Push images to registry (requires REGISTRY=...)
	$(if $(REGISTRY),,$(error REGISTRY is required for push target))
	$(DOCKER) push $(APP_IMAGE)
	$(DOCKER) push $(WORKER_IMAGE)
	$(DOCKER) push $(CLIENT_IMAGE)

build-push: build push ## Build and push all images

# ─── Container targets ───────────────────────────────────────────────────────

up: ## Start all services
	TAG=$(VERSION) $(COMPOSE) up -d

down: ## Stop all services
	$(COMPOSE) down

restart: down up ## Restart all services

logs: ## Tail logs from all services
	$(COMPOSE) logs -f

logs-app: ## Tail app (API) logs
	$(COMPOSE) logs -f app

logs-worker: ## Tail worker logs
	$(COMPOSE) logs -f worker

logs-client: ## Tail client (frontend) logs
	$(COMPOSE) logs -f client

logs-db: ## Tail database logs
	$(COMPOSE) logs -f postgres

# ─── Dev mode (backend in Docker, client local with HMR) ─────────────────────

up-infra: ## Start everything except client (for local frontend dev)
	TAG=$(VERSION) $(COMPOSE) up -d postgres redis ollama app worker

dev-client: ## Start frontend in dev mode (Vite HMR)
	cd client && npm run dev

# ─── Open in browser ─────────────────────────────────────────────────────────

open-client: ## Open frontend in browser
	xdg-open http://localhost:8080

open-api: ## Open API docs in browser
	xdg-open http://localhost:8000/docs

# ─── Database ────────────────────────────────────────────────────────────────

psql: ## Open psql shell in Postgres container
	docker container exec -it marc-comparator-postgres psql -d marc -U marcAdmin

# ─── Python environments ─────────────────────────────────────────────────────

sdk-env: ## Create SDK virtualenv and install dependencies
	$(PYTHON_BASE) -m venv $(SDK_VENV)
	$(SDK_PIP) install --upgrade pip
	$(SDK_PIP) install -r sdk/requirements.txt

sdk-env-clean: ## Remove SDK virtualenv
	rm -rf $(SDK_VENV)

sdk-env-reset: sdk-env-clean sdk-env ## Recreate SDK virtualenv

app-env: ## Create app virtualenv and install dependencies
	$(PYTHON_BASE) -m venv $(APP_VENV)
	$(APP_PIP) install --upgrade pip
	$(APP_PIP) install -e sdk/
	$(APP_PIP) install -r app/requirements.app.txt -r app/requirements.worker.txt
	$(APP_PIP) install $(APP_TEST_LIBS)

app-env-clean: ## Remove app virtualenv
	rm -rf $(APP_VENV)

app-env-reset: app-env-clean app-env ## Recreate app virtualenv

# ─── Tests ───────────────────────────────────────────────────────────────────

test: ## Run all app tests with coverage
	cd app && PYTHONPATH=. $(abspath $(APP_PYTHON)) -m coverage run -m pytest discover -s tests \
		&& $(abspath $(APP_PYTHON)) -m coverage html \
		&& $(abspath $(APP_PYTHON)) -m coverage report

test-integration: ## Run integration tests (filter with APP_TEST_TARGET=...)
	cd app && PYTHONPATH=. $(abspath $(APP_PYTHON)) -m coverage run -m pytest tests/integration -k "$(APP_TEST_TARGET)" \
		&& $(abspath $(APP_PYTHON)) -m coverage html \
		&& $(abspath $(APP_PYTHON)) -m coverage report

test-integration-verbose: ## Run integration tests with verbose output
	cd app && PYTHONPATH=. $(abspath $(APP_PYTHON)) -m pytest -s -vv tests/integration -k "$(APP_TEST_TARGET)"

coverage-report: ## Open coverage report in browser
	xdg-open app/htmlcov/index.html &

# ─── Local dev (no Docker) ───────────────────────────────────────────────────

dev-sdk: ## Install SDK in editable mode (into app venv)
	$(APP_PIP) install -e sdk/

dev-app: ## Start FastAPI app locally (requires infra services)
	cd app && PYTHONPATH=. $(abspath $(APP_PYTHON)) -m uvicorn app:app --reload --host 127.0.0.1 --port 8000

dev-worker: ## Start Celery worker locally (requires infra services)
	cd app && PYTHONPATH=. $(abspath $(APP_PYTHON)) -m celery -A adapters.tasks worker --loglevel=info

dev-beat: ## Start Celery Beat locally with redbeat scheduler
	cd app && PYTHONPATH=. $(abspath $(APP_PYTHON)) -m celery -A adapters.tasks beat -S redbeat.RedBeatScheduler --loglevel=info

# ─── Cleanup ─────────────────────────────────────────────────────────────────

clean: down ## Stop services and remove containers
	$(COMPOSE) rm -f

clean-images: ## Remove built images
	$(COMPOSE) down --rmi local

clean-volumes: ## Remove all volumes (destroys data)
	$(COMPOSE) down -v

clean-all: clean-images clean-volumes sdk-env-clean app-env-clean ## Remove everything (images, volumes, venvs)
