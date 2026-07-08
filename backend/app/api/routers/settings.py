"""Settings and LLM health check router."""
from fastapi import APIRouter

from app.core.config import get_settings
from app.learning.q_learning import q_orchestrator
from app.llm.registry import list_providers, list_role_mappings
from app.services.llm_service import check_llm_health, check_provider_health

router = APIRouter(prefix="/settings", tags=["settings"])
settings = get_settings()


@router.get("")
async def get_settings_endpoint():
    policy = q_orchestrator.get_policy_summary()
    providers = list_providers()
    configured = [p for p in providers if p["configured"]]
    return {
        "rl_alpha": settings.rl_alpha,
        "rl_gamma": settings.rl_gamma,
        "rl_epsilon_start": settings.rl_epsilon_start,
        "rl_epsilon_end": settings.rl_epsilon_end,
        "rl_epsilon_decay": settings.rl_epsilon_decay,
        "llm_default_provider": settings.llm_default_provider,
        "llm_role_mappings": list_role_mappings(),
        "llm_providers": providers,
        "llm_provider_configured": len(configured) > 0,
        "embedding_model": settings.embedding_model,
        "q_table_states": len(policy.get("states", {})),
        "engagement_count": policy.get("engagement_count", 0),
        "epsilon": policy.get("epsilon", 0),
        # backward compat
        "llm_model": settings.llm_model,
        "llm_provider": settings.llm_default_provider,
        "nvidia_api_base": settings.nvidia_api_base,
        "api_key_configured": any(p["configured"] for p in providers),
    }


@router.get("/llm")
async def check_llm():
    return await check_llm_health()


@router.get("/llm/{provider_name}")
async def check_llm_provider(provider_name: str):
    return await check_provider_health(provider_name)


@router.get("/llm-providers/list")
async def llm_providers_list():
    return {
        "default": settings.llm_default_provider,
        "providers": list_providers(),
        "role_mappings": list_role_mappings(),
    }


# Backward-compatible alias
@router.get("/ollama")
async def check_ollama_alias():
    return await check_llm_health()
