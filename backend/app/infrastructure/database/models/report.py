"""Reporting and dashboard models."""

import uuid
from enum import Enum

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.models.base import TimestampMixin, UUIDMixin
from app.infrastructure.database.session import Base


class WidgetType(str, Enum):
    """Dashboard widget types."""

    LINE_CHART = "line_chart"
    BAR_CHART = "bar_chart"
    PIE_CHART = "pie_chart"
    AREA_CHART = "area_chart"
    SCATTER_PLOT = "scatter_plot"
    HEATMAP = "heatmap"
    KPI_CARD = "kpi_card"
    TABLE = "table"
    WATERFALL = "waterfall"
    RESPONSE_CURVE = "response_curve"
    FORECAST = "forecast"


class Dashboard(Base, UUIDMixin, TimestampMixin):
    """Dashboard model."""

    __tablename__ = "dashboards"

    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)

    # Layout configuration
    layout: Mapped[dict] = mapped_column(JSONB, default=dict)
    theme: Mapped[str] = mapped_column(String(50), default="light")

    # Filters
    default_filters: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Relationships
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )

    widgets: Mapped[list["Widget"]] = relationship(back_populates="dashboard")


class Widget(Base, UUIDMixin, TimestampMixin):
    """Dashboard widget model."""

    __tablename__ = "widgets"

    title: Mapped[str] = mapped_column(String(255))
    widget_type: Mapped[str] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text)

    # Position and size
    position_x: Mapped[int] = mapped_column(Integer, default=0)
    position_y: Mapped[int] = mapped_column(Integer, default=0)
    width: Mapped[int] = mapped_column(Integer, default=4)
    height: Mapped[int] = mapped_column(Integer, default=3)

    # Data configuration
    data_source: Mapped[str | None] = mapped_column(String(100))  # model, dataset, optimization
    data_config: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Visualization configuration
    chart_config: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Refresh settings
    auto_refresh: Mapped[bool] = mapped_column(Boolean, default=False)
    refresh_interval_seconds: Mapped[int] = mapped_column(Integer, default=300)

    # Relationship
    dashboard_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dashboards.id"), index=True
    )
    dashboard: Mapped["Dashboard"] = relationship(back_populates="widgets")


class Report(Base, UUIDMixin, TimestampMixin):
    """Report template model."""

    __tablename__ = "reports"

    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    report_type: Mapped[str] = mapped_column(String(50))  # mmm, forecast, optimization

    # Template configuration
    template: Mapped[dict] = mapped_column(JSONB, default=dict)
    sections: Mapped[list] = mapped_column(JSONB, default=list)

    # Export formats
    available_formats: Mapped[list] = mapped_column(
        JSONB, default=["pdf", "excel", "pptx"]
    )

    # Relationships
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )

    scheduled_reports: Mapped[list["ScheduledReport"]] = relationship(
        back_populates="report"
    )


class ScheduledReport(Base, UUIDMixin, TimestampMixin):
    """Scheduled report configuration."""

    __tablename__ = "scheduled_reports"

    name: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Schedule configuration
    schedule_type: Mapped[str] = mapped_column(String(20))  # daily, weekly, monthly
    schedule_config: Mapped[dict] = mapped_column(JSONB, default=dict)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")

    # Delivery
    delivery_method: Mapped[str] = mapped_column(String(20))  # email, slack, s3
    delivery_config: Mapped[dict] = mapped_column(JSONB, default=dict)
    recipients: Mapped[list] = mapped_column(JSONB, default=list)

    # Export settings
    export_format: Mapped[str] = mapped_column(String(20), default="pdf")

    # Last run info
    last_run_at: Mapped[str | None] = mapped_column(String(50))
    last_run_status: Mapped[str | None] = mapped_column(String(20))
    next_run_at: Mapped[str | None] = mapped_column(String(50))

    # Relationship
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reports.id"), index=True
    )
    report: Mapped["Report"] = relationship(back_populates="scheduled_reports")

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True
    )


class Export(Base, UUIDMixin, TimestampMixin):
    """Export job model."""

    __tablename__ = "exports"

    export_type: Mapped[str] = mapped_column(String(50))  # report, data, model
    export_format: Mapped[str] = mapped_column(String(20))  # pdf, excel, csv, pptx
    status: Mapped[str] = mapped_column(String(20), default="pending")

    # Configuration
    config: Mapped[dict] = mapped_column(JSONB, default=dict)

    # File info
    file_path: Mapped[str | None] = mapped_column(String(500))
    file_size_bytes: Mapped[int | None] = mapped_column()
    download_url: Mapped[str | None] = mapped_column(String(500))
    expires_at: Mapped[str | None] = mapped_column(String(50))

    # Error handling
    error_message: Mapped[str | None] = mapped_column(Text)

    # Relationships
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
