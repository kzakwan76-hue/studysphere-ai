"""Application settings, loaded from environment variables and the .env file in the project root."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]  # the studysphere/ folder, whatever folder you run from
STORAGE_DIR = ROOT_DIR / "storage"  # database and uploads live here (git-ignored)


class Settings(BaseSettings):
    # extra="ignore": settings added in later milestones may already be in .env without causing an error.
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    # No default on purpose: the app refuses to start without a strong secret.
    secret_key: str = Field(min_length=32)
    access_token_minutes: int = Field(default=60, ge=1, le=1440)
    database_url: str = f"sqlite:///{(STORAGE_DIR / 'studysphere.db').as_posix()}"


@lru_cache
def get_settings() -> Settings:
    return Settings()