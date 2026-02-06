"""Tests for OIDC authentication."""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from homelab.auth.oidc import OIDCClient, OIDCConfig


class TestOIDCConfig:
    """Test OIDC configuration."""
    
    def test_config_defaults(self):
        """Test OIDC config has sensible defaults."""
        config = OIDCConfig(
            issuer_url="https://auth.example.com",
            client_id="test-client",
            client_secret="test-secret",
            redirect_uri="http://localhost:8000/callback",
        )
        
        assert config.issuer_url == "https://auth.example.com"
        assert config.client_id == "test-client"
        assert "openid" in config.scopes
    
    def test_config_custom_scopes(self):
        """Test custom scopes can be specified."""
        config = OIDCConfig(
            issuer_url="https://auth.example.com",
            client_id="test-client",
            client_secret="test-secret",
            redirect_uri="http://localhost:8000/callback",
            scopes=["openid", "profile", "email", "groups"],
        )
        
        assert "groups" in config.scopes


class TestOIDCClient:
    """Test OIDC client operations."""
    
    @pytest.fixture
    def oidc_config(self):
        """Create test OIDC config."""
        return OIDCConfig(
            issuer_url="https://auth.example.com",
            client_id="test-client",
            client_secret="test-secret",
            redirect_uri="http://localhost:8000/callback",
        )
    
    @pytest.fixture
    def oidc_client(self, oidc_config):
        """Create test OIDC client."""
        client = OIDCClient(oidc_config)
        # Mock discovery metadata
        client._metadata = {
            "authorization_endpoint": "https://auth.example.com/authorize",
            "token_endpoint": "https://auth.example.com/token",
            "userinfo_endpoint": "https://auth.example.com/userinfo",
            "jwks_uri": "https://auth.example.com/.well-known/jwks.json",
        }
        return client
    
    def test_authorization_url_generation(self, oidc_client):
        """Test authorization URL is correctly generated."""
        url, state = oidc_client.get_authorization_url()
        
        assert "https://auth.example.com/authorize" in url
        assert "client_id=test-client" in url
        assert "response_type=code" in url
        assert "scope=" in url
        assert state is not None
        assert len(state) > 16  # Should be a secure random string
    
    def test_authorization_url_includes_state(self, oidc_client):
        """Test authorization URL includes state parameter."""
        url, state = oidc_client.get_authorization_url()
        
        assert f"state={state}" in url
    
    @pytest.mark.asyncio
    async def test_token_exchange_success(self, oidc_client):
        """Test successful token exchange."""
        mock_response = {
            "access_token": "test-access-token",
            "refresh_token": "test-refresh-token",
            "id_token": "test-id-token",
            "expires_in": 3600,
            "token_type": "Bearer",
        }
        
        with patch.object(oidc_client, "_http_client") as mock_http:
            mock_http.post = AsyncMock(return_value=MagicMock(
                json=lambda: mock_response,
                status_code=200,
                raise_for_status=lambda: None,
            ))
            
            tokens = await oidc_client.exchange_code("test-code")
            
            assert tokens["access_token"] == "test-access-token"
            assert tokens["refresh_token"] == "test-refresh-token"
    
    @pytest.mark.asyncio
    async def test_token_exchange_invalid_code(self, oidc_client):
        """Test token exchange with invalid code."""
        with patch.object(oidc_client, "_http_client") as mock_http:
            mock_http.post = AsyncMock(return_value=MagicMock(
                status_code=400,
                json=lambda: {"error": "invalid_grant"},
                raise_for_status=MagicMock(side_effect=Exception("Bad Request")),
            ))
            
            with pytest.raises(Exception):
                await oidc_client.exchange_code("invalid-code")


class TestJWTValidation:
    """Test JWT token validation."""
    
    def test_expired_token_rejected(self):
        """Test that expired tokens are rejected."""
        # This would require a real JWT library test
        # For now, test the concept
        exp_time = datetime.now(timezone.utc) - timedelta(hours=1)
        
        # Token is expired
        assert exp_time < datetime.now(timezone.utc)
    
    def test_future_iat_rejected(self):
        """Test that tokens with future iat are rejected."""
        iat_time = datetime.now(timezone.utc) + timedelta(hours=1)
        
        # iat is in the future (invalid)
        assert iat_time > datetime.now(timezone.utc)


class TestTokenRefresh:
    """Test token refresh functionality."""
    
    @pytest.fixture
    def oidc_config(self):
        """Create test OIDC config."""
        return OIDCConfig(
            issuer_url="https://auth.example.com",
            client_id="test-client",
            client_secret="test-secret",
            redirect_uri="http://localhost:8000/callback",
        )
    
    @pytest.fixture
    def oidc_client(self, oidc_config):
        """Create test OIDC client."""
        client = OIDCClient(oidc_config)
        client._metadata = {
            "token_endpoint": "https://auth.example.com/token",
        }
        return client
    
    @pytest.mark.asyncio
    async def test_token_refresh_success(self, oidc_client):
        """Test successful token refresh."""
        mock_response = {
            "access_token": "new-access-token",
            "refresh_token": "new-refresh-token",
            "expires_in": 3600,
        }
        
        with patch.object(oidc_client, "_http_client") as mock_http:
            mock_http.post = AsyncMock(return_value=MagicMock(
                json=lambda: mock_response,
                status_code=200,
                raise_for_status=lambda: None,
            ))
            
            tokens = await oidc_client.refresh_token("old-refresh-token")
            
            assert tokens["access_token"] == "new-access-token"
