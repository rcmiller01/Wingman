"""API for managing application settings including LLM configuration."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from homelab.llm.providers import llm_manager, LLMProvider, LLMFunction

router = APIRouter(prefix="/api/settings", tags=["settings"])


class LLMSettingsResponse(BaseModel):
    """Current LLM settings."""
    chat: dict
    embedding: dict


class LLMSettingsUpdate(BaseModel):
    """Update LLM settings for a function."""
    provider: str
    model: str | None = None


class ModelInfo(BaseModel):
    """Model information."""
    id: str
    name: str
    provider: str
    capabilities: dict
    context_length: int | None = None
    size: int | None = None
    pricing: dict | None = None


class ProviderInfo(BaseModel):
    """Provider information."""
    id: str
    name: str
    available: bool
    configured: bool


@router.get("/llm")
async def get_llm_settings() -> LLMSettingsResponse:
    """Get current LLM configuration."""
    settings = llm_manager.get_settings()
    return LLMSettingsResponse(
        chat=settings["chat"],
        embedding=settings["embedding"],
    )


@router.put("/llm/{function}")
async def update_llm_settings(
    function: str,
    update: LLMSettingsUpdate,
):
    """Update LLM settings for a specific function."""
    try:
        func = LLMFunction(function)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid function: {function}. Use 'chat' or 'embedding'")

    try:
        provider = LLMProvider(update.provider)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid provider: {update.provider}")

    llm_manager.set_settings(func, provider, update.model)

    return {
        "message": f"Updated {function} settings",
        "function": function,
        "provider": update.provider,
        "model": update.model,
    }


@router.get("/llm/providers")
async def list_providers() -> list[ProviderInfo]:
    """List available LLM providers."""
    providers = await llm_manager.list_all_providers()
    return [ProviderInfo(**p) for p in providers]


@router.get("/llm/models/{provider}")
async def list_models(
    provider: str,
    function: str | None = Query(None, description="Filter by function: 'chat' or 'embedding'"),
) -> list[ModelInfo]:
    """List available models for a provider."""
    try:
        prov = LLMProvider(provider)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid provider: {provider}")

    func = None
    if function:
        try:
            func = LLMFunction(function)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid function: {function}")

    models = await llm_manager.list_models(prov, func)
    return [ModelInfo(**m) for m in models]


@router.post("/llm/test")
async def test_llm_connection(provider: str = Query(...)):
    """Test connection to an LLM provider."""
    try:
        prov = LLMProvider(provider)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid provider: {provider}")

    try:
        models = await llm_manager.list_models(prov)
        if not models:
            return {
                "success": False,
                "provider": provider,
                "error": "No models available. For Ollama, ensure models are pulled.",
            }

        return {
            "success": True,
            "provider": provider,
            "model_count": len(models),
        }
    except Exception as e:
        return {
            "success": False,
            "provider": provider,
            "error": str(e),
        }
