## Prerequisites

- python 3.11
- docker
- postgresql
- postgresql-devel

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run

Edit `serets.env` according to your desired values. value for `POSTGRES_HOSTNAME` can be found like this:

```bash
docker inspect listener_db  | grep Gateway
```

After that, run

```bash
docker compose up listener_db -d
alembic upgrade head
uvicorn app.main:listener --host localhost --port 8008 --reload
```

For the `RUNTIME_CORE_ROOT` and `ETS_FRONTEND_ROOT` repositories, you may want to apply the followng patches that introduce basic infrastructure that is needed for correct operation of the listener:

- https://gitcode.com/nazarovkonstantin/arkcompiler_ets_frontend/tree/feature/review_rules_test
- https://gitcode.com/nazarovkonstantin/arkcompiler_runtime_core/tree/feature/review_rules_test

## Generate migration

```bash
alembic revision --autogenerate -m "My migration message"
```

## Update requirements list

```bash
pip freeze > requirements.txt
```
