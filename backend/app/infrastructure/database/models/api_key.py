"""API Key model for programmatic access."""

import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.models.base import TimestampMixin, UUIDMixin
from app.infrastructure.database.session import Base


def generate_api_key() -> str:
    """Generate a secure API key."""
    return f"sf_{secrets.token_urlsafe(32)}"


class APIKey(Base, UUIDMixin, TimestampMixin):
    """API Key model for programmatic access."""

    __tablename__ = "api_keys"

    name: Mapped[str] = mapped_column(String(255))
    key_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    key_prefix: Mapped[str] = mapped_column(String(10))  # First chars for identification
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Expiration
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Scopes/permissions
    scopes: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)

    # Rate limiting
    rate_limit_requests: Mapped[int] = mapped_column(default=1000)
    rate_limit_period: Mapped[int] = mapped_column(default=3600)  # seconds

    # User relationship
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    user: Mapped["User"] = relationship(back_populates="api_keys")

    @property
    def is_expired(self) -> bool:
        """Check if API key has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if API key is valid (active and not expired)."""
        return self.is_active and not self.is_expired

    def has_scope(self, scope: str) -> bool:
        """Check if API key has a specific scope."""
        if "*" in self.scopes:
            return True
        return scope in self.scopes


# Import for type hints
from app.infrastructure.database.models.user import User  # noqa: E402
