from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://structapi:structapi@localhost:5432/structapi"
    log_level: str = "INFO"


settings = Settings()
