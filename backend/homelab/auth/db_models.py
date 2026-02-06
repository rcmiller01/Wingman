"""Database models for authentication (users, sessions, service accounts)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from homelab.storage.models import Base, String, DateTime


class UserDB(Base):
    """User account linked to OIDC identity (database model)."""
    
    __tablename__ = "users"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    
    # OIDC identity
    oidc_sub: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    
    # User profile
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Authorization
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="viewer")
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    # Status
    disabled: Mapped[bool] = mapped_column(default=False)
    
    __table_args__ = (
        Index("ix_users_email", "email"),
    )


class SessionDB(Base):
    """User session with token tracking (database model)."""
    
    __tablename__ = "sessions"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    
    # Token hashes (never store raw tokens)
    access_token_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    refresh_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    # Session lifecycle
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    __table_args__ = (
        Index("ix_sessions_user_id", "user_id"),
        Index("ix_sessions_access_token_hash", "access_token_hash"),
    )


class ServiceAccountDB(Base):
    """Service account for API key authentication (database model)."""
    
    __tablename__ = "service_accounts"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    
    # Identity
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    
    # API key (hashed)
    api_key_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    api_key_prefix: Mapped[str] = mapped_column(String(8), nullable=False)  # For identification (e.g., "hc_abc123")
    
    # Authorization
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="operator")
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    last_used: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    # Status
    disabled: Mapped[bool] = mapped_column(default=False)
    
    __table_args__ = (
        Index("ix_service_accounts_api_key_hash", "api_key_hash"),
    )
