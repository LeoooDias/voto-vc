from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://votovc:votovc@localhost:54329/votovc"
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 1 week
    cors_origins: str = "http://localhost:5173"
    log_level: str = "DEBUG"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
