"""API package init."""
from app.api.health import router as health_router
from app.api.inventory import router as inventory_router
from app.api.logs import router as logs_router
from app.api.facts import router as facts_router
from app.api.incidents import router as incidents_router

__all__ = ["health_router", "inventory_router", "logs_router", "facts_router", "incidents_router"]
