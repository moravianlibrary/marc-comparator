start:
	docker compose up -d

stop:
	docker compose down

restart: stop start

build:
	docker compose build

rebuild: stop build start

psql:
	docker container exec -it marc-comparator-postgres-1 psql -d marc -U marcAdmin
