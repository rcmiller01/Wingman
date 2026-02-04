"""FastAPI middleware and dependencies for authentication."""

from typing import Optional, Callable
from functools import wraps

from fastapi import Request, HTTPException, Depends
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials

from .models import User, Role, Permission, get_permissions_for_role
from .tokens import validate_session_token
from .store import user_store
from .secrets import get_rate_limiter


# --- Exceptions ---

class AuthenticationError(HTTPException):
    """Raised when authentication fails."""
    def __init__(self, detail: str = "Authentication required", retry_after: int | None = None):
        headers = {"Retry-After": str(retry_after)} if retry_after else None
        super().__init__(status_code=401, detail=detail, headers=headers)


class AuthorizationError(HTTPException):
    """Raised when authorization fails."""
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(status_code=403, detail=detail)


class RateLimitError(HTTPException):
    """Raised when rate limit is exceeded."""
    def __init__(self, retry_after_seconds: int):
        super().__init__(
            status_code=429, 
            detail=f"Too many authentication failures. Retry after {retry_after_seconds} seconds.",
            headers={"Retry-After": str(retry_after_seconds)}
        )


# --- Security schemes ---

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


# --- Dependencies ---

async def get_current_user(
    request: Request,
    api_key: Optional[str] = Depends(api_key_header),
    bearer: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[User]:
    """Get the current authenticated user.
    
    Supports two authentication methods:
    1. API Key via X-API-Key header
    2. Bearer token via Authorization header
    
    Includes rate limiting for failed attempts.
    Returns None if no authentication provided (for optional auth).
    """
    user = None
    rate_limiter = get_rate_limiter()
    
    # Get source identifier for rate limiting (IP or key prefix)
    source = _get_rate_limit_source(request, api_key)
    
    # Check if rate limited
    is_locked, locked_until = rate_limiter.is_locked(source)
    if is_locked and locked_until:
        from datetime import datetime, timezone
        retry_after = int((locked_until - datetime.now(timezone.utc)).total_seconds())
        raise RateLimitError(retry_after_seconds=max(1, retry_after))
    
    # Try API key first
    if api_key:
        user = user_store.get_user_by_api_key(api_key)
        if user:
            rate_limiter.record_success(source)
            user_store.record_login(user.id)
            return user
        else:
            # Failed auth attempt
            lockout = rate_limiter.record_failure(source)
            if lockout:
                raise RateLimitError(retry_after_seconds=int(lockout.total_seconds()))
    
    # Try bearer token
    if bearer:
        payload = validate_session_token(bearer.credentials)
        if payload:
            user = user_store.get_user(payload["user_id"])
            if user and user.is_active:
                rate_limiter.record_success(source)
                return user
        
        # Failed bearer auth
        lockout = rate_limiter.record_failure(source)
        if lockout:
            raise RateLimitError(retry_after_seconds=int(lockout.total_seconds()))
    
    return None


def _get_rate_limit_source(request: Request, api_key: Optional[str]) -> str:
    """Get identifier for rate limiting (IP + key prefix)."""
    # Get client IP
    client_ip = request.client.host if request.client else "unknown"
    
    # If API key provided, use key prefix for more granular limiting
    if api_key and len(api_key) >= 16:
        key_prefix = api_key[:16]
        return f"{client_ip}:{key_prefix}"
    
    return client_ip


async def require_auth(
    user: Optional[User] = Depends(get_current_user),
) -> User:
    """Require authentication - raises 401 if not authenticated."""
    if not user:
        raise AuthenticationError("Authentication required")
    return user


def require_role(required_role: Role):
    """Dependency that requires a minimum role level."""
    async def check_role(user: User = Depends(require_auth)) -> User:
        if not user.has_role(required_role):
            raise AuthorizationError(
                f"Role '{required_role.value}' or higher required, "
                f"you have '{user.role.value}'"
            )
        return user
    return check_role


def require_permission(required_permission: Permission):
    """Dependency that requires a specific permission."""
    async def check_permission(user: User = Depends(require_auth)) -> User:
        if not user.has_permission(required_permission):
            raise AuthorizationError(
                f"Permission '{required_permission.value}' required"
            )
        return user
    return check_permission


def require_any_permission(*permissions: Permission):
    """Dependency that requires any of the specified permissions."""
    async def check_permissions(user: User = Depends(require_auth)) -> User:
        for perm in permissions:
            if user.has_permission(perm):
                return user
        raise AuthorizationError(
            f"One of these permissions required: {[p.value for p in permissions]}"
        )
    return check_permissions


# --- Optional auth (for endpoints that behave differently based on auth) ---

async def get_optional_user(
    user: Optional[User] = Depends(get_current_user),
) -> Optional[User]:
    """Get user if authenticated, None otherwise. Never raises."""
    return user


# --- Response helpers ---

def user_context(user: Optional[User]) -> dict:
    """Create a user context dict for audit logging."""
    if user:
        return {
            "user_id": user.id,
            "username": user.username,
            "role": user.role.value,
        }
    return {
        "user_id": "anonymous",
        "username": "anonymous",
        "role": "none",
    }


# --- Development/testing helpers ---

class DevAuthBypass:
    """Context manager to bypass auth in development/testing."""
    
    _bypass_enabled: bool = False
    _bypass_user: Optional[User] = None
    
    @classmethod
    def enable(cls, role: Role = Role.ADMIN):
        """Enable auth bypass with specified role."""
        cls._bypass_enabled = True
        cls._bypass_user = User(
            id="dev-bypass",
            username="dev-bypass",
            role=role,
            display_name="Development Bypass User",
        )
    
    @classmethod
    def disable(cls):
        """Disable auth bypass."""
        cls._bypass_enabled = False
        cls._bypass_user = None
    
    @classmethod
    def is_enabled(cls) -> bool:
        return cls._bypass_enabled
    
    @classmethod
    def get_user(cls) -> Optional[User]:
        return cls._bypass_user if cls._bypass_enabled else None


async def get_current_user_with_bypass(
    request: Request,
    api_key: Optional[str] = Depends(api_key_header),
    bearer: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[User]:
    """Get current user with development bypass support."""
    # Check bypass first
    if DevAuthBypass.is_enabled():
        return DevAuthBypass.get_user()
    
    # Fall back to normal auth
    return await get_current_user(request, api_key, bearer)
