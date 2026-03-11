from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # LLM Provider — supports multiple providers, "auto" picks first available
    llm_provider: str = "auto"

    # Groq (free tier — llama-3.3-70b-versatile)
    groq_api_key: Optional[str] = None
    groq_model: str = "llama-3.3-70b-versatile"

    # Google Gemini (free tier — gemini-1.5-flash)
    google_api_key: Optional[str] = None
    gemini_model: str = "gemini-2.0-flash"

    # Ollama (local, fully free)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # OpenAI
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"

    # Anthropic
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-5-sonnet-20241022"

    # xAI Grok
    xai_api_key: Optional[str] = None
    grok_model: str = "grok-2-latest"

    # Tools — Optional API keys
    tavily_api_key: Optional[str] = None
    e2b_api_key: Optional[str] = None

    # Memory — ChromaDB
    chroma_persist_dir: str = "./chroma_data"
    chroma_collection: str = "aria_memory"

    # Cost tracking per 1M tokens (input/output)
    cost_per_million_tokens: float = 0.0  # 0 for free tiers

    # App
    cors_origins: str = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
    max_subtasks: int = 5
    max_retries: int = 2
    cost_limit_usd: float = 1.00
    max_concurrent_runs: int = 3
    outputs_dir: str = "./outputs"

    # Faster model for refinement loop (critic/refiner) to reduce latency
    refine_provider: str = "openai"
    refine_model: str = "gpt-4o-mini"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()


# ─── Runtime overrides (set from frontend) ─────────────────────────────────
# These are mutable at runtime and take precedence over env settings

_runtime_overrides: dict = {}


def set_runtime_override(key: str, value):
    """Set a runtime override for a setting."""
    _runtime_overrides[key] = value


def get_runtime_override(key: str, default=None):
    """Get a runtime override, or None."""
    return _runtime_overrides.get(key, default)


def get_active_provider() -> str:
    """Get the currently active provider (runtime override > env setting)."""
    provider = get_runtime_override("llm_provider", settings.llm_provider)
    if provider == "auto":
        return _auto_select_provider()
    return provider


def get_active_model(provider: str | None = None) -> str:
    """Get the active model for a provider."""
    if provider is None:
        provider = get_active_provider()

    override_model = get_runtime_override(f"{provider}_model")
    if override_model:
        return override_model

    model_map = {
        "groq": settings.groq_model,
        "gemini": settings.gemini_model,
        "ollama": settings.ollama_model,
        "openai": settings.openai_model,
        "anthropic": settings.anthropic_model,
        "grok": settings.grok_model,
    }
    return model_map.get(provider, "auto")


def get_api_key(provider: str) -> str | None:
    """Get API key for a provider (runtime override > env)."""
    override = get_runtime_override(f"{provider}_api_key")
    if override:
        return override

    key_map = {
        "groq": settings.groq_api_key,
        "gemini": settings.google_api_key,
        "openai": settings.openai_api_key,
        "anthropic": settings.anthropic_api_key,
        "grok": settings.xai_api_key,
    }
    return key_map.get(provider)


def _auto_select_provider() -> str:
    """Auto-select the first provider that has an API key configured."""
    priority = ["groq", "gemini", "openai", "anthropic", "grok", "ollama"]
    for p in priority:
        key = get_api_key(p)
        if key:
            return p
    # Fallback to Ollama (local, no key needed)
    return "ollama"

# End of configuration
