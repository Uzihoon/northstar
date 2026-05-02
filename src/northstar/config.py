from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
  model_config = SettingsConfigDict(
    env_file=".env",
    env_file_encoding="utf-8",
    extra="ignore"
  )

  app_name: str = "northstar"
  environment: str = "dev"
  ollama_base_url: str = "http://localhost:11434"
  default_model: str = "gemma4:e4b"
  database_url: str = "postgresql+psycopg://northstar:northstar@localhost:5432/northstar"

@lru_cache
def get_settings() -> Settings:
  return Settings()