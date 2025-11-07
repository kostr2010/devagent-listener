VENV = .venv
VENV_SYMLINK = venv # to ensure correct work of the IDEs
VENV_PYTHON = $(VENV)/bin/python
SYSTEM_PYTHON = $(or $(shell which python3.11), $(shell which python))
PYTHON = $(or $(wildcard $(VENV_PYTHON)), $(SYSTEM_PYTHON))

worker:
	docker compose up listener_devagent_worker

worker_active:
	docker exec devagent_listener_devagent_worker celery -A app.devagent.worker.devagent_worker inspect active

worker_logs:
	docker logs devagent_listener_devagent_worker

worker_logs_f:
	docker logs devagent_listener_devagent_worker -f

redis:
	docker compose up -d listener_redis

redis_logs:
	docker logs devagent_listener_redis

redis_logs_f:
	docker logs devagent_listener_redis -f

postgres:
	docker compose up -d listener_postgres

app:
	docker compose up -d --build listener_app 

app_no_deps:
	docker compose up -d --no-deps --build listener_app 

app_logs:
	docker logs devagent_listener_app

app_logs_f:
	docker logs devagent_listener_app -f

down:
	docker compose rm -s -v -f listener_app
	docker compose rm -s -v -f listener_devagent_worker
	docker compose rm -s -v -f listener_redis
	docker compose rm -s -v -f listener_postgres

test:
	$(PYTHON) -m unittest discover -v -s tests -p "*_test.py"

mypy:
	MYPYPATH=. mypy . --explicit-package-bases

tests_full:
	make test
	make mypy

venv:
	rm -rf $(VENV) $(VENV_SYMLINK)
	$(SYSTEM_PYTHON) -m venv $(VENV)
	$(VENV_PYTHON) -m pip install -r requirements.txt
	ln -s $(VENV) $(VENV_SYMLINK)

.PHONY: worker
.PHONY: worker_active
.PHONY: worker_logs
.PHONY: worker_logs_f
.PHONY: redis
.PHONY: redis_logs
.PHONY: redis_logs_f
.PHONY: postgres
.PHONY: app
.PHONY: app_no_deps
.PHONY: app_logs
.PHONY: app_logs_f
.PHONY: down
.PHONY: migrate
.PHONY: test
.PHONY: mypy
.PHONY: tests_full
.PHONY: venv
