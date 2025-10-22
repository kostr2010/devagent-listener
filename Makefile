VENV = .venv
VENV_SYMLINK = venv # to ensure correct work of the IDEs
VENV_PYTHON = $(VENV)/bin/python
SYSTEM_PYTHON = $(or $(shell which python3.11), $(shell which python))
PYTHON = $(or $(wildcard $(VENV_PYTHON)), $(SYSTEM_PYTHON))

worker:
	docker compose up listener_devagent_worker

redis:
	docker compose up -d listener_redis

app:
	docker compose up -d --build listener_app 

app_no_deps:
	docker compose up -d --no-deps --build listener_app 

down:
	docker compose rm -s -v -f listener_app
	docker compose rm -s -v -f listener_devagent_worker
	docker compose rm -s -v -f listener_redis

test:
	$(PYTHON) -m unittest discover -v -s tests -p "*_test.py"

venv:
	rm -rf $(VENV) $(VENV_SYMLINK)
	$(SYSTEM_PYTHON) -m venv $(VENV)
	$(VENV_PYTHON) -m pip install -r requirements.txt
	ln -s $(VENV) $(VENV_SYMLINK)

.PHONY: db
.PHONY: app
.PHONY: down
.PHONY: migrate
.PHONY: test
.PHONY: venv
