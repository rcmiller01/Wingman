"""In-memory user store for development/testing.

In production, this would be backed by a database.
Ships with default users for each role to enable immediate testing.
"""

from typing import Optional, Dict
from datetime import datetime, timezone
from uuid import uuid4

from .models import User, Role
from .tokens import create_api_key, validate_api_key


class UserStore:
    """Simple in-memory user store with default users."""
    
    def __init__(self):
        self._users: Dict[str, User] = {}
        self._api_keys: Dict[str, str] = {}  # key_hash -> user_id
        self._init_default_users()
    
    def _init_default_users(self):
        """Create default users for each role."""
        # Default users with predictable API keys for development
        defaults = [
            ("viewer", Role.VIEWER, "Viewer User"),
            ("operator", Role.OPERATOR, "Operator User"),
            ("approver", Role.APPROVER, "Approver User"),
            ("admin", Role.ADMIN, "Admin User"),
        ]
        
        for username, role, display_name in defaults:
            user_id = f"default-{username}"
            user = User(
                id=user_id,
                username=username,
                role=role,
                display_name=display_name,
                email=f"{username}@wingman.local",
            )
            self._users[user_id] = user
            
            # Create a predictable dev API key
            # Format: wm_dev_{role}_key
            dev_key = f"wm_dev_{role.value}_key"
            key_hash = self._hash_key(dev_key)
            user.api_key_hash = key_hash
            self._api_keys[key_hash] = user_id
    
    def _hash_key(self, key: str) -> str:
        """Hash an API key."""
        import hashlib
        return hashlib.sha256(key.encode()).hexdigest()
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get a user by ID."""
        return self._users.get(user_id)
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get a user by username."""
        for user in self._users.values():
            if user.username == username:
                return user
        return None
    
    def get_user_by_api_key(self, api_key: str) -> Optional[User]:
        """Validate an API key and return the user if valid."""
        key_hash = self._hash_key(api_key)
        user_id = self._api_keys.get(key_hash)
        if user_id:
            user = self._users.get(user_id)
            if user and user.is_active:
                return user
        return None
    
    def create_user(
        self,
        username: str,
        role: Role,
        display_name: str = "",
        email: Optional[str] = None,
    ) -> tuple[User, str]:
        """Create a new user and return (user, api_key).
        
        The API key is only returned once at creation time.
        """
        user_id = str(uuid4())
        
        # Generate API key
        api_key, key_hash = create_api_key(user_id)
        
        user = User(
            id=user_id,
            username=username,
            role=role,
            display_name=display_name or username,
            email=email,
            api_key_hash=key_hash,
        )
        
        self._users[user_id] = user
        self._api_keys[key_hash] = user_id
        
        return user, api_key
    
    def update_user_role(self, user_id: str, new_role: Role) -> Optional[User]:
        """Update a user's role."""
        user = self._users.get(user_id)
        if user:
            user.role = new_role
        return user
    
    def deactivate_user(self, user_id: str) -> bool:
        """Deactivate a user (soft delete)."""
        user = self._users.get(user_id)
        if user:
            user.is_active = False
            return True
        return False
    
    def regenerate_api_key(self, user_id: str) -> Optional[str]:
        """Regenerate a user's API key. Returns new key (only shown once)."""
        user = self._users.get(user_id)
        if not user:
            return None
        
        # Remove old key
        if user.api_key_hash:
            self._api_keys.pop(user.api_key_hash, None)
        
        # Generate new key
        api_key, key_hash = create_api_key(user_id)
        user.api_key_hash = key_hash
        self._api_keys[key_hash] = user_id
        
        return api_key
    
    def list_users(self, include_inactive: bool = False) -> list[User]:
        """List all users."""
        users = list(self._users.values())
        if not include_inactive:
            users = [u for u in users if u.is_active]
        return users
    
    def record_login(self, user_id: str) -> None:
        """Record a user login."""
        user = self._users.get(user_id)
        if user:
            user.last_login = datetime.now(timezone.utc)


# Global user store instance
user_store = UserStore()


# Convenience functions
def get_default_api_keys() -> dict[str, str]:
    """Get the default development API keys.
    
    Returns dict of role -> api_key for testing.
    """
    return {
        "viewer": "wm_dev_viewer_key",
        "operator": "wm_dev_operator_key",
        "approver": "wm_dev_approver_key",
        "admin": "wm_dev_admin_key",
    }
