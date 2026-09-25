.DEFAULT_GOAL := help
MAKEFLAGS += --no-print-directory

COMPOSE_FILE := deploy/docker-compose/docker-compose.yml
DOCKER ?= docker
# DOCKER ?= podman
COMPOSE := $(DOCKER) compose -f $(COMPOSE_FILE)
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

# The chart's own workloads, as deployment name suffixes
HELM_WORKLOADS := app worker beat client

# k3d gets its own kubeconfig so creating the local cluster never rewrites (or
# switches the context of) a real cluster's kubeconfig via $KUBECONFIG
K3D_KUBECONFIG := $(CURDIR)/.k3d-kubeconfig.yaml

# PID/log files for the background port-forwards
PF_DIR := $(CURDIR)/.k3d-port-forward
PF_APP_PORT ?= 8000
PF_CLIENT_PORT ?= 8080

# The CNPG Cluster the chart creates (keep in sync with values.yaml cnpg.name)
CNPG_CLUSTER ?= marc-comparator-db
PG_DATABASE ?= marc

# PROFILE=1 grants the worker CAP_SYS_PTRACE so py-spy can attach to the pool.
# It is left off otherwise, and it replaces the worker pod when it changes.
PROFILE ?=
# SQLTRACE=1 makes the worker record the application stack behind every SQL
# statement (adapters.sql_tracing). Separate from PROFILE because the stack
# capture it adds to every query would skew a py-spy sample taken beside it.
SQLTRACE ?=
HELM_PROFILE_FLAGS := $(if $(PROFILE),--set worker.profiling=true,) \
                      $(if $(SQLTRACE),--set worker.sqlTrace=true,)

# CloudNativePG operator — provides the postgresql.cnpg.io CRDs the chart needs
CNPG_VERSION ?= 1.30.0
CNPG_MANIFEST := https://github.com/cloudnative-pg/cloudnative-pg/releases/download/v$(CNPG_VERSION)/cnpg-$(CNPG_VERSION).yaml

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
        k3d-up k3d-down k3d-load k3d-env \
        k3d-port-forward-up k3d-port-forward-down \
        cnpg-install cnpg-uninstall \
        helm-lint helm-template helm-install helm-uninstall helm-test helm-reload \
        profile-db-init profile-db-reset profile-db-report \
        profile-worker profile-worker-dump \
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

# Cluster-mutating targets talk to the local k3d cluster and ignore the caller's
# $KUBECONFIG, which otherwise silently aims them at whatever real cluster the
# shell is pointed at — and `kubectl apply` of the CNPG manifest does not merely
# install the operator there, it upgrades the one already running.
# ALLOW_REMOTE=1 opts out and uses the caller's context instead.
KUBE := $(if $(ALLOW_REMOTE),,env KUBECONFIG=$(K3D_KUBECONFIG))

define require_cluster
	@if [ -n "$(ALLOW_REMOTE)" ]; then \
		echo "→ ALLOW_REMOTE set — target context: $$(kubectl config current-context)"; \
	elif [ ! -f "$(K3D_KUBECONFIG)" ]; then \
		echo "REFUSING: no local cluster at $(K3D_KUBECONFIG)"; \
		echo "  create it first:          make k3d-up   (or: make helm-test)"; \
		echo "  deliberate remote change: ALLOW_REMOTE=1 make <target>"; \
		exit 1; \
	else \
		echo "→ target context: $$($(KUBE) kubectl config current-context) (local k3d cluster)"; \
	fi
endef

k3d-up: ## Create the local k3s cluster for Helm testing (reuses an existing one)
	@if k3d cluster list $(K3D_CLUSTER) >/dev/null 2>&1; then \
		echo "→ cluster '$(K3D_CLUSTER)' already exists — reusing it"; \
	else \
		k3d cluster create $(K3D_CLUSTER) --agents 1 --wait \
			--kubeconfig-update-default=false --kubeconfig-switch-context=false; \
	fi
	k3d kubeconfig get $(K3D_CLUSTER) > $(K3D_KUBECONFIG)
	@echo "→ cluster kubeconfig: $(K3D_KUBECONFIG)"
	@echo "  point a shell at it — fish: set -x KUBECONFIG (make k3d-env)"
	@echo "                    bash/zsh: export KUBECONFIG=\$$(make k3d-env)"

k3d-down: ## Delete the local k3s cluster
	k3d cluster delete $(K3D_CLUSTER)
	rm -f $(K3D_KUBECONFIG)

k3d-env: ## Print the local cluster's kubeconfig path (for $KUBECONFIG)
	@echo "$(K3D_KUBECONFIG)"

k3d-load: build ## Build images and import them into the k3d cluster
	k3d image import -c $(K3D_CLUSTER) $(APP_IMAGE) $(WORKER_IMAGE) $(CLIENT_IMAGE)

# $(call pf_start,name,service,local port,remote port) — backgrounded, PID recorded
define pf_start
	if [ -f $(PF_DIR)/$(1).pid ] && kill -0 $$(cat $(PF_DIR)/$(1).pid) 2>/dev/null; then \
		echo "→ $(1): already forwarded (pid $$(cat $(PF_DIR)/$(1).pid))"; \
	else \
		nohup $(KUBE) kubectl --namespace $(HELM_NAMESPACE) port-forward \
			svc/$(2) $(3):$(4) >$(PF_DIR)/$(1).log 2>&1 & \
		echo $$! >$(PF_DIR)/$(1).pid; \
		echo "→ $(1): http://localhost:$(3) → svc/$(2):$(4)"; \
	fi
endef

k3d-port-forward-up: ## Forward the app and client from the local cluster to localhost
	$(require_cluster)
	@mkdir -p $(PF_DIR)
	@$(call pf_start,app,$(HELM_RELEASE)-app,$(PF_APP_PORT),8000)
	@$(call pf_start,client,$(HELM_RELEASE)-client,$(PF_CLIENT_PORT),80)
	@echo "  logs in $(PF_DIR); stop with: make k3d-port-forward-down"

k3d-port-forward-down: ## Stop the port-forwards started by k3d-port-forward-up
	@for name in app client; do \
		pidfile=$(PF_DIR)/$$name.pid; \
		if [ ! -f $$pidfile ]; then \
			echo "→ $$name: nothing recorded"; \
		elif kill $$(cat $$pidfile) 2>/dev/null; then \
			echo "→ $$name: stopped (pid $$(cat $$pidfile))"; \
		else \
			echo "→ $$name: not running (stale pid $$(cat $$pidfile))"; \
		fi; \
		rm -f $$pidfile; \
	done

cnpg-install: ## Install the CloudNativePG operator into the local cluster
	$(require_cluster)
	$(KUBE) kubectl apply --server-side -f $(CNPG_MANIFEST)
	$(KUBE) kubectl wait --for=condition=Available deployment/cnpg-controller-manager \
		--namespace cnpg-system --timeout 5m

cnpg-uninstall: ## Remove the CloudNativePG operator
	$(require_cluster)
	$(KUBE) kubectl delete -f $(CNPG_MANIFEST) --ignore-not-found

helm-lint: ## Lint the Helm chart
	helm lint $(CHART_DIR)

helm-template: ## Render the chart templates locally (no cluster needed)
	helm template $(HELM_RELEASE) $(CHART_DIR)

helm-install: ## Install/upgrade the chart into the local cluster (ALLOW_REMOTE=1 for yours)
	$(require_cluster)
	$(KUBE) helm upgrade --install $(HELM_RELEASE) $(CHART_DIR) \
		--namespace $(HELM_NAMESPACE) --create-namespace \
		--set image.tag=$(VERSION) \
		$(HELM_PROFILE_FLAGS) \
		--wait --timeout 10m

helm-uninstall: ## Remove the release from the cluster
	$(require_cluster)
	$(KUBE) helm uninstall $(HELM_RELEASE) --namespace $(HELM_NAMESPACE)

helm-test: k3d-up k3d-load cnpg-install helm-install ## Full local test: cluster + operator + images + install

# Rebuilding under an unchanged VERSION renders a pod spec identical to the
# running one, so `helm upgrade` reports success and leaves the old containers
# in place — with pullPolicy IfNotPresent the new image is never picked up.
# The restart is what makes the rebuild take effect. Nothing here touches the
# CNPG cluster or its volume, so harvested data survives.
helm-reload: k3d-load helm-install ## Rebuild images and restart the workloads (keeps the database)
	@for w in $(HELM_WORKLOADS); do \
		$(KUBE) kubectl --namespace $(HELM_NAMESPACE) rollout restart deploy/$(HELM_RELEASE)-$$w; \
	done
	@for w in $(HELM_WORKLOADS); do \
		$(KUBE) kubectl --namespace $(HELM_NAMESPACE) rollout status deploy/$(HELM_RELEASE)-$$w --timeout=5m; \
	done

# ─── Profiling ───────────────────────────────────────────────────────────────

# Two instruments, because on this workload the time has repeatedly turned out
# to be in the database rather than in Python: pg_stat_statements attributes it
# to SQL across a whole run, py-spy attributes whatever is left to Python and
# native frames. Reach for the SQL one first.

PROFILE_SECONDS ?= 120
PROFILE_TOP ?= 25
PROFILE_OUT ?= $(CURDIR)/.profile
# flamegraph (an .svg to open), raw (folded stacks, for aggregating self time
# yourself), or speedscope. The SVG merges boxes by name, so it is good for
# seeing shape and bad for attributing cost — use raw when you need numbers.
PROFILE_FORMAT ?= flamegraph
PROFILE_EXT = $(if $(filter flamegraph,$(PROFILE_FORMAT)),svg,txt)

worker_pod = $$($(KUBE) kubectl --namespace $(HELM_NAMESPACE) get pod \
	-l app.kubernetes.io/component=worker \
	-o jsonpath='{.items[0].metadata.name}')

db_pod = $$($(KUBE) kubectl --namespace $(HELM_NAMESPACE) get pod \
	-l cnpg.io/cluster=$(CNPG_CLUSTER),cnpg.io/instanceRole=primary \
	-o jsonpath='{.items[0].metadata.name}')

# Percentages are of the total in the view, so they only mean anything when the
# counters were reset at the start of the run being measured.
define PROFILE_DB_QUERY
SELECT round((total_exec_time / 1000)::numeric, 1) AS total_s,
       round((100 * total_exec_time / nullif(sum(total_exec_time) OVER (), 0))::numeric, 1) AS pct,
       calls,
       round(mean_exec_time::numeric, 2) AS mean_ms,
       round((shared_blks_hit + shared_blks_read)::numeric / greatest(calls, 1), 0) AS blks_per_call,
       left(regexp_replace(query, '\s+', ' ', 'g'), 100) AS query
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT $(PROFILE_TOP);
endef
export PROFILE_DB_QUERY

# CNPG drops this extension once, during its startup reconciliation: after a
# restart the instance manager polls pg_extension in every database and issues
# DROP EXTENSION pg_stat_statements, because nothing declares that it should be
# there. It does not come back for it afterwards, so recreating it after the
# restart holds for the whole run. The counters live in shared memory and are
# lost on restart anyway, so reset creates it rather than trusting an earlier
# init to still hold.
profile-db-init: ## Create the pg_stat_statements extension
	$(require_cluster)
	@$(KUBE) kubectl --namespace $(HELM_NAMESPACE) exec -c postgres $(db_pod) -- \
		psql -U postgres -d $(PG_DATABASE) \
		-c 'CREATE EXTENSION IF NOT EXISTS pg_stat_statements;'

profile-db-reset: profile-db-init ## Zero the statement counters — run immediately before a measured run
	@$(KUBE) kubectl --namespace $(HELM_NAMESPACE) exec -c postgres $(db_pod) -- \
		psql -U postgres -d $(PG_DATABASE) -tAc 'SELECT pg_stat_statements_reset();' >/dev/null
	@echo "→ statement counters reset"

# Deliberately does not create the extension: if it is missing, the run being
# reported on straddled a database restart and the numbers are gone. An empty
# report would read as "nothing took any time".
profile-db-report: ## Statements from the local database, worst total time first
	$(require_cluster)
	@if ! $(KUBE) kubectl --namespace $(HELM_NAMESPACE) exec -c postgres $(db_pod) -- \
		psql -U postgres -d $(PG_DATABASE) -tAc \
		"SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'" | grep -q 1; then \
		echo "pg_stat_statements is not installed."; \
		echo "The database restarted since the last 'make profile-db-reset', which"; \
		echo "takes the counters with it. Reset again and re-run the task."; \
		exit 1; \
	fi
	@$(KUBE) kubectl --namespace $(HELM_NAMESPACE) exec -c postgres $(db_pod) -- \
		psql -U postgres -d $(PG_DATABASE) -P pager=off -c "$$PROFILE_DB_QUERY"

# py-spy is fetched on this machine and copied into the pod, not installed from
# inside it: the worker has no route to PyPI, and the shipped image is better
# off carrying no profiler at all. The copy is lost when the pod is replaced.
PY_SPY_BIN := $(PROFILE_OUT)/bin/py-spy

$(PY_SPY_BIN):
	@mkdir -p $(PROFILE_OUT)/bin
	$(UV) venv --quiet $(PROFILE_OUT)/venv
	$(UV) pip install --quiet --python $(PROFILE_OUT)/venv py-spy
	@cp $(PROFILE_OUT)/venv/bin/py-spy $@

define py_spy_present
	$(KUBE) kubectl --namespace $(HELM_NAMESPACE) exec $$pod -- test -x /tmp/py-spy \
		2>/dev/null \
		|| $(KUBE) kubectl --namespace $(HELM_NAMESPACE) cp \
			$(PY_SPY_BIN) $(HELM_NAMESPACE)/$$pod:/tmp/py-spy
endef

profile-worker: $(PY_SPY_BIN) ## Record a py-spy flamegraph of the worker (PROFILE_SECONDS=120)
	$(require_cluster)
	@mkdir -p $(PROFILE_OUT)
	@pod=$(worker_pod); \
	out=worker-$$(date +%Y%m%d-%H%M%S).$(PROFILE_EXT); \
	echo "→ sampling $$pod for $(PROFILE_SECONDS)s"; \
	$(py_spy_present); \
	$(KUBE) kubectl --namespace $(HELM_NAMESPACE) exec $$pod -- \
		/tmp/py-spy record --pid 1 --subprocesses --duration $(PROFILE_SECONDS) \
		--rate 100 --format $(PROFILE_FORMAT) --output /tmp/$$out; \
	$(KUBE) kubectl --namespace $(HELM_NAMESPACE) cp \
		$(HELM_NAMESPACE)/$$pod:/tmp/$$out $(PROFILE_OUT)/$$out; \
	echo "→ $(PROFILE_OUT)/$$out"

profile-worker-dump: $(PY_SPY_BIN) ## Print what every worker process is doing right now
	$(require_cluster)
	@pod=$(worker_pod); \
	$(py_spy_present); \
	$(KUBE) kubectl --namespace $(HELM_NAMESPACE) exec $$pod -- \
		/tmp/py-spy dump --pid 1 --subprocesses

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
