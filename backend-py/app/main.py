from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.storage import init_db
from app.api import health_router, inventory_router, logs_router, facts_router, incidents_router, plans_router
from app.scheduler import start_scheduler, stop_scheduler


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

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)
app.include_router(inventory_router)
app.include_router(logs_router)
app.include_router(facts_router)
app.include_router(incidents_router)
app.include_router(plans_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": "0.1.0",
        "docs": "/docs",
    }
