import pydantic_settings


class Settings(pydantic_settings.BaseSettings):
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

    class Config:
        env_file = "./.env"


app_settings = Settings()
