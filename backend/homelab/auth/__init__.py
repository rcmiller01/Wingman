"""Authentication package public exports.

Keep this module lightweight so submodule imports such as
``from homelab.auth.db_schema import UserDB`` do not pull optional
OIDC dependencies at import time.
"""

from typing import Annotated

from fastapi import Depends

from homelab.auth.models import (
    Role,
    Permission,
    User,
    role_has_permission,
    get_permissions_for_role,
    get_approval_permission_for_risk,
    get_execute_permission_for_risk,
)
from homelab.auth.store import user_store
from homelab.auth.tokens import create_session_token
from homelab.auth.middleware import (
    get_current_user,
    require_auth,
    require_role,
    require_permission,
    user_context,
)

CurrentUser = Annotated[User, Depends(get_current_user)]

__all__ = [
    "Role",
    "Permission",
    "User",
    "role_has_permission",
    "get_permissions_for_role",
    "user_store",
    "create_session_token",
    "get_current_user",
    "require_auth",
    "require_role",
    "require_permission",
    "get_approval_permission_for_risk",
    "get_execute_permission_for_risk",
    "user_context",
    "CurrentUser",
]
