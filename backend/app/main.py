from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings, get_active_provider, get_active_model, get_api_key
from .constants import PROVIDER_CATALOG
from .api.runs import router as runs_router
from .api.memory import router as memory_router
from .api.controls import router as controls_router
from .api.exports import router as exports_router
from .api.settings import router as settings_router
from .api.database import router as database_router
from .repositories.base import init_db
from .repositories.api_keys_repo import get_all_api_keys
from .cache import get_redis, close_redis
from .logger import get_logger
from .config import set_runtime_override
from .agent.tools.registry import get_available_tools

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: initialize database and Redis."""
    logger.info("Initializing database...")
    await init_db()
    
    # Load API keys from DB into config overrides
    logger.info("Loading API keys from database...")
    api_keys = await get_all_api_keys()
    for provider_id, key in api_keys.items():
        set_runtime_override(f"{provider_id}_api_key", key)

    logger.info("Connecting to Redis...")
    await get_redis()
    logger.info("ARIA backend started successfully.")
    yield
    await close_redis()


app = FastAPI(
    title="ARIA",
    description="Full-featured agentic AI research system with memory, self-critique, and multi-tool execution",
    version="1.1.0",
    lifespan=lifespan,
)

# CORS — allow React dev server
origins = [o.strip() for o in settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routes ───────────────────────────────────────────────────────────────────
app.include_router(runs_router, prefix="/api/v1", tags=["runs"])
app.include_router(memory_router, prefix="/api/v1", tags=["memory"])
app.include_router(controls_router, prefix="/api/v1", tags=["controls"])
app.include_router(exports_router, prefix="/api/v1", tags=["exports"])
app.include_router(settings_router, prefix="/api/v1", tags=["settings"])
app.include_router(database_router, prefix="/api/v1", tags=["database"])


@app.get("/api/v1/suggestions")
async def get_suggestions():
    """Return default topic suggestion chips for the frontend."""
    return {
        "suggestions": [
            {"icon": "⚡", "label": "AI agent architectures"},
            {"icon": "🔗", "label": "Multi-agent orchestration"},
            {"icon": "⚛️", "label": "Quantum computing trends"},
            {"icon": "🤖", "label": "LLM comparison"},
            {"icon": "🧬", "label": "Advances in protein folding"},
            {"icon": "🌐", "label": "Edge computing architectures"},
        ]
    }


@app.get("/api/v1/health")
async def health():
    provider = get_active_provider()
    return {
        "status": "ok",
        "provider": provider,
        "provider_name": PROVIDER_CATALOG.get(provider, {}).get("name", provider),
        "model": get_active_model(provider),
        "memory": "chromadb",
        "tools": _available_tools(),
        "available_providers": [
            pid for pid, info in PROVIDER_CATALOG.items()
            if not info["requires_key"] or get_api_key(pid)
        ],
    }


def _available_tools() -> list[str]:
    """Return the list of available tools based on the central registry."""
    tools_meta = get_available_tools()
    return [name for name, info in tools_meta.items() if info.get("available")]
