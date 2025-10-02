### Compose shortcuts

up:
	docker compose up --build -d

run:
	docker compose run listener_app

down:
	docker compose down --remove-orphans --volumes

sh:
	docker compose run -p 8000:8000 --rm app_launch bash

logs:
	docker compose logs -f

migrate:
	alembic upgrade head

### Project shortcuts
fast_api:
	docker compose run --rm app_launch python src/app.py

fast_api_app:
	docker compose run --rm app_launch uvicorn src.app:app --proxy-headers --host 0.0.0.0 --port 80
