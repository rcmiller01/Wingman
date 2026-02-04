"""Auth data models and role definitions."""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


class Role(str, Enum):
    """User roles with increasing privilege levels."""
    VIEWER = "viewer"       # Read-only access to everything
    OPERATOR = "operator"   # Create executions, execute Tier 1 (low-risk)
    APPROVER = "approver"   # Approve/reject Tier 2/3 executions
    ADMIN = "admin"         # Full access: allowlists, dangerous toggles


class Permission(str, Enum):
    """Granular permissions for RBAC."""
    # Read permissions
    READ_EXECUTIONS = "read:executions"
    READ_SKILLS = "read:skills"
    READ_INVENTORY = "read:inventory"
    READ_LOGS = "read:logs"
    READ_INCIDENTS = "read:incidents"
    READ_SETTINGS = "read:settings"
    READ_ALLOWLISTS = "read:allowlists"
    
    # Write permissions
    CREATE_EXECUTION = "create:execution"
    EXECUTE_TIER1 = "execute:tier1"       # Low-risk skills
    EXECUTE_TIER2 = "execute:tier2"       # Medium-risk skills
    EXECUTE_TIER3 = "execute:tier3"       # High-risk skills
    
    # Approval permissions
    APPROVE_TIER2 = "approve:tier2"       # Approve medium-risk
    APPROVE_TIER3 = "approve:tier3"       # Approve high-risk
    REJECT_EXECUTION = "reject:execution"
    
    # Admin permissions
    MANAGE_ALLOWLISTS = "manage:allowlists"
    MANAGE_SETTINGS = "manage:settings"
    MANAGE_USERS = "manage:users"
    TOGGLE_DANGEROUS = "toggle:dangerous"
    FORCE_LAB_MODE = "force:lab_mode"


# Role -> Permission mapping
ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.VIEWER: {
        Permission.READ_EXECUTIONS,
        Permission.READ_SKILLS,
        Permission.READ_INVENTORY,
        Permission.READ_LOGS,
        Permission.READ_INCIDENTS,
        Permission.READ_SETTINGS,
        Permission.READ_ALLOWLISTS,
    },
    
    Role.OPERATOR: {
        # All viewer permissions
        Permission.READ_EXECUTIONS,
        Permission.READ_SKILLS,
        Permission.READ_INVENTORY,
        Permission.READ_LOGS,
        Permission.READ_INCIDENTS,
        Permission.READ_SETTINGS,
        Permission.READ_ALLOWLISTS,
        # Plus operator permissions
        Permission.CREATE_EXECUTION,
        Permission.EXECUTE_TIER1,
    },
    
    Role.APPROVER: {
        # All operator permissions
        Permission.READ_EXECUTIONS,
        Permission.READ_SKILLS,
        Permission.READ_INVENTORY,
        Permission.READ_LOGS,
        Permission.READ_INCIDENTS,
        Permission.READ_SETTINGS,
        Permission.READ_ALLOWLISTS,
        Permission.CREATE_EXECUTION,
        Permission.EXECUTE_TIER1,
        # Plus approver permissions
        Permission.EXECUTE_TIER2,
        Permission.APPROVE_TIER2,
        Permission.APPROVE_TIER3,
        Permission.REJECT_EXECUTION,
    },
    
    Role.ADMIN: {
        # All permissions
        Permission.READ_EXECUTIONS,
        Permission.READ_SKILLS,
        Permission.READ_INVENTORY,
        Permission.READ_LOGS,
        Permission.READ_INCIDENTS,
        Permission.READ_SETTINGS,
        Permission.READ_ALLOWLISTS,
        Permission.CREATE_EXECUTION,
        Permission.EXECUTE_TIER1,
        Permission.EXECUTE_TIER2,
        Permission.EXECUTE_TIER3,
        Permission.APPROVE_TIER2,
        Permission.APPROVE_TIER3,
        Permission.REJECT_EXECUTION,
        Permission.MANAGE_ALLOWLISTS,
        Permission.MANAGE_SETTINGS,
        Permission.MANAGE_USERS,
        Permission.TOGGLE_DANGEROUS,
        Permission.FORCE_LAB_MODE,
    },
}


def get_permissions_for_role(role: Role) -> set[Permission]:
    """Get all permissions granted to a role."""
    return ROLE_PERMISSIONS.get(role, set())


def role_has_permission(role: Role, permission: Permission) -> bool:
    """Check if a role has a specific permission."""
    return permission in ROLE_PERMISSIONS.get(role, set())


@dataclass
class User:
    """User account for authentication."""
    id: str
    username: str
    role: Role
    display_name: str = ""
    email: Optional[str] = None
    api_key_hash: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    is_active: bool = True
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if user has a specific permission."""
        return role_has_permission(self.role, permission)
    
    def has_role(self, role: Role) -> bool:
        """Check if user has at least the specified role level."""
        role_order = [Role.VIEWER, Role.OPERATOR, Role.APPROVER, Role.ADMIN]
        user_level = role_order.index(self.role)
        required_level = role_order.index(role)
        return user_level >= required_level
    
    def to_dict(self) -> dict:
        """Convert to dictionary (safe for API responses)."""
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role.value,
            "display_name": self.display_name or self.username,
            "email": self.email,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "is_active": self.is_active,
        }


# Risk tier to permission mapping
RISK_TO_PERMISSION: dict[str, Permission] = {
    "low": Permission.EXECUTE_TIER1,
    "medium": Permission.EXECUTE_TIER2,
    "high": Permission.EXECUTE_TIER3,
}

RISK_TO_APPROVAL_PERMISSION: dict[str, Permission] = {
    "medium": Permission.APPROVE_TIER2,
    "high": Permission.APPROVE_TIER3,
}


def get_execute_permission_for_risk(risk: str) -> Permission:
    """Get the permission required to execute a skill of given risk."""
    return RISK_TO_PERMISSION.get(risk.lower(), Permission.EXECUTE_TIER3)


def get_approval_permission_for_risk(risk: str) -> Optional[Permission]:
    """Get the permission required to approve a skill of given risk."""
    return RISK_TO_APPROVAL_PERMISSION.get(risk.lower())
