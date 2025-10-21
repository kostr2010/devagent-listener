db:
	docker compose up -d listener_db

app:
	docker compose up -d --build listener_app

down:
	docker compose down --remove-orphans --volumes

migrate:
	alembic upgrade head

.PHONY: db
.PHONY: app
.PHONY: down
.PHONY: migrate