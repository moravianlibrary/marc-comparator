COMPOSE_FILE := deploy/docker-compose/docker-compose.yml
DOCKER ?= $(shell which podman 2>/dev/null || which docker 2>/dev/null)
VERSION := $(shell cat VERSION)

REGISTRY ?=

REG_PREFIX := $(if $(REGISTRY),$(REGISTRY)/,)
APP_IMAGE := $(REG_PREFIX)marc-comparator-app:$(VERSION)
WORKER_IMAGE := $(REG_PREFIX)marc-comparator-worker:$(VERSION)
CLIENT_IMAGE := $(REG_PREFIX)marc-comparator-client:$(VERSION)

SYSTEM_VERSION := $(VERSION)
SYSTEM_COMMIT := $(shell git rev-parse --short HEAD 2>/dev/null)

# ------------------------------
# Build Images
# ------------------------------
build:
	$(DOCKER) build \
		--build-arg SYSTEM_VERSION=$(SYSTEM_VERSION) \
		--build-arg SYSTEM_COMMIT=$(SYSTEM_COMMIT) \
		-t $(APP_IMAGE) \
		-f app/app.Containerfile .
	$(DOCKER) build -t $(WORKER_IMAGE) -f app/worker.Containerfile .
	$(DOCKER) build -t $(CLIENT_IMAGE) -f client/Containerfile client/

# ------------------------------
# Push Images
# ------------------------------
push:
	$(if $(REGISTRY),,$(error REGISTRY is required for push target))
	$(DOCKER) push $(APP_IMAGE)
	$(DOCKER) push $(WORKER_IMAGE)
	$(DOCKER) push $(CLIENT_IMAGE)

build-push: build push

# ------------------------------
# Local Development
# ------------------------------
start:
	TAG=$(VERSION) $(DOCKER) compose -f $(COMPOSE_FILE) up -d

stop:
	$(DOCKER) compose -f $(COMPOSE_FILE) down

restart: stop start

rebuild: stop build start

restart-clean:
	$(DOCKER) compose -f $(COMPOSE_FILE) down -v
	TAG=$(VERSION) $(DOCKER) compose -f $(COMPOSE_FILE) up -d

rebuild-clean:
	$(DOCKER) compose -f $(COMPOSE_FILE) down -v
	$(MAKE) build
	TAG=$(VERSION) $(DOCKER) compose -f $(COMPOSE_FILE) up -d

# ------------------------------
# Postgres Shell
# ------------------------------
psql:
	docker container exec -it marc-comparator-postgres psql -d marc -U marcAdmin
