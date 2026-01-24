"""Dataset and data management models."""

import uuid
from enum import Enum

from sqlalchemy import BigInteger, Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.models.base import TimestampMixin, UUIDMixin
from app.infrastructure.database.session import Base


class DataSourceType(str, Enum):
    """Data source type enumeration."""

    FILE = "file"
    API = "api"
    DATABASE = "database"
    GOOGLE_ADS = "google_ads"
    META_ADS = "meta_ads"
    SNOWFLAKE = "snowflake"
    BIGQUERY = "bigquery"
    REDSHIFT = "redshift"


class DataSource(Base, UUIDMixin, TimestampMixin):
    """Data source configuration model."""

    __tablename__ = "data_sources"

    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(50), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Connection configuration (encrypted in production)
    connection_config: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Organization
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True
    )

    # Relationships
    datasets: Mapped[list["Dataset"]] = relationship(back_populates="data_source")


class Dataset(Base, UUIDMixin, TimestampMixin):
    """Dataset model for storing data references."""

    __tablename__ = "datasets"

    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Schema information
    schema_definition: Mapped[dict] = mapped_column(JSONB, default=dict)
    column_types: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Statistics
    row_count: Mapped[int | None] = mapped_column(BigInteger)
    column_count: Mapped[int | None] = mapped_column(Integer)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger)

    # Time range (for time series data)
    start_date: Mapped[str | None] = mapped_column(String(50))
    end_date: Mapped[str | None] = mapped_column(String(50))
    time_granularity: Mapped[str | None] = mapped_column(String(20))  # daily, weekly, monthly

    # Tags and metadata
    tags: Mapped[list] = mapped_column(JSONB, default=list)
    metadata: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Storage
    storage_path: Mapped[str | None] = mapped_column(String(500))
    storage_format: Mapped[str] = mapped_column(String(20), default="parquet")

    # Relationships
    data_source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_sources.id")
    )
    data_source: Mapped["DataSource"] = relationship(back_populates="datasets")

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True
    )
    organization: Mapped["Organization"] = relationship(back_populates="datasets")

    versions: Mapped[list["DataVersion"]] = relationship(back_populates="dataset")
    channels: Mapped[list["Channel"]] = relationship(back_populates="dataset")
    metrics: Mapped[list["Metric"]] = relationship(back_populates="dataset")


class DataVersion(Base, UUIDMixin, TimestampMixin):
    """Dataset version for tracking changes."""

    __tablename__ = "data_versions"

    version: Mapped[str] = mapped_column(String(50), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)

    # DVC tracking
    dvc_hash: Mapped[str | None] = mapped_column(String(100))
    dvc_path: Mapped[str | None] = mapped_column(String(500))

    # Changes from previous version
    changes_summary: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Statistics at this version
    row_count: Mapped[int | None] = mapped_column(BigInteger)
    checksum: Mapped[str | None] = mapped_column(String(100))

    # Relationship
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.id"), index=True
    )
    dataset: Mapped["Dataset"] = relationship(back_populates="versions")


class Channel(Base, UUIDMixin, TimestampMixin):
    """Marketing channel definition."""

    __tablename__ = "channels"

    name: Mapped[str] = mapped_column(String(255), index=True)
    display_name: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    channel_type: Mapped[str] = mapped_column(String(50))  # paid, organic, owned

    # Column mapping in dataset
    spend_column: Mapped[str | None] = mapped_column(String(100))
    impression_column: Mapped[str | None] = mapped_column(String(100))
    click_column: Mapped[str | None] = mapped_column(String(100))

    # Default transformation parameters
    default_adstock_type: Mapped[str] = mapped_column(String(50), default="geometric")
    default_saturation_type: Mapped[str] = mapped_column(String(50), default="hill")

    # Relationship
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.id"), index=True
    )
    dataset: Mapped["Dataset"] = relationship(back_populates="channels")


class Metric(Base, UUIDMixin, TimestampMixin):
    """Business metric definition."""

    __tablename__ = "metrics"

    name: Mapped[str] = mapped_column(String(255), index=True)
    display_name: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    metric_type: Mapped[str] = mapped_column(String(50))  # revenue, conversions, leads

    # Column mapping
    column_name: Mapped[str] = mapped_column(String(100))

    # Aggregation settings
    aggregation_method: Mapped[str] = mapped_column(String(20), default="sum")
    is_target: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationship
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.id"), index=True
    )
    dataset: Mapped["Dataset"] = relationship(back_populates="metrics")


# Import for type hints
from app.infrastructure.database.models.organization import Organization  # noqa: E402
