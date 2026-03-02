"""API Key GraphQL types."""

from datetime import datetime
from typing import Optional
from uuid import UUID

import strawberry


@strawberry.type
class APIKeyType:
    """API Key type."""

    id: UUID
    name: str
    key_prefix: str
    description: Optional[str]
    is_active: bool
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    scopes: list[str]
    rate_limit_requests: int
    rate_limit_period: int
    created_at: datetime
    updated_at: datetime


@strawberry.type
class APIKeyCreatedType:
    """API Key type returned after creation (includes full key)."""

    id: UUID
    name: str
    key: str  # Full API key (only shown once)
    key_prefix: str
    description: Optional[str]
    expires_at: Optional[datetime]
    scopes: list[str]
    created_at: datetime


@strawberry.input
class CreateAPIKeyInput:
    """Input for creating an API key."""

    name: str
    description: Optional[str] = None
    expires_in_days: Optional[int] = None  # None = never expires
    scopes: Optional[list[str]] = None  # None = all scopes
    rate_limit_requests: int = 1000
    rate_limit_period: int = 3600  # seconds


@strawberry.input
class UpdateAPIKeyInput:
    """Input for updating an API key."""

    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    scopes: Optional[list[str]] = None
    rate_limit_requests: Optional[int] = None
    rate_limit_period: Optional[int] = None
