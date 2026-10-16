"""Application settings, loaded from environment variables and the .env file in the project root."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
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

    # Uploaded documents
    uploads_dir: Path = STORAGE_DIR / "uploads"
    max_upload_mb: int = Field(default=10, ge=1, le=50)
    max_documents_per_user: int = Field(default=50, ge=1)
    max_pdf_pages: int = Field(default=300, ge=1)
    max_extracted_chars: int = Field(default=2_000_000, ge=1_000)

    # Login throttling
    login_max_failures: int = Field(default=5, ge=1)  # per (email, IP) pair inside the window
    login_max_failures_per_ip: int = Field(default=20, ge=1)  # per IP across all emails
    login_window_minutes: int = Field(default=15, ge=1)

    # Answers and the AI provider ("none" shows the best passages only and needs no key)
    llm_provider: Literal["none", "anthropic", "ollama"] = "none"
    anthropic_api_key: SecretStr = SecretStr("")
    anthropic_model: str = "claude-haiku-4-5-20251001"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    llm_timeout_seconds: float = Field(default=60.0, gt=0)
    llm_max_answer_tokens: int = Field(default=400, ge=50, le=2000)
    answer_min_coverage: float = Field(default=0.5, ge=0.0, le=1.0)  # below this, the app refuses to answer
    ask_limit_per_hour: int = Field(default=30, ge=1)


@lru_cache
def get_settings() -> Settings:
    return Settings()