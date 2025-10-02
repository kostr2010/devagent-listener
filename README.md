# For production

Edit `serets.env` according to your desired values. value for `POSTGRES_HOSTNAME` can be found like this:

```bash
docker inspect listener_db  | grep Gateway
```

After that, run

```bash
make up
make migrate
make run
```

# For local

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

```bash
docker compose up listener_db -d
alembic upgrade head
uvicorn app.main:listener --host localhost --port 8008 --reload
```

## Generate migration

```bash
alembic revision --autogenerate -m "My migration message"
```

## Update requirements list

```bash
pip freeze > requirements.txt
```
