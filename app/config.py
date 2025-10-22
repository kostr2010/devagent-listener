import pydantic_settings


class ListenerConfig(pydantic_settings.BaseSettings):
    GITCODE_TOKEN: str
    GITEE_TOKEN: str
    LISTENER_PORT: int
    DEVAGENT_PROVIDER: str
    DEVAGENT_MODEL: str
    DEVAGENT_API_KEY: str
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_USERNAME: str
    REDIS_PASSWORD: str
    LISTENER_REDIS_DB: int
    DEVAGENT_REDIS_DB: int

    class Config:
        env_file = "./.env"


CONFIG = ListenerConfig()
