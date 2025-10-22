## Prerequisites

- python 3.11
- docker
- postgresql
- postgresql-devel

## Setup

```bash
python -m venv venv-devagent-listener
source venv-devagent-listener/bin/activate
pip install -r requirements.txt
```

## Run

First, edit `serets.env` according to your desired values. Value for `POSTGRES_HOSTNAME` can be left empty for now

```bash
cp .env.example .env
```

Then, build your database

```bash
make db
```

Edit value for `POSTGRES_HOSTNAME` in `serets.env`. Correct value can be found like this:

```bash
docker inspect listener_db  | grep Gateway
```

After that, run

```bash
make app
```

## Generate migration

```bash
alembic revision --autogenerate -m "My migration message"
```

## Update requirements list

```bash
pip freeze > requirements.txt
```
