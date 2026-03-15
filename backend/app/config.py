from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://votovc:votovc@localhost:54329/votovc"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30

    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 1 week

    cors_origins: str = "http://localhost:5173"
    log_level: str = "INFO"

    redis_url: str = "redis://localhost:6379/0"

    rate_limit_default: str = "60/minute"
    rate_limit_matching: str = "20/minute"
    rate_limit_auth: str = "10/minute"

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/auth/google/callback"
    frontend_url: str = "http://localhost:5173"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
