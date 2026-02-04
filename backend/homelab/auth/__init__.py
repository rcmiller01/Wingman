"""Authentication and authorization for Wingman.

Simple role-based access control:
- viewer: read-only access
- operator: create executions, execute Tier 1 (low-risk)
- approver: approve/reject Tier 2/3 executions
- admin: lab allowlists, dangerous toggles, all permissions
"""

from .models import (
    Role,
    User,
    Permission,
    ROLE_PERMISSIONS,
    get_approval_permission_for_risk,
    get_execute_permission_for_risk,
)
from .middleware import (
    get_current_user,
    require_auth,
    require_role,
    require_permission,
    AuthenticationError,
    AuthorizationError,
    RateLimitError,
    user_context,
)
from .tokens import (
    create_api_key,
    validate_api_key,
    create_session_token,
    validate_session_token,
)
from .store import user_store
from .secrets import (
    get_secrets_config,
    get_rate_limiter,
    get_key_rotation_manager,
    get_auth_secret,
    hash_key_secure,
    verify_key_secure,
)

__all__ = [
    # Models
    "Role",
    "User", 
    "Permission",
    "ROLE_PERMISSIONS",
    "get_approval_permission_for_risk",
    "get_execute_permission_for_risk",
    # Middleware
    "get_current_user",
    "require_auth",
    "require_role",
    "require_permission",
    "AuthenticationError",
    "AuthorizationError",
    "RateLimitError",
    "user_context",
    # Tokens
    "create_api_key",
    "validate_api_key",
    "create_session_token",
    "validate_session_token",
    # Store
    "user_store",
    # Secrets & hardening
    "get_secrets_config",
    "get_rate_limiter",
    "get_key_rotation_manager",
    "get_auth_secret",
    "hash_key_secure",
    "verify_key_secure",
]
