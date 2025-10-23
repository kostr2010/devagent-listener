import pydantic_settings


class ListenerConfig(pydantic_settings.BaseSettings):
    GITCODE_TOKEN: str
    GITEE_TOKEN: str
    DEVAGENT_PROVIDER: str
    DEVAGENT_MODEL: str
    DEVAGENT_API_KEY: str
    REDIS_HOST: str
    REDIS_PORT: str
    REDIS_USERNAME: str
    REDIS_PASSWORD: str
    LISTENER_REDIS_DB: str
    DEVAGENT_REDIS_DB: str

    class Config:
        env_file = "./.env"


CONFIG = ListenerConfig()
