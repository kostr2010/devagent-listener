worker:
	docker compose up listener_devagent_worker

redis:
	docker compose up -d listener_redis

app:
	docker compose up -d --build listener_app 

down:
	docker compose down --remove-orphans --volumes

.PHONY: db
.PHONY: app
.PHONY: down
.PHONY: migrate
