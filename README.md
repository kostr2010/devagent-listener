## Prerequisites

- python 3.11
- docker

## Setup for tests and local development

```bash
make venv
```

## Testing

For testing purposes, `.env` file creation can be skipped like this

```bash
cp .env.example .env
```

To check code for static errors, run the following command

```bash
make mypy
```

To run unit tests, run the following command

```bash
make test
```

Shortuct to run all checks is always the following:

```bash
make tests_full
```

## Send test requests

Fox ease of request sending, there are dedicated scripts for each possible request in `scripts` directory.

NOTE: to run them, you should first do

```bash
make venv
```

Then execute script using `.venv/bin/python`, like this:

```bash
.venv/bin/python ./scripts/<script>.py [args]
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
