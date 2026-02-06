"""FastAPI dependencies for authentication and authorization."""

from __future__ import annotations

import hashlib
from typing import Annotated

from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from homelab.storage.database import get_db
from homelab.auth.oidc import OIDCClient
# from homelab.auth.db_schema import UserDB, SessionDB, ServiceAccountDB # Moved to local scope
from homelab.auth.models import Role, Permission, role_has_permission
from datetime import datetime, timezone


# Security scheme
security = HTTPBearer(auto_error=False)


def _hash_token(token: str) -> str:
    """Hash a token for storage/lookup."""
    return hashlib.sha256(token.encode()).hexdigest()


async def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Extract and validate current user from JWT token.
    
    Returns user dict with id, email, name, role.
    Raises 401 if token is invalid or user not found.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    token_hash = _hash_token(token)
    
    # Local import to avoid circular dependency
    from homelab.auth.db_schema import UserDB, SessionDB
    
    # Look up session
    query = (
        select(SessionDB, UserDB)
        .join(UserDB, SessionDB.user_id == UserDB.id)
        .where(
            SessionDB.access_token_hash == token_hash,
            SessionDB.revoked_at.is_(None),
            SessionDB.expires_at > datetime.now(timezone.utc),
            UserDB.disabled == False,
        )
    )
    
    result = await db.execute(query)
    row = result.first()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    session, user = row
    
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "oidc_sub": user.oidc_sub,
    }


async def get_current_user_from_api_key(
    x_api_key: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
) -> dict | None:
    """Extract user from API key header.
    
    Returns user dict if API key is valid, None otherwise.
    """
    if not x_api_key:
        return None
    
    # API keys have format: hc_<prefix>_<secret>
    if not x_api_key.startswith("hc_"):
        return None
    
    api_key_hash = _hash_token(x_api_key)
    
    # Local import
    from homelab.auth.db_schema import ServiceAccountDB

    # Look up service account
    query = (
        select(ServiceAccountDB)
        .where(
            ServiceAccountDB.api_key_hash == api_key_hash,
            ServiceAccountDB.disabled == False,
        )
    )
    
    result = await db.execute(query)
    service_account = result.scalar_one_or_none()
    
    if not service_account:
        return None
    
    # Update last_used
    service_account.last_used = datetime.now(timezone.utc)
    await db.flush()
    
    return {
        "id": service_account.id,
        "email": f"{service_account.name}@service-account",
        "name": service_account.name,
        "role": service_account.role,
        "is_service_account": True,
    }


async def get_current_user(
    token_user: dict | None = Depends(get_current_user_from_token),
    api_key_user: dict | None = Depends(get_current_user_from_api_key),
) -> dict:
    """Get current user from either token or API key.
    
    Tries token first, then API key.
    Raises 401 if neither is valid.
    """
    # Try API key first (for service accounts)
    if api_key_user:
        return api_key_user
    
    # Then try token
    if token_user:
        return token_user
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_role(required_role: Role):
    """Dependency factory for role-based access control.
    
    Usage:
        @router.get("/admin")
        async def admin_endpoint(user: dict = Depends(require_role(Role.ADMIN))):
            ...
    """
    async def check_role(user: dict = Depends(get_current_user)) -> dict:
        user_role = Role(user["role"])
        
        # Check role hierarchy
        role_order = [Role.VIEWER, Role.OPERATOR, Role.APPROVER, Role.ADMIN]
        user_level = role_order.index(user_role)
        required_level = role_order.index(required_role)
        
        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {required_role.value} role or higher",
            )
        
        return user
    
    return check_role


def require_permission(permission: Permission):
    """Dependency factory for permission-based access control.
    
    Usage:
        @router.post("/tasks")
        async def create_task(user: dict = Depends(require_permission(Permission.CREATE_EXECUTION))):
            ...
    """
    async def check_permission(user: dict = Depends(get_current_user)) -> dict:
        user_role = Role(user["role"])
        
        if not role_has_permission(user_role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {permission.value}",
            )
        
        return user
    
    return check_permission


# Type alias for dependency injection
CurrentUser = Annotated[dict, Depends(get_current_user)]
