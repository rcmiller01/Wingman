"""OpenID Connect (OIDC) authentication client."""

from __future__ import annotations

import httpx
from datetime import datetime, timezone, timedelta
from typing import Any
from pydantic import BaseModel, Field

from jose import jwt, JWTError


class OIDCConfig(BaseModel):
    """OIDC provider configuration."""
    
    issuer: str = Field(..., description="OIDC issuer URL (e.g., https://accounts.google.com)")
    client_id: str = Field(..., description="OAuth2 client ID")
    client_secret: str = Field(..., description="OAuth2 client secret")
    redirect_uri: str = Field(..., description="Redirect URI after authentication")
    scopes: list[str] = Field(default=["openid", "profile", "email"], description="OAuth2 scopes")
    
    # Discovered endpoints (populated from .well-known/openid-configuration)
    authorization_endpoint: str | None = None
    token_endpoint: str | None = None
    userinfo_endpoint: str | None = None
    jwks_uri: str | None = None


class OIDCClient:
    """OIDC client for authentication flows."""
    
    def __init__(self, config: OIDCConfig):
        self.config = config
        self._jwks_cache: dict[str, Any] | None = None
        self._jwks_cache_time: datetime | None = None
    
    async def discover_endpoints(self) -> None:
        """Discover OIDC endpoints from .well-known/openid-configuration."""
        discovery_url = f"{self.config.issuer.rstrip('/')}/.well-known/openid-configuration"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(discovery_url)
            response.raise_for_status()
            discovery = response.json()
        
        self.config.authorization_endpoint = discovery["authorization_endpoint"]
        self.config.token_endpoint = discovery["token_endpoint"]
        self.config.userinfo_endpoint = discovery.get("userinfo_endpoint")
        self.config.jwks_uri = discovery["jwks_uri"]
    
    def get_authorization_url(self, state: str) -> str:
        """Generate authorization URL for login redirect.
        
        Args:
            state: Random state parameter for CSRF protection
        
        Returns:
            Authorization URL to redirect user to
        """
        if not self.config.authorization_endpoint:
            raise ValueError("Authorization endpoint not configured. Call discover_endpoints() first.")
        
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.config.scopes),
            "state": state,
        }
        
        query_string = "&".join(f"{k}={httpx.QueryParams({k: v})[k]}" for k, v in params.items())
        return f"{self.config.authorization_endpoint}?{query_string}"
    
    async def exchange_code_for_tokens(self, code: str) -> dict[str, Any]:
        """Exchange authorization code for access/refresh tokens.
        
        Args:
            code: Authorization code from callback
        
        Returns:
            Token response with access_token, refresh_token (optional), id_token
        """
        if not self.config.token_endpoint:
            raise ValueError("Token endpoint not configured. Call discover_endpoints() first.")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.config.token_endpoint,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self.config.redirect_uri,
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            return response.json()
    
    async def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        """Refresh access token using refresh token.
        
        Args:
            refresh_token: Refresh token from previous token exchange
        
        Returns:
            New token response with access_token
        """
        if not self.config.token_endpoint:
            raise ValueError("Token endpoint not configured. Call discover_endpoints() first.")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.config.token_endpoint,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            return response.json()
    
    async def validate_token(self, token: str) -> dict[str, Any]:
        """Validate JWT token and return claims.
        
        Args:
            token: JWT access token or ID token
        
        Returns:
            Token claims (payload)
        
        Raises:
            JWTError: If token is invalid or expired
        """
        # Get JWKS (with caching)
        jwks = await self._get_jwks()
        
        # Decode and validate token
        try:
            # Get token header to find key ID
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            
            # Find matching key
            key = None
            for jwk in jwks.get("keys", []):
                if jwk.get("kid") == kid:
                    key = jwk
                    break
            
            if not key:
                raise JWTError("No matching key found in JWKS")
            
            # Validate token
            claims = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self.config.client_id,
                issuer=self.config.issuer,
            )
            
            return claims
        
        except JWTError as e:
            raise JWTError(f"Token validation failed: {str(e)}")
    
    async def _get_jwks(self) -> dict[str, Any]:
        """Get JWKS (JSON Web Key Set) with caching."""
        # Cache for 1 hour
        if self._jwks_cache and self._jwks_cache_time:
            age = datetime.now(timezone.utc) - self._jwks_cache_time
            if age < timedelta(hours=1):
                return self._jwks_cache
        
        if not self.config.jwks_uri:
            raise ValueError("JWKS URI not configured. Call discover_endpoints() first.")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(self.config.jwks_uri)
            response.raise_for_status()
            jwks = response.json()
        
        self._jwks_cache = jwks
        self._jwks_cache_time = datetime.now(timezone.utc)
        
        return jwks
    
    async def get_userinfo(self, access_token: str) -> dict[str, Any]:
        """Get user information from userinfo endpoint.
        
        Args:
            access_token: Access token
        
        Returns:
            User information (sub, email, name, etc.)
        """
        if not self.config.userinfo_endpoint:
            raise ValueError("Userinfo endpoint not configured. Call discover_endpoints() first.")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.config.userinfo_endpoint,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json()
