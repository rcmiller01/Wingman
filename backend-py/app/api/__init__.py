"""API package init."""
from app.api.health import router as health_router
from app.api.inventory import router as inventory_router

__all__ = ["health_router", "inventory_router"]
