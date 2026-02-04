"""Token generation and validation for API keys and sessions."""

import secrets
import hashlib
import hmac
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
import base64
import json

# Secret key for signing tokens (in production, load from env/secrets manager)
_SECRET_KEY: str = "wingman-dev-secret-change-in-production"


def set_secret_key(key: str) -> None:
    """Set the secret key for token operations."""
    global _SECRET_KEY
    _SECRET_KEY = key


def _hash_key(key: str) -> str:
    """Create a hash of an API key for storage."""
    return hashlib.sha256(key.encode()).hexdigest()


def _sign_token(payload: str) -> str:
    """Sign a payload with HMAC."""
    signature = hmac.new(
        _SECRET_KEY.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return signature


# --- API Keys ---

def create_api_key(user_id: str, prefix: str = "wm") -> Tuple[str, str]:
    """Create a new API key.
    
    Returns:
        Tuple of (full_key, key_hash)
        - full_key: The complete key to give to the user (only shown once)
        - key_hash: The hash to store in the database
    """
    # Generate 32 random bytes -> 64 hex chars
    random_part = secrets.token_hex(32)
    
    # Format: prefix_userid_random
    # e.g., wm_user123_a1b2c3d4...
    full_key = f"{prefix}_{user_id[:8]}_{random_part}"
    key_hash = _hash_key(full_key)
    
    return full_key, key_hash


def validate_api_key(key: str, stored_hash: str) -> bool:
    """Validate an API key against its stored hash."""
    key_hash = _hash_key(key)
    return hmac.compare_digest(key_hash, stored_hash)


def get_user_id_from_api_key(key: str) -> Optional[str]:
    """Extract user ID hint from API key format."""
    try:
        parts = key.split("_")
        if len(parts) >= 2:
            return parts[1]  # The user ID prefix
    except Exception:
        pass
    return None


# --- Session Tokens ---

def create_session_token(
    user_id: str,
    username: str,
    role: str,
    expires_in: timedelta = timedelta(hours=24)
) -> str:
    """Create a signed session token.
    
    The token contains user info and expiration, signed with HMAC.
    """
    now = datetime.now(timezone.utc)
    expires_at = now + expires_in
    
    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "issued_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
    }
    
    # Encode payload
    payload_json = json.dumps(payload, separators=(",", ":"))
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode()
    
    # Sign it
    signature = _sign_token(payload_b64)
    
    # Format: payload.signature
    return f"{payload_b64}.{signature}"


def validate_session_token(token: str) -> Optional[dict]:
    """Validate a session token and return the payload if valid.
    
    Returns:
        The payload dict if valid, None if invalid or expired.
    """
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        
        payload_b64, signature = parts
        
        # Verify signature
        expected_signature = _sign_token(payload_b64)
        if not hmac.compare_digest(signature, expected_signature):
            return None
        
        # Decode payload
        payload_json = base64.urlsafe_b64decode(payload_b64).decode()
        payload = json.loads(payload_json)
        
        # Check expiration
        expires_at = datetime.fromisoformat(payload["expires_at"])
        if datetime.now(timezone.utc) > expires_at:
            return None
        
        return payload
        
    except Exception:
        return None


def get_token_expiry(token: str) -> Optional[datetime]:
    """Get the expiry time of a token without full validation."""
    try:
        payload_b64 = token.split(".")[0]
        payload_json = base64.urlsafe_b64decode(payload_b64).decode()
        payload = json.loads(payload_json)
        return datetime.fromisoformat(payload["expires_at"])
    except Exception:
        return None
