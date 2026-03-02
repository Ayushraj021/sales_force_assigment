"""Forecast models."""

import uuid
from enum import Enum

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.models.base import TimestampMixin, UUIDMixin
from app.infrastructure.database.session import Base


class ForecastStatus(str, Enum):
    """Forecast status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Forecast(Base, UUIDMixin, TimestampMixin):
    """Forecast model for storing forecast results."""

    __tablename__ = "forecasts"

    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)

    # Model configuration
    model_type: Mapped[str] = mapped_column(String(50))  # prophet, arima, ensemble, neural
    target_metric: Mapped[str] = mapped_column(String(100))  # sales, revenue, conversions
    horizon: Mapped[int] = mapped_column(Integer, default=30)  # Days to forecast
    confidence_level: Mapped[float] = mapped_column(Float, default=0.95)

    # Date range
    start_date: Mapped[str | None] = mapped_column(String(50))
    end_date: Mapped[str | None] = mapped_column(String(50))
    forecast_start_date: Mapped[str | None] = mapped_column(String(50))
    forecast_end_date: Mapped[str | None] = mapped_column(String(50))

    # Results stored as JSONB
    predicted_values: Mapped[list] = mapped_column(JSONB, default=list)
    lower_bounds: Mapped[list] = mapped_column(JSONB, default=list)
    upper_bounds: Mapped[list] = mapped_column(JSONB, default=list)
    forecast_dates: Mapped[list] = mapped_column(JSONB, default=list)

    # Model parameters and metrics
    model_params: Mapped[dict] = mapped_column(JSONB, default=dict)
    metrics: Mapped[dict] = mapped_column(JSONB, default=dict)  # mape, rmse, mae

    # Error handling
    error_message: Mapped[str | None] = mapped_column(Text)

    # Flags
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.id")
    )
    model_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("models.id")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
