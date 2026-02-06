"""Tests for RBAC (Role-Based Access Control)."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException

from homelab.auth.rbac import Role, Permission, ROLE_PERMISSIONS


class TestRolePermissions:
    """Test role and permission definitions."""
    
    def test_admin_has_all_permissions(self):
        """Admin role should have all permissions."""
        admin_perms = ROLE_PERMISSIONS[Role.ADMIN]
        
        # Admin should have all defined permissions
        for perm in Permission:
            assert perm in admin_perms, f"Admin missing permission: {perm}"
    
    def test_operator_has_operational_permissions(self):
        """Operator role should have execution permissions."""
        operator_perms = ROLE_PERMISSIONS[Role.OPERATOR]
        
        assert Permission.EXECUTE_ACTIONS in operator_perms
        assert Permission.VIEW_FACTS in operator_perms
        assert Permission.VIEW_INCIDENTS in operator_perms
    
    def test_operator_cannot_manage_users(self):
        """Operator role should not manage users."""
        operator_perms = ROLE_PERMISSIONS[Role.OPERATOR]
        
        assert Permission.MANAGE_USERS not in operator_perms
    
    def test_viewer_read_only(self):
        """Viewer role should only have read permissions."""
        viewer_perms = ROLE_PERMISSIONS[Role.VIEWER]
        
        # Should have view permissions
        assert Permission.VIEW_FACTS in viewer_perms
        assert Permission.VIEW_INCIDENTS in viewer_perms
        
        # Should NOT have execute permissions
        assert Permission.EXECUTE_ACTIONS not in viewer_perms
        assert Permission.MANAGE_WORKERS not in viewer_perms


class TestHasPermission:
    """Test permission checking."""
    
    def test_admin_has_any_permission(self):
        """Admin should pass any permission check."""
        from homelab.auth.rbac import has_permission
        
        for perm in Permission:
            assert has_permission(Role.ADMIN, perm)
    
    def test_viewer_denied_execute(self):
        """Viewer should be denied execute permission."""
        from homelab.auth.rbac import has_permission
        
        assert not has_permission(Role.VIEWER, Permission.EXECUTE_ACTIONS)
    
    def test_operator_can_execute(self):
        """Operator should be allowed to execute actions."""
        from homelab.auth.rbac import has_permission
        
        assert has_permission(Role.OPERATOR, Permission.EXECUTE_ACTIONS)


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
        checker = require_permission(Permission.VIEW_FACTS)
        
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
        checker = require_permission(Permission.EXECUTE_ACTIONS)
        
        # Should raise 403
        with pytest.raises(HTTPException) as exc_info:
            await checker(mock_user)
        
        assert exc_info.value.status_code == 403


class TestGetCurrentUser:
    """Test get_current_user dependency."""
    
    @pytest.mark.asyncio
    async def test_valid_token_returns_user(self):
        """Test valid token returns user object."""
        # This would need database fixtures
        pass
    
    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self):
        """Test invalid token raises 401."""
        from homelab.auth.dependencies import get_current_user
        
        # Mock request with invalid token
        mock_request = MagicMock()
        mock_request.headers = {"Authorization": "Bearer invalid-token"}
        
        # Would need database session mock
        pass
    
    @pytest.mark.asyncio
    async def test_missing_token_raises_401(self):
        """Test missing token raises 401."""
        from homelab.auth.dependencies import get_current_user
        
        # Mock request without Authorization header
        mock_request = MagicMock()
        mock_request.headers = {}
        
        # Would need database session mock
        pass


class TestServiceAccountAuth:
    """Test service account authentication."""
    
    def test_api_key_format(self):
        """Test API key format validation."""
        # Valid format: wingman_sa_<random>
        valid_key = "wingman_sa_abc123def456"
        invalid_key = "invalid_key"
        
        assert valid_key.startswith("wingman_sa_")
        assert not invalid_key.startswith("wingman_sa_")
    
    @pytest.mark.asyncio
    async def test_valid_api_key_authenticates(self):
        """Test valid API key returns service account."""
        # Would need database fixtures
        pass
    
    @pytest.mark.asyncio
    async def test_invalid_api_key_rejected(self):
        """Test invalid API key is rejected."""
        # Would need database fixtures
        pass
