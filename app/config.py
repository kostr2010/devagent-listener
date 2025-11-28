import pydantic_settings


class ListenerConfig(pydantic_settings.BaseSettings):
    GITCODE_TOKEN: str
    LISTENER_PORT: int
    DEVAGENT_PROVIDER: str
    DEVAGENT_MODEL: str
    DEVAGENT_API_KEY: str
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_USERNAME: str
    REDIS_PASSWORD: str
    REDIS_LISTENER_DB: int
    REDIS_DEVAGENT_DB: int
    DB_PROTOCOL: str
    DB_PORT: int
    DB_PASSWORD: str
    DB_USER: str
    DB_DB: str
    DB_HOST: str
    DB_HOSTNAME: str
    EXPIRY_TASK_INFO: int
    EXPIRY_DEVAGENT_WORKER: int
    SECRET_KEY: str
    PGADMIN_DEFAULT_EMAIL: str
    PGADMIN_DEFAULT_PASSWORD: str
    PGADMIN_PORT: int
    NEXUS_USERNAME: str
    NEXUS_PASSWORD: str
    NEXUS_REPO_URL: str
    MAX_WORKERS: int

    class Config:
        env_file = "./.env"


CONFIG = ListenerConfig()
