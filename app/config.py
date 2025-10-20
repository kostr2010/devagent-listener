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

    class Config:
        env_file = "./secrets.env"


app_settings = Settings()
