worker:
	docker compose up listener_devagent_worker

redis:
	docker compose up -d listener_redis

app:
	docker compose up -d --build listener_app 

down:
	docker compose down --remove-orphans --volumes

test:
	python -m unittest discover -s tests -p "*_test.py"

.PHONY: db
.PHONY: app
.PHONY: down
.PHONY: migrate
.PHONY: test
