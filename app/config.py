from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql://dbw_user:dbw2026@localhost:5432/dbw_v3"

    class Config:
        env_file = ".env"

settings = Settings()
