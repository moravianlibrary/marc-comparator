.DEFAULT_GOAL := help
MAKEFLAGS += --no-print-directory

COMPOSE_FILE := deploy/docker-compose/docker-compose.yml
COMPOSE := docker compose -f $(COMPOSE_FILE)
DOCKER ?= $(shell command -v podman 2>/dev/null || command -v docker 2>/dev/null)
VERSION := $(shell cat VERSION)

# PEP 440 form of VERSION for Python manifests (1.0.0-rc6 -> 1.0.0rc6)
PY_VERSION := $(subst -,,$(VERSION))

REGISTRY ?=

REG_PREFIX := $(if $(REGISTRY),$(REGISTRY)/,)
APP_IMAGE := $(REG_PREFIX)marc-comparator-app:$(VERSION)
WORKER_IMAGE := $(REG_PREFIX)marc-comparator-worker:$(VERSION)
CLIENT_IMAGE := $(REG_PREFIX)marc-comparator-client:$(VERSION)

SYSTEM_VERSION := $(VERSION)
SYSTEM_COMMIT := $(shell git rev-parse --short HEAD 2>/dev/null)

# ─── Python (uv) ─────────────────────────────────────────────────────────────

UV ?= uv
SDK_VENV := sdk/.venv
APP_VENV := app/.venv
APP_TEST_TARGET ?= not _smoke

# requirements*.txt are generated from uv.lock for the container builds, which
# install with pip. The SDK itself is excluded — the images `pip install /sdk/`.
UV_EXPORT_FLAGS := --no-dev --no-hashes --no-emit-project \
                   --no-emit-package marc-comparator-sdk --format requirements-txt

# ─── Client (bun) ────────────────────────────────────────────────────────────

BUN ?= bun

# ─── Helm / local k3s ────────────────────────────────────────────────────────

CHART_DIR := deploy/helm/marc-comparator
K3D_CLUSTER ?= marc-comparator
HELM_RELEASE ?= marc-comparator
HELM_NAMESPACE ?= marc-comparator

.PHONY: help \
        build push build-push \
        up down restart logs \
        logs-app logs-worker logs-client logs-db \
        up-infra dev-client \
        open-client open-api \
        psql \
        sdk-env sdk-env-clean sdk-env-reset \
        app-env app-env-clean app-env-reset \
        deps-export deps-check \
        format format-check lint lint-fix typecheck version-check check \
        set-version tag-version tag-latest release \
        k3d-up k3d-down k3d-load \
        helm-lint helm-template helm-install helm-uninstall helm-test \
        test test-integration test-integration-verbose coverage-report \
        dev-sdk dev-app dev-worker dev-beat \
        db-migrate db-upgrade db-downgrade db-history \
        clean clean-images clean-volumes clean-all

# ─── Help ────────────────────────────────────────────────────────────────────

help: ## Show this help
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-26s\033[0m %s\n", $$1, $$2}'

# ─── Quality ─────────────────────────────────────────────────────────────────

format: ## Format all code (Python + client)
	$(UV) run --directory app ruff format . ../sdk
	cd client && $(BUN) run format

format-check: ## Check formatting without writing
	$(UV) run --directory app ruff format --check . ../sdk
	cd client && $(BUN) run format:check

lint: ## Lint all code
	$(UV) run --directory app ruff check . ../sdk
	cd client && $(BUN) run lint

lint-fix: ## Lint and apply safe fixes
	$(UV) run --directory app ruff check --fix . ../sdk
	cd client && $(BUN) run lint:fix

typecheck: ## Type-check Python (basedpyright) and client (tsc)
	$(UV) run --directory app basedpyright
	cd client && $(BUN) run typecheck

version-check: ## Fail if VERSION drifted from the manifests that embed it
	@app_v=$$(grep -m1 '^version = ' app/pyproject.toml | sed 's/.*"\(.*\)".*/\1/'); \
	chart_v=$$(grep -m1 '^appVersion:' $(CHART_DIR)/Chart.yaml | sed 's/.*"\(.*\)".*/\1/'); \
	fail=0; \
	if [ "$$app_v" != "$(PY_VERSION)" ]; then \
		echo "VERSION drift: app/pyproject.toml is $$app_v, expected $(PY_VERSION)"; fail=1; fi; \
	if [ "$$chart_v" != "$(VERSION)" ]; then \
		echo "VERSION drift: Chart.yaml appVersion is $$chart_v, expected $(VERSION)"; fail=1; fi; \
	[ $$fail -eq 0 ] && echo "VERSION $(VERSION) consistent across manifests"; \
	exit $$fail

deps-check: ## Fail if requirements*.txt drifted from uv.lock
	@tmp=$$(mktemp -d); \
	(cd app && $(UV) export $(UV_EXPORT_FLAGS) --extra api) > $$tmp/app.txt 2>/dev/null; \
	(cd app && $(UV) export $(UV_EXPORT_FLAGS) --extra worker) > $$tmp/worker.txt 2>/dev/null; \
	fail=0; \
	diff -q $$tmp/app.txt app/requirements.app.txt >/dev/null || \
		{ echo "app/requirements.app.txt is stale — run 'make deps-export'"; fail=1; }; \
	diff -q $$tmp/worker.txt app/requirements.worker.txt >/dev/null || \
		{ echo "app/requirements.worker.txt is stale — run 'make deps-export'"; fail=1; }; \
	rm -rf $$tmp; \
	[ $$fail -eq 0 ] && echo "requirements*.txt in sync with uv.lock"; \
	exit $$fail

check: version-check deps-check format-check lint typecheck helm-lint ## Run the full quality gate

# ─── Release ─────────────────────────────────────────────────────────────────

set-version: ## Set the version everywhere (usage: make set-version VERSION=1.2.3)
	$(if $(VERSION),,$(error VERSION is required))
	@echo "$(VERSION)" > VERSION
	@sed -i 's/^version = ".*"/version = "$(PY_VERSION)"/' app/pyproject.toml
	@sed -i 's/^appVersion: .*/appVersion: "$(VERSION)"/' $(CHART_DIR)/Chart.yaml
	@echo "Version set to $(VERSION) (Python manifests: $(PY_VERSION))"

tag-version: ## Force-retag v$(VERSION) locally and on the remote
	-git tag -d v$(VERSION)
	-git push origin :refs/tags/v$(VERSION)
	git tag v$(VERSION)
	git push origin v$(VERSION)

tag-latest: ## Force-move the latest tag to HEAD
	-git tag -d latest
	-git push origin :refs/tags/latest
	git tag latest
	git push origin latest

release: build-push tag-version tag-latest ## Build+push images and move the git tags

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

# ─── Local Helm testing (k3s via k3d) ────────────────────────────────────────

k3d-up: ## Create the local k3s cluster for Helm testing
	k3d cluster create $(K3D_CLUSTER) --agents 1 --wait

k3d-down: ## Delete the local k3s cluster
	k3d cluster delete $(K3D_CLUSTER)

k3d-load: build ## Build images and import them into the k3d cluster
	k3d image import -c $(K3D_CLUSTER) $(APP_IMAGE) $(WORKER_IMAGE) $(CLIENT_IMAGE)

helm-lint: ## Lint the Helm chart
	helm lint $(CHART_DIR)

helm-template: ## Render the chart templates locally (no cluster needed)
	helm template $(HELM_RELEASE) $(CHART_DIR)

helm-install: ## Install/upgrade the chart into the current kube context
	helm upgrade --install $(HELM_RELEASE) $(CHART_DIR) \
		--namespace $(HELM_NAMESPACE) --create-namespace \
		--wait --timeout 10m

helm-uninstall: ## Remove the release from the cluster
	helm uninstall $(HELM_RELEASE) --namespace $(HELM_NAMESPACE)

helm-test: k3d-up k3d-load helm-install ## Full local test: cluster + images + install

# ─── Dev mode (backend in Docker, client local with HMR) ─────────────────────

up-infra: ## Start everything except client (for local frontend dev)
	TAG=$(VERSION) $(COMPOSE) up -d postgres redis ollama app worker

dev-client: ## Start frontend in dev mode (Vite HMR)
	cd client && $(BUN) run dev

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
	cd sdk && $(UV) sync

sdk-env-clean: ## Remove SDK virtualenv
	rm -rf $(SDK_VENV)

sdk-env-reset: sdk-env-clean sdk-env ## Recreate SDK virtualenv

app-env: ## Create app virtualenv and install dependencies (incl. SDK, editable)
	cd app && $(UV) sync --all-extras

app-env-clean: ## Remove app virtualenv
	rm -rf $(APP_VENV)

app-env-reset: app-env-clean app-env ## Recreate app virtualenv

deps-export: ## Regenerate requirements*.txt from uv.lock (for the container builds)
	cd app && $(UV) export $(UV_EXPORT_FLAGS) --extra api > requirements.app.txt
	cd app && $(UV) export $(UV_EXPORT_FLAGS) --extra worker > requirements.worker.txt

# ─── Tests ───────────────────────────────────────────────────────────────────

test: ## Run all app tests with coverage
	cd app && PYTHONPATH=. $(UV) run coverage run -m pytest tests \
		&& $(UV) run coverage html \
		&& $(UV) run coverage report

test-integration: ## Run integration tests (filter with APP_TEST_TARGET=...)
	cd app && PYTHONPATH=. $(UV) run coverage run -m pytest tests/integration -k "$(APP_TEST_TARGET)" \
		&& $(UV) run coverage html \
		&& $(UV) run coverage report

test-integration-verbose: ## Run integration tests with verbose output
	cd app && PYTHONPATH=. $(UV) run pytest -s -vv tests/integration -k "$(APP_TEST_TARGET)"

coverage-report: ## Open coverage report in browser
	xdg-open app/htmlcov/index.html &

# ─── Local dev (no Docker) ───────────────────────────────────────────────────

dev-sdk: ## Re-sync the app env (the SDK is an editable path dependency)
	cd app && $(UV) sync --all-extras

dev-app: ## Start FastAPI app locally (requires infra services)
	cd app && PYTHONPATH=. $(UV) run uvicorn app:app --reload --host 127.0.0.1 --port 8000

dev-worker: ## Start Celery worker locally (requires infra services)
	cd app && PYTHONPATH=. $(UV) run celery -A adapters.tasks worker --loglevel=info

dev-beat: ## Start Celery Beat locally with redbeat scheduler
	cd app && PYTHONPATH=. $(UV) run celery -A adapters.tasks beat -S redbeat.RedBeatScheduler --loglevel=info

# ─── Database migrations (Alembic) ───────────────────────────────────────────

ALEMBIC := cd app && set -a && . ../deploy/docker-compose/app.env && set +a && POSTGRES_HOST=localhost PYTHONPATH=. $(UV) run alembic

db-migrate: ## Generate a new migration (usage: make db-migrate MSG="add foo column")
	$(ALEMBIC) revision --autogenerate -m "$(MSG)"

db-upgrade: ## Apply all pending migrations (or specify REV=<revision>)
	$(ALEMBIC) upgrade $(or $(REV),head)

db-downgrade: ## Revert last migration (or specify REV=<revision>)
	$(ALEMBIC) downgrade $(or $(REV),-1)

db-history: ## Show migration history
	$(ALEMBIC) history --verbose

# ─── Cleanup ─────────────────────────────────────────────────────────────────

clean: down ## Stop services and remove containers
	$(COMPOSE) rm -f

clean-images: ## Remove built images
	$(COMPOSE) down --rmi local

clean-volumes: ## Remove all volumes (destroys data)
	$(COMPOSE) down -v

clean-all: clean-images clean-volumes sdk-env-clean app-env-clean ## Remove everything (images, volumes, venvs)
