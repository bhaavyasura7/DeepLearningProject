import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str = "sqlite:///./movierec.db"
    
    # Redis / Queue
    REDIS_URL: str = "redis://localhost:6379/0"
    USE_IN_MEMORY_QUEUE: bool = True  # Allows running without standalone Redis in dev/test
    
    # Auth & Security
    SECRET_KEY: str = "dev_secret_key_change_in_production_1234567890"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # LLM Settings
    LLM_PROVIDER: str = "mock"  # "mock", "openai", "ollama"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1:8b"
    
    # Recommendation Parameters
    DECAY_RATE: float = 0.05
    SHORT_TERM_WEIGHT: float = 0.6
    LONG_TERM_WEIGHT: float = 0.4
    DEFAULT_BATCH_SIZE: int = 10
    DEFAULT_COOLDOWN_MINUTES: int = 30
    
    # Algorithm Versions
    BASELINE_ALGO_VERSION: str = "v1.0-baseline-content-cf"
    DYNAMIC_ALGO_VERSION: str = "v1.0-dynamic-memory-t-pra"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
