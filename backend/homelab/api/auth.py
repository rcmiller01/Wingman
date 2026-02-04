"""Auth API endpoints for login, user management, and token operations."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from homelab.auth import (
    User,
    Role,
    Permission,
    user_store,
    get_current_user,
    require_auth,
    require_role,
    require_permission,
    create_session_token,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


# --- Request/Response Models ---

class LoginRequest(BaseModel):
    """Login with username/password (for future use) or API key."""
    api_key: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None  # Not implemented yet


class LoginResponse(BaseModel):
    """Login response with session token and user info."""
    token: str
    user: dict
    expires_in_seconds: int = 86400  # 24 hours


class UserResponse(BaseModel):
    """User information response."""
    id: str
    username: str
    role: str
    display_name: str
    email: Optional[str]
    created_at: Optional[str]
    last_login: Optional[str]
    is_active: bool


class CreateUserRequest(BaseModel):
    """Request to create a new user."""
    username: str
    role: str
    display_name: Optional[str] = None
    email: Optional[str] = None


class CreateUserResponse(BaseModel):
    """Response with new user info and API key (shown only once)."""
    user: dict
    api_key: str  # Only shown at creation time!


class UpdateRoleRequest(BaseModel):
    """Request to update a user's role."""
    role: str


class WhoAmIResponse(BaseModel):
    """Response for current user info."""
    authenticated: bool
    user: Optional[dict] = None
    permissions: list[str] = []


# --- Public Endpoints ---

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Login and get a session token.
    
    Currently supports API key authentication.
    Username/password auth can be added later.
    """
    user = None
    
    if request.api_key:
        user = user_store.get_user_by_api_key(request.api_key)
    
    # Future: username/password auth
    # elif request.username and request.password:
    #     user = authenticate_password(request.username, request.password)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not user.is_active:
        raise HTTPException(status_code=401, detail="User account is deactivated")
    
    # Record login
    user_store.record_login(user.id)
    
    # Create session token
    token = create_session_token(
        user_id=user.id,
        username=user.username,
        role=user.role.value,
    )
    
    return LoginResponse(
        token=token,
        user=user.to_dict(),
        expires_in_seconds=86400,
    )


@router.get("/whoami", response_model=WhoAmIResponse)
async def whoami(user: Optional[User] = Depends(get_current_user)):
    """Get information about the current authenticated user."""
    if not user:
        return WhoAmIResponse(authenticated=False)
    
    from homelab.auth.models import ROLE_PERMISSIONS
    permissions = [p.value for p in ROLE_PERMISSIONS.get(user.role, set())]
    
    return WhoAmIResponse(
        authenticated=True,
        user=user.to_dict(),
        permissions=permissions,
    )


@router.get("/dev-keys")
async def get_dev_keys():
    """Get development API keys (only available in dev mode).
    
    These are predictable keys for testing each role.
    """
    from homelab.config import get_settings
    settings = get_settings()
    
    # Only allow in development
    if settings.environment == "production":
        raise HTTPException(
            status_code=403,
            detail="Dev keys not available in production"
        )
    
    from homelab.auth.store import get_default_api_keys
    return {
        "message": "Development API keys for testing",
        "warning": "These keys are only for development/testing",
        "keys": get_default_api_keys(),
        "usage": "Add header: X-API-Key: <key>",
    }


# --- Protected Endpoints ---

@router.get("/users", response_model=list[UserResponse])
async def list_users(
    include_inactive: bool = False,
    user: User = Depends(require_permission(Permission.MANAGE_USERS)),
):
    """List all users (admin only)."""
    users = user_store.list_users(include_inactive=include_inactive)
    return [
        UserResponse(
            id=u.id,
            username=u.username,
            role=u.role.value,
            display_name=u.display_name,
            email=u.email,
            created_at=u.created_at.isoformat() if u.created_at else None,
            last_login=u.last_login.isoformat() if u.last_login else None,
            is_active=u.is_active,
        )
        for u in users
    ]


@router.post("/users", response_model=CreateUserResponse)
async def create_user(
    request: CreateUserRequest,
    user: User = Depends(require_permission(Permission.MANAGE_USERS)),
):
    """Create a new user (admin only).
    
    Returns the API key which is only shown once!
    """
    # Validate role
    try:
        role = Role(request.role)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role: {request.role}. Must be one of: {[r.value for r in Role]}"
        )
    
    # Check if username exists
    if user_store.get_user_by_username(request.username):
        raise HTTPException(
            status_code=400,
            detail=f"Username '{request.username}' already exists"
        )
    
    new_user, api_key = user_store.create_user(
        username=request.username,
        role=role,
        display_name=request.display_name,
        email=request.email,
    )
    
    return CreateUserResponse(
        user=new_user.to_dict(),
        api_key=api_key,
    )


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: User = Depends(require_auth),
):
    """Get a specific user's info.
    
    Users can view their own info; admins can view anyone.
    """
    # Allow users to view themselves
    if user_id != current_user.id:
        if not current_user.has_permission(Permission.MANAGE_USERS):
            raise HTTPException(status_code=403, detail="Cannot view other users")
    
    target_user = user_store.get_user(user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse(
        id=target_user.id,
        username=target_user.username,
        role=target_user.role.value,
        display_name=target_user.display_name,
        email=target_user.email,
        created_at=target_user.created_at.isoformat() if target_user.created_at else None,
        last_login=target_user.last_login.isoformat() if target_user.last_login else None,
        is_active=target_user.is_active,
    )


@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    request: UpdateRoleRequest,
    current_user: User = Depends(require_permission(Permission.MANAGE_USERS)),
):
    """Update a user's role (admin only)."""
    try:
        new_role = Role(request.role)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role: {request.role}"
        )
    
    # Can't change your own role
    if user_id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot change your own role"
        )
    
    updated_user = user_store.update_user_role(user_id, new_role)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "Role updated", "user": updated_user.to_dict()}


@router.delete("/users/{user_id}")
async def deactivate_user(
    user_id: str,
    current_user: User = Depends(require_permission(Permission.MANAGE_USERS)),
):
    """Deactivate a user (soft delete)."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot deactivate yourself"
        )
    
    success = user_store.deactivate_user(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "User deactivated"}


@router.post("/users/{user_id}/regenerate-key")
async def regenerate_api_key(
    user_id: str,
    current_user: User = Depends(require_auth),
):
    """Regenerate a user's API key.
    
    Users can regenerate their own key; admins can regenerate anyone's.
    """
    if user_id != current_user.id:
        if not current_user.has_permission(Permission.MANAGE_USERS):
            raise HTTPException(status_code=403, detail="Cannot regenerate other users' keys")
    
    new_key = user_store.regenerate_api_key(user_id)
    if not new_key:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "message": "API key regenerated",
        "api_key": new_key,
        "warning": "Save this key - it will not be shown again!",
    }
