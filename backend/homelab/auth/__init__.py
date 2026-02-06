"""Authentication package."""

from homelab.auth.models import Role, Permission, User, role_has_permission, get_permissions_for_role
from homelab.auth.oidc import OIDCClient, OIDCConfig
# from homelab.auth.db_schema import UserDB, SessionDB, ServiceAccountDB
from homelab.auth.store import user_store
from homelab.auth.tokens import create_session_token
from homelab.auth.middleware import (
    get_current_user,
    require_auth,
    require_role,
    require_permission,
    # CurrentUser, # Middleware doesn't define CurrentUser alias, checking...
)

# Alias for compatibility if needed, or define it here
from typing import Annotated
from fastapi import Depends
CurrentUser = Annotated[User, Depends(get_current_user)]

__all__ = [
    # RBAC
    "Role",
    "Permission",
    "User",
    "role_has_permission",
    "get_permissions_for_role",
    
    # Store
    "user_store",
    
    # Tokens
    "create_session_token",
    
    # OIDC
    "OIDCClient",
    "OIDCConfig",
    
    # Database models (commented out to avoid confusing API that expects memory models)
    # "UserDB",
    # "SessionDB",
    # "ServiceAccountDB",
    
    # Dependencies (from middleware)
    "get_current_user",
    "require_auth",
    "require_role",
    "require_permission",
    "CurrentUser",
]
