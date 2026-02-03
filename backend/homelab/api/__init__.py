"""API package init."""
from homelab.api.health import router as health_router
from homelab.api.inventory import router as inventory_router
from homelab.api.logs import router as logs_router
from homelab.api.facts import router as facts_router
from homelab.api.incidents import router as incidents_router
from homelab.api.plans import router as plans_router
from homelab.api.rag import router as rag_router
from homelab.api.todos import router as todos_router

__all__ = ["health_router", "inventory_router", "logs_router", "facts_router", "incidents_router", "plans_router", "rag_router", "todos_router"]
