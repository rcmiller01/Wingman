"""Authentication package."""

from homelab.auth.models import Role, Permission, role_has_permission, get_permissions_for_role
from homelab.auth.oidc import OIDCClient, OIDCConfig
from homelab.auth.db_models import UserDB, SessionDB, ServiceAccountDB
from homelab.auth.dependencies import (
    get_current_user,
    require_role,
    require_permission,
    CurrentUser,
)

__all__ = [
    # RBAC
    "Role",
    "Permission",
    "role_has_permission",
    "get_permissions_for_role",
    
    # OIDC
    "OIDCClient",
    "OIDCConfig",
    
    # Database models
    "UserDB",
    "SessionDB",
    "ServiceAccountDB",
    
    # Dependencies
    "get_current_user",
    "require_role",
    "require_permission",
    "CurrentUser",
]
