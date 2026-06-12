from functools import lru_cache
from typing import List

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=True)

    APP_NAME: str = "LLM-as-a-Judge Platform"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    DATABASE_URL: str

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    CORS_ORIGINS: List[str] = []

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | List[str]) -> List[str]:
        """
        Parse CORS origins from either a comma-separated string or JSON list.

        This handles both formats:
          - '["http://localhost:3000"]' (JSON from .env)
          - 'http://localhost:3000,http://localhost:8080' (plain CSV)
        """
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            # Try JSON parse first, then CSV fallback
            import json

            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return []
    
@lru_cache
def get_settings() -> Settings:
    return Settings()

settings: Settings = get_settings()
