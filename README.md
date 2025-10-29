## Prerequisites

- python 3.11
- docker

## Setup for tests and local development

```bash
make venv
```

## Test

```bash
make test
```

## Run

First, edit `.env` according to your desired values. Value for `REDIS_HOSTNAME` and `POSTGRES_HOSTNAME` can be left empty for now

```bash
cp .env.example .env
```

Then, build your databases

```bash
make redis
make db
```

Edit value for `REDIS_HOSTNAME` in `.env`. Correct value can be found like this:

```bash
docker inspect devagent_listener_redis  | grep Gateway
```

Edit value for `POSTGRES_HOSTNAME` in `.env`. Correct value can be found like this:

```bash
docker inspect devagent_listener_postgres  | grep Gateway
```

After that, run

```bash
make app
```

## Update requirements list

```bash
pip freeze > requirements.txt
```

## Generate migration

```bash
alembic revision --autogenerate -m "My migration message"
```
