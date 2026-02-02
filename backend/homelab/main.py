from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from homelab.config import get_settings
from homelab.storage.database import init_db, engine
from homelab.observability.logging import configure_logging
from homelab.observability.middleware import RequestContextMiddleware
from homelab.observability.otel import configure_otel
from homelab.api.health import router as health_router
from homelab.api.inventory import router as inventory_router
from homelab.api.logs import router as logs_router
from homelab.api.facts import router as facts_router
from homelab.api.incidents import router as incidents_router
from homelab.api.plans import router as plans_router
from homelab.api.rag import router as rag_router
from homelab.scheduler import start_scheduler, stop_scheduler


configure_logging()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    print("[Copilot] Starting Homelab Copilot backend...")
    await init_db()
    print("[Copilot] Database initialized")
    start_scheduler()
    
    yield
    
    # Shutdown
    stop_scheduler()
    print("[Copilot] Shutting down...")


app = FastAPI(
    title=settings.app_name,
    description="Privacy-forward infrastructure copilot for homelabs",
    version="0.1.0",
    lifespan=lifespan,
)
configure_otel(app, engine)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestContextMiddleware)

# Include routers
app.include_router(health_router)
app.include_router(inventory_router)
app.include_router(logs_router)
app.include_router(facts_router)
app.include_router(incidents_router)
app.include_router(plans_router)
app.include_router(rag_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": "0.1.0",
        "docs": "/docs",
    }
