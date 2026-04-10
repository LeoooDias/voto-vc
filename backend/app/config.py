from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://votovc:votovc@localhost:54329/votovc"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30

    cors_origins: str = "http://localhost:5173"
    log_level: str = "INFO"

    redis_url: str = "redis://localhost:6379/0"

    rate_limit_default: str = "60/minute"
    rate_limit_matching: str = "20/minute"
    rate_limit_share: str = "5/minute"

    frontend_url: str = "http://localhost:5173"

    anthropic_api_key: str = ""
    chat_rate_limit: str = "30/hour"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
