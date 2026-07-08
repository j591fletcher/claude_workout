"""Centralized configuration. Every knob is env-driven (see .env.example)."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Secrets — required at runtime, never committed (CLAUDE.md §1)
    anthropic_api_key: str = ""
    hevy_api_key: str = ""

    # LLM
    anthropic_model: str = "claude-opus-4-8"
    max_tokens: int = 4096

    # Retriever (Module B)
    embedding_backend: str = "sentence-transformers"  # or "hashing" (offline fallback)
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    chroma_dir: Path = REPO_ROOT / "data" / "chroma"
    pdf_dir: Path = REPO_ROOT / "pdfs"
    top_k: int = 8

    # Hevy (Module C)
    hevy_base_url: str = "https://api.hevyapp.com"
    hevy_routines: tuple[str, ...] = ("Push", "Pull", "New Abs", "Upper Mix", "Legs")

    # Server — bind stays on localhost/tailnet (CLAUDE.md §1)
    host: str = "127.0.0.1"
    port: int = 8000

    # Runtime prompt for Module A
    trainer_prompt_path: Path = REPO_ROOT / "prompts" / "trainer.md"


@lru_cache
def get_settings() -> Settings:
    return Settings()
