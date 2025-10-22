import pydantic_settings


class ListenerConfig(pydantic_settings.BaseSettings):
    DATABASE_PORT: int
    POSTGRES_PASSWORD: str
    POSTGRES_USER: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_HOSTNAME: str
    GITCODE_TOKEN: str
    GITEE_TOKEN: str
    DEVAGENT_PROVIDER: str
    DEVAGENT_MODEL: str
    DEVAGENT_API_KEY: str
    REDIS_HOST: str
    REDIS_PORT: str
    REDIS_PASSWORD: str

    class Config:
        env_file = "./.env"


LISTENER_CONFIG = ListenerConfig()
