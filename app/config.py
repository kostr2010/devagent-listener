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
    POSTGRES_PORT: int
    POSTGRES_PASSWORD: str
    POSTGRES_USER: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_HOSTNAME: str
    EXPIRY_TASK_INFO: int
    EXPIRY_DEVAGENT_WORKER: int

    class Config:
        env_file = "./.env"


CONFIG = ListenerConfig()
