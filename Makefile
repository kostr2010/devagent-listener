VENV = .venv
VENV_SYMLINK = venv # to ensure correct work of the IDEs
VENV_PYTHON = $(VENV)/bin/python
SYSTEM_PYTHON = $(or $(shell which python3.11), $(shell which python3))
PYTHON = $(or $(wildcard $(VENV_PYTHON)), $(SYSTEM_PYTHON))

worker:
	docker compose up listener_devagent_worker
.PHONY: worker

worker_down:
	docker compose rm -s -v -f listener_devagent_worker
.PHONY: worker_down

worker_active:
	docker exec devagent_listener_devagent_worker celery -A app.devagent.worker.devagent_worker inspect active
.PHONY: worker_active

worker_logs:
	docker logs devagent_listener_devagent_worker
.PHONY: worker_logs

worker_logs_f:
	docker logs devagent_listener_devagent_worker -f
.PHONY: worker_logs_f

redis:
	docker compose up -d listener_redis
.PHONY: redis

redis_down:
	docker compose rm -s -v -f listener_redis
.PHONY: redis_down

redis_logs:
	docker logs devagent_listener_redis
.PHONY: redis_logs

redis_logs_f:
	docker logs devagent_listener_redis -f
.PHONY: redis_logs_f

postgres:
	docker compose up -d listener_postgres
.PHONY: postgres

postgres_down:
	docker compose rm -s -v -f listener_postgres
.PHONY: postgres_down

pgadmin:
	docker compose up -d listener_pgadmin
.PHONY: pgadmin

pgadmin_down:
	docker compose rm -s -v -f listener_pgadmin
.PHONY: pgadmin_down

app:
	docker compose up -d --build listener_app 
.PHONY: app

app_down:
	docker compose rm -s -v -f listener_app
.PHONY: app_down

app_no_deps:
	docker compose up -d --no-deps --build listener_app 
.PHONY: app_no_deps

app_logs:
	docker logs devagent_listener_app
.PHONY: app_logs

app_logs_f:
	docker logs devagent_listener_app -f
.PHONY: app_logs_f

update_app:
	make app_down
	make worker_down
	make app
.PHONY: update_app

down:
	make app_down
	make worker_down
	make redis_down
	make postgres_down
.PHONY: down

test:
	$(PYTHON) -m unittest discover -v -s tests -p "*_test.py"
.PHONY: test

mypy:
	MYPYPATH=. $(PYTHON) -m mypy . --explicit-package-bases
.PHONY: mypy

tests_full:
	make test
	make mypy
.PHONY: tests_full

venv:
	rm -rf $(VENV) $(VENV_SYMLINK)
	$(SYSTEM_PYTHON) -m venv $(VENV)
	$(VENV_PYTHON) -m pip install -r requirements.txt
	ln -s $(VENV) $(VENV_SYMLINK)
.PHONY: venv

