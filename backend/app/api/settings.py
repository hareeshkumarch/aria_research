"""Settings API — manage LLM provider, model, and API keys at runtime."""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from ..config import (
    get_active_model, get_api_key, get_active_provider, set_runtime_override
)
from ..constants import PROVIDER_CATALOG
from ..repositories.api_keys_repo import save_api_key, delete_api_key


router = APIRouter()


class UpdateSettingsRequest(BaseModel):
    provider: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None


class ProviderStatus(BaseModel):
    id: str
    name: str
    models: list[str]
    default_model: str
    requires_key: bool
    free_tier: bool
    has_key: bool
    is_active: bool
    active_model: str


@router.get("/settings/providers")
async def list_providers():
    """List all available LLM providers and their configuration status."""
    active_provider = get_active_provider()
    providers = []

    for pid, info in PROVIDER_CATALOG.items():
        key = get_api_key(pid)
        providers.append(ProviderStatus(
            id=pid,
            name=info["name"],
            models=info["models"],
            default_model=info["default_model"],
            requires_key=info["requires_key"],
            free_tier=info["free_tier"],
            has_key=bool(key) or not info["requires_key"],
            is_active=(pid == active_provider),
            active_model=get_active_model(pid),
        ))

    return {
        "providers": [p.model_dump() for p in providers],
        "active_provider": active_provider,
        "active_model": get_active_model(active_provider),
    }


@router.post("/settings/provider")
async def set_provider(body: UpdateSettingsRequest):
    """Set the active LLM provider and optionally model + API key."""
    if body.provider:
        if body.provider not in PROVIDER_CATALOG and body.provider != "auto":
            return {"error": f"Unknown provider: {body.provider}"}
        set_runtime_override("llm_provider", body.provider)

    if body.api_key and body.provider:
        # Store the API key for the specified provider
        key_name = f"{body.provider}_api_key"
        set_runtime_override(key_name, body.api_key)
        try:
            await save_api_key(body.provider, body.api_key)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to persist API key for {body.provider}: {e}")

    if body.model and body.provider:
        model_name = f"{body.provider}_model"
        set_runtime_override(model_name, body.model)

    active_provider = get_active_provider()
    return {
        "message": "Settings updated",
        "active_provider": active_provider,
        "active_model": get_active_model(active_provider),
    }


@router.delete("/settings/provider/{provider_id}/key")
async def delete_provider_key(provider_id: str):
    """Delete an API key for a provider."""
    key_name = f"{provider_id}_api_key"
    set_runtime_override(key_name, None)
    try:
        await delete_api_key(provider_id)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to delete API key for {provider_id}: {e}")
    
    active_provider = get_active_provider()
    return {
        "message": f"API key deleted for {provider_id}",
        "active_provider": active_provider,
    }


@router.get("/settings/active")
async def get_active():
    """Get the currently active provider and model."""
    provider = get_active_provider()
    return {
        "provider": provider,
        "model": get_active_model(provider),
        "provider_name": PROVIDER_CATALOG.get(provider, {}).get("name", provider),
    }
