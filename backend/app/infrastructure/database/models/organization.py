"""Organization model for multi-tenancy."""

import uuid
from enum import Enum

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.models.base import TimestampMixin, UUIDMixin
from app.infrastructure.database.session import Base


class SubscriptionTier(str, Enum):
    """Organization subscription tiers."""

    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class Organization(Base, UUIDMixin, TimestampMixin):
    """Organization model for multi-tenant support."""

    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), index=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Subscription & limits
    subscription_tier: Mapped[str] = mapped_column(
        String(50), default=SubscriptionTier.FREE.value
    )
    max_users: Mapped[int] = mapped_column(default=5)
    max_models: Mapped[int] = mapped_column(default=10)
    max_datasets: Mapped[int] = mapped_column(default=20)

    # Settings
    settings: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Owner
    owner_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    # Relationships
    users: Mapped[list["User"]] = relationship(back_populates="organization")
    datasets: Mapped[list["Dataset"]] = relationship(back_populates="organization")
    models: Mapped[list["Model"]] = relationship(back_populates="organization")
    experiments: Mapped[list["Experiment"]] = relationship(back_populates="organization")

    @property
    def user_count(self) -> int:
        """Get the number of users in the organization."""
        return len(self.users)

    def can_add_user(self) -> bool:
        """Check if organization can add more users."""
        return self.user_count < self.max_users


# Import for type hints
from app.infrastructure.database.models.user import User  # noqa: E402
from app.infrastructure.database.models.dataset import Dataset  # noqa: E402
from app.infrastructure.database.models.model import Model, Experiment  # noqa: E402
