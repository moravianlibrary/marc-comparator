COMPOSE_FILE := deploy/docker-compose/docker-compose.yml
TAG ?= local

build:
	docker build -t marc-comparator-app:$(TAG) -f app/app.Containerfile .
	docker build -t marc-comparator-worker:$(TAG) -f app/worker.Containerfile .

start:
	docker compose -f $(COMPOSE_FILE) up -d

stop:
	docker compose -f $(COMPOSE_FILE) down

restart: stop start

rebuild: stop build start

restart-clean:
	docker compose -f $(COMPOSE_FILE) down -v
	docker compose -f $(COMPOSE_FILE) up -d

psql:
	docker container exec -it marc-comparator-postgres-1 psql -d marc -U marcAdmin
