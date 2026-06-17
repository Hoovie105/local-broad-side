"""
Auth/models.py

Auth owns User and PlatformConnection.
Backend owns PublishJob.
Same DB, different owners — each service manages its own tables.
"""
from sqlalchemy import Column, String, DateTime, Boolean, Enum as SAEnum, func
from services.auth_oauth.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class PlatformConnection(Base):
    """
    One row per user per platform.
    Stores the OAuth token Auth retrieved — Core reads this via Auth's
    internal HTTP endpoint, never by importing this model directly.
    """
    __tablename__ = "platform_connections"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)

    platform = Column(String, nullable=False)       # "instagram" | "tiktok" | "youtube"
    access_token = Column(String, nullable=False)   # encrypted at rest — see services/token.py
    platform_user_id = Column(String, nullable=False)  # ig_user_id, tiktok_user_id, etc.

    token_expires_at = Column(DateTime, nullable=True)   # null = no expiry (MVP)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class TokenBlacklist(Base):
    """
    Invalidated JWT tokens. Checked on every request.
    In production: move to Redis with TTL matching token expiry.
    """
    __tablename__ = "token_blacklist"

    token = Column(String, primary_key=True)
    blacklisted_at = Column(DateTime, server_default=func.now())

class PKCEVerifier(Base):
    """Temporary store for PKCE code verifiers. Deleted after use."""
    __tablename__ = "pkce_verifiers"

    state = Column(String, primary_key=True)  # user_id
    verifier = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())