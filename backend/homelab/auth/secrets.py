"""Secrets management for authentication.

Provides secure key storage with:
- Environment variable / Docker secrets loading
- Key hashing at rest (only stores hashes, never raw keys)
- Key rotation support (create new → deprecate old)
- Rate limiting for auth failures
"""

import os
import hashlib
import hmac
import secrets
import logging
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path
from collections import defaultdict

logger = logging.getLogger(__name__)


# --- Key Hashing ---

def hash_key_secure(key: str, salt: Optional[bytes] = None) -> tuple[str, bytes]:
    """
    Hash an API key using PBKDF2 for secure storage.
    
    Returns (hashed_key, salt) - both needed to verify later.
    """
    if salt is None:
        salt = secrets.token_bytes(32)
    
    # PBKDF2 with SHA256, 100k iterations (OWASP recommended minimum)
    hashed = hashlib.pbkdf2_hmac(
        'sha256',
        key.encode('utf-8'),
        salt,
        iterations=100_000,
    )
    
    return hashed.hex(), salt


def verify_key_secure(key: str, stored_hash: str, salt: bytes) -> bool:
    """
    Verify a key against its stored hash using constant-time comparison.
    """
    computed_hash, _ = hash_key_secure(key, salt)
    return hmac.compare_digest(computed_hash, stored_hash)


# --- Secrets Loading ---

@dataclass
class SecretsConfig:
    """Configuration for secrets storage."""
    
    # Auth secret key (for signing tokens)
    auth_secret: str = ""
    
    # Path to Docker secrets (if using Docker Swarm/secrets)
    docker_secrets_path: str = "/run/secrets"
    
    # Environment variable prefix for secrets
    env_prefix: str = "WINGMAN_"
    
    @classmethod
    def load(cls) -> "SecretsConfig":
        """Load secrets from environment and Docker secrets."""
        config = cls()
        
        # 1. Try Docker secrets first (most secure)
        secrets_path = Path(config.docker_secrets_path)
        if secrets_path.exists():
            auth_secret_file = secrets_path / "wingman_auth_secret"
            if auth_secret_file.exists():
                config.auth_secret = auth_secret_file.read_text().strip()
                logger.info("[Secrets] Loaded auth_secret from Docker secrets")
        
        # 2. Fall back to environment variables
        if not config.auth_secret:
            config.auth_secret = os.environ.get(
                f"{config.env_prefix}AUTH_SECRET",
                os.environ.get("AUTH_SECRET_KEY", "")
            )
            if config.auth_secret:
                logger.info("[Secrets] Loaded auth_secret from environment")
        
        # 3. Generate ephemeral secret for dev (warn loudly)
        if not config.auth_secret:
            config.auth_secret = secrets.token_hex(32)
            logger.warning(
                "[Secrets] ⚠️  Generated ephemeral auth_secret. "
                "Set WINGMAN_AUTH_SECRET for production!"
            )
        
        return config


# --- Rate Limiting ---

@dataclass 
class RateLimitEntry:
    """Tracks auth failures for rate limiting."""
    failures: int = 0
    first_failure: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_failure: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    locked_until: Optional[datetime] = None


class AuthRateLimiter:
    """
    Rate limiter for authentication failures.
    
    Strategy:
    - After 5 failures in 15 minutes: 1 minute lockout
    - After 10 failures in 15 minutes: 5 minute lockout  
    - After 20 failures in 15 minutes: 30 minute lockout
    """
    
    def __init__(
        self,
        window_minutes: int = 15,
        soft_limit: int = 5,
        medium_limit: int = 10,
        hard_limit: int = 20,
    ):
        self.window = timedelta(minutes=window_minutes)
        self.soft_limit = soft_limit
        self.medium_limit = medium_limit
        self.hard_limit = hard_limit
        
        # Track by source (IP or key prefix)
        self._entries: dict[str, RateLimitEntry] = defaultdict(RateLimitEntry)
    
    def record_failure(self, source: str) -> Optional[timedelta]:
        """
        Record an auth failure and return lockout duration if triggered.
        
        Args:
            source: Identifier (IP address, key prefix, etc.)
            
        Returns:
            Lockout duration if rate limit exceeded, None otherwise.
        """
        now = datetime.now(timezone.utc)
        entry = self._entries[source]
        
        # Reset if outside window
        if now - entry.first_failure > self.window:
            entry.failures = 0
            entry.first_failure = now
        
        entry.failures += 1
        entry.last_failure = now
        
        # Determine lockout
        lockout: Optional[timedelta] = None
        
        if entry.failures >= self.hard_limit:
            lockout = timedelta(minutes=30)
            logger.warning(f"[RateLimit] Hard lockout for {source}: {entry.failures} failures")
        elif entry.failures >= self.medium_limit:
            lockout = timedelta(minutes=5)
            logger.warning(f"[RateLimit] Medium lockout for {source}: {entry.failures} failures")
        elif entry.failures >= self.soft_limit:
            lockout = timedelta(minutes=1)
            logger.info(f"[RateLimit] Soft lockout for {source}: {entry.failures} failures")
        
        if lockout:
            entry.locked_until = now + lockout
        
        return lockout
    
    def record_success(self, source: str) -> None:
        """Record successful auth - resets failure count."""
        if source in self._entries:
            del self._entries[source]
    
    def is_locked(self, source: str) -> tuple[bool, Optional[datetime]]:
        """
        Check if a source is currently locked out.
        
        Returns (is_locked, locked_until).
        """
        entry = self._entries.get(source)
        if not entry or not entry.locked_until:
            return False, None
        
        now = datetime.now(timezone.utc)
        if now >= entry.locked_until:
            # Lockout expired
            entry.locked_until = None
            return False, None
        
        return True, entry.locked_until
    
    def get_stats(self) -> dict[str, int]:
        """Get rate limit statistics."""
        now = datetime.now(timezone.utc)
        active = sum(1 for e in self._entries.values() if now - e.first_failure <= self.window)
        locked = sum(1 for e in self._entries.values() if e.locked_until and now < e.locked_until)
        
        return {
            "tracked_sources": len(self._entries),
            "active_in_window": active,
            "currently_locked": locked,
        }
    
    def cleanup_stale(self, max_age_hours: int = 24) -> int:
        """Remove stale entries older than max_age_hours."""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=max_age_hours)
        
        stale = [k for k, v in self._entries.items() if v.last_failure < cutoff]
        for key in stale:
            del self._entries[key]
        
        return len(stale)


# --- Key Rotation ---

@dataclass
class KeyRotationRecord:
    """Record of a key rotation event."""
    old_key_hash: str
    new_key_hash: str
    rotated_at: datetime
    rotated_by: str  # User ID who performed rotation
    reason: str = ""


class KeyRotationManager:
    """
    Manages API key rotation.
    
    Supports:
    - Creating new keys while keeping old valid (grace period)
    - Revoking old keys after grace period
    - Audit trail of rotations
    """
    
    def __init__(self, grace_period_hours: int = 24):
        self.grace_period = timedelta(hours=grace_period_hours)
        self._pending_rotations: dict[str, KeyRotationRecord] = {}  # user_id -> record
        self._rotation_history: list[KeyRotationRecord] = []
    
    def initiate_rotation(
        self,
        user_id: str,
        old_key_hash: str,
        new_key_hash: str,
        rotated_by: str,
        reason: str = "",
    ) -> KeyRotationRecord:
        """
        Initiate a key rotation with grace period.
        
        During grace period, both old and new keys are valid.
        """
        record = KeyRotationRecord(
            old_key_hash=old_key_hash,
            new_key_hash=new_key_hash,
            rotated_at=datetime.now(timezone.utc),
            rotated_by=rotated_by,
            reason=reason,
        )
        
        self._pending_rotations[user_id] = record
        logger.info(f"[KeyRotation] Initiated rotation for user {user_id} by {rotated_by}")
        
        return record
    
    def complete_rotation(self, user_id: str) -> Optional[KeyRotationRecord]:
        """
        Complete a pending rotation (revoke old key).
        
        Called automatically after grace period, or manually.
        """
        record = self._pending_rotations.pop(user_id, None)
        if record:
            self._rotation_history.append(record)
            logger.info(f"[KeyRotation] Completed rotation for user {user_id}")
        return record
    
    def cancel_rotation(self, user_id: str) -> bool:
        """Cancel a pending rotation (keep using old key)."""
        if user_id in self._pending_rotations:
            del self._pending_rotations[user_id]
            logger.info(f"[KeyRotation] Cancelled rotation for user {user_id}")
            return True
        return False
    
    def is_key_valid_during_rotation(
        self,
        user_id: str,
        key_hash: str,
    ) -> tuple[bool, str]:
        """
        Check if a key is valid during rotation grace period.
        
        Returns (is_valid, status) where status is:
        - "current": Key is the current key
        - "rotating_old": Key is old key during grace period
        - "rotating_new": Key is new key during grace period
        - "invalid": Key doesn't match
        """
        record = self._pending_rotations.get(user_id)
        
        if not record:
            # No rotation in progress
            return True, "current"
        
        now = datetime.now(timezone.utc)
        grace_expired = now > record.rotated_at + self.grace_period
        
        if grace_expired:
            # Grace period expired - only new key valid
            if hmac.compare_digest(key_hash, record.new_key_hash):
                return True, "current"
            return False, "invalid"
        
        # During grace period - both keys valid
        if hmac.compare_digest(key_hash, record.new_key_hash):
            return True, "rotating_new"
        if hmac.compare_digest(key_hash, record.old_key_hash):
            return True, "rotating_old"
        
        return False, "invalid"
    
    def get_pending_rotations(self) -> list[tuple[str, KeyRotationRecord]]:
        """Get all pending rotations."""
        return list(self._pending_rotations.items())
    
    def get_rotation_history(self, limit: int = 100) -> list[KeyRotationRecord]:
        """Get recent rotation history."""
        return self._rotation_history[-limit:]
    
    def cleanup_expired(self) -> int:
        """Complete all rotations past their grace period."""
        now = datetime.now(timezone.utc)
        expired = [
            uid for uid, rec in self._pending_rotations.items()
            if now > rec.rotated_at + self.grace_period
        ]
        
        for user_id in expired:
            self.complete_rotation(user_id)
        
        return len(expired)


# --- Global Instances ---

_secrets_config: Optional[SecretsConfig] = None
_rate_limiter: Optional[AuthRateLimiter] = None
_key_rotation_manager: Optional[KeyRotationManager] = None


def get_secrets_config() -> SecretsConfig:
    """Get or create secrets configuration."""
    global _secrets_config
    if _secrets_config is None:
        _secrets_config = SecretsConfig.load()
    return _secrets_config


def get_rate_limiter() -> AuthRateLimiter:
    """Get or create rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = AuthRateLimiter()
    return _rate_limiter


def get_key_rotation_manager() -> KeyRotationManager:
    """Get or create key rotation manager."""
    global _key_rotation_manager
    if _key_rotation_manager is None:
        _key_rotation_manager = KeyRotationManager()
    return _key_rotation_manager


# --- Helper to get auth secret ---

def get_auth_secret() -> str:
    """Get the auth secret key for token signing."""
    return get_secrets_config().auth_secret
