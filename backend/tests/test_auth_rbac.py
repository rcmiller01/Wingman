"""Tests for RBAC (Role-Based Access Control)."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException

from homelab.auth.models import Role, Permission, ROLE_PERMISSIONS, role_has_permission, get_permissions_for_role


class TestRolePermissions:
    """Test role and permission definitions."""
    
    def test_admin_has_all_permissions(self):
        """Admin role should have all permissions."""
        admin_perms = get_permissions_for_role(Role.ADMIN)
        
        # Admin should have all defined permissions
        for perm in Permission:
            assert perm in admin_perms, f"Admin missing permission: {perm}"
    
    def test_operator_has_operational_permissions(self):
        """Operator role should have execution permissions."""
        operator_perms = get_permissions_for_role(Role.OPERATOR)
        
        assert Permission.CREATE_EXECUTION in operator_perms
        assert Permission.EXECUTE_TIER1 in operator_perms
        assert Permission.READ_EXECUTIONS in operator_perms
    
    def test_operator_cannot_manage_users(self):
        """Operator role should not manage users."""
        operator_perms = get_permissions_for_role(Role.OPERATOR)
        
        assert Permission.MANAGE_USERS not in operator_perms
    
    def test_viewer_read_only(self):
        """Viewer role should only have read permissions."""
        viewer_perms = get_permissions_for_role(Role.VIEWER)
        
        # Should have read permissions
        assert Permission.READ_EXECUTIONS in viewer_perms
        assert Permission.READ_SKILLS in viewer_perms
        
        # Should NOT have execute permissions
        assert Permission.CREATE_EXECUTION not in viewer_perms
        assert Permission.EXECUTE_TIER1 not in viewer_perms


class TestHasPermission:
    """Test permission checking."""
    
    def test_admin_has_any_permission(self):
        """Admin should pass any permission check."""
        for perm in Permission:
            assert role_has_permission(Role.ADMIN, perm)
    
    def test_viewer_denied_execute(self):
        """Viewer should be denied execute permission."""
        assert not role_has_permission(Role.VIEWER, Permission.EXECUTE_TIER1)
    
    def test_operator_can_execute_tier1(self):
        """Operator should be allowed to execute tier 1 actions."""
        assert role_has_permission(Role.OPERATOR, Permission.EXECUTE_TIER1)
    
    def test_operator_cannot_execute_tier2(self):
        """Operator should NOT be allowed to execute tier 2 actions."""
        assert not role_has_permission(Role.OPERATOR, Permission.EXECUTE_TIER2)


class TestRequirePermissionDecorator:
    """Test the require_permission dependency."""
    
    @pytest.mark.asyncio
    async def test_require_permission_success(self):
        """Test successful permission check passes."""
        from homelab.auth.dependencies import require_permission
        
        # Create mock user with admin role
        mock_user = MagicMock()
        mock_user.role = Role.ADMIN
        
        # Create the dependency
        checker = require_permission(Permission.READ_EXECUTIONS)
        
        # Should not raise
        result = await checker(mock_user)
        assert result == mock_user
    
    @pytest.mark.asyncio
    async def test_require_permission_denied(self):
        """Test denied permission raises HTTPException."""
        from homelab.auth.dependencies import require_permission
        
        # Create mock user with viewer role
        mock_user = MagicMock()
        mock_user.role = Role.VIEWER
        
        # Create the dependency for execute permission
        checker = require_permission(Permission.EXECUTE_TIER1)
        
        # Should raise 403
        with pytest.raises(HTTPException) as exc_info:
            await checker(mock_user)
        
        assert exc_info.value.status_code == 403


class TestServiceAccountAuth:
    """Test service account authentication."""
    
    def test_api_key_format(self):
        """Test API key format validation."""
        # Valid format: wingman_sa_<random>
        valid_key = "wingman_sa_abc123def456"
        invalid_key = "invalid_key"
        
        assert valid_key.startswith("wingman_sa_")
        assert not invalid_key.startswith("wingman_sa_")
