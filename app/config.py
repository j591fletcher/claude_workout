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

    # LLM — "ollama" (local, free, needs the GPU host reachable over Tailscale)
    # or "anthropic" (hosted, billed). Ollama is the default to avoid API cost.
    llm_backend: str = "ollama"
    anthropic_model: str = "claude-opus-4-8"
    max_tokens: int = 4096
    ollama_base_url: str = ""  # e.g. http://100.85.238.56:11434 (tailnet IP of the GPU box)
    ollama_model: str = "qwen2.5:14b"

    # Retriever (Module B)
    embedding_backend: str = "sentence-transformers"  # or "hashing" (offline fallback)
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    chroma_dir: Path = REPO_ROOT / "data" / "chroma"
    pdf_dir: Path = REPO_ROOT / "pdfs"
    top_k: int = 8
    # Cosine distance cutoff (all-MiniLM-L6-v2): single-topic matches cluster
    # ~0.27-0.34, but compound/multi-topic questions can pull unrelated chunks
    # into that same range — see Phase 4 live-verify notes in HANDOFF.md. 0.35
    # trades recall for precision: better to say "not found" than hallucinate.
    retrieval_max_distance: float = 0.35

    # Hevy (Module C)
    hevy_base_url: str = "https://api.hevyapp.com"
    # Exact titles as they appear in Hevy (confirmed at Checkpoint 2, 2026-07-08);
    # matching is case-insensitive.
    hevy_routines: tuple[str, ...] = (
        "Push", "Pull", "New abs", "Upper Mix",
        "Legs (Quads, Hamstrings, Glutes, Calves)",
    )

    # Server — bind stays on localhost/tailnet (CLAUDE.md §1)
    host: str = "127.0.0.1"
    port: int = 8000

    # Runtime prompt for Module A
    trainer_prompt_path: Path = REPO_ROOT / "prompts" / "trainer.md"


@lru_cache
def get_settings() -> Settings:
    return Settings()
