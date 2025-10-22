import celery

from ..config import CONFIG


def celery_instance(
    worker_name: str, redis_db: int, expiry: int = 3600
) -> celery.Celery:
    usr = CONFIG.REDIS_USERNAME
    pwd = CONFIG.REDIS_PASSWORD
    host = CONFIG.REDIS_HOST
    port = CONFIG.REDIS_PORT
    redis_url = f"redis://{usr}:{pwd}@{host}:{port}/{redis_db}"

    app = celery.Celery(
        worker_name,
        broker=redis_url,
        backend=redis_url,
    )

    app.conf.task_track_started = True
    app.conf.result_expires = expiry

    return app
