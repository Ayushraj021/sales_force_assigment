"""Data management GraphQL types."""

from datetime import datetime
from typing import Optional
from uuid import UUID

import strawberry


@strawberry.type
class DataSourceType:
    """Data source configuration."""

    id: UUID
    name: str
    description: Optional[str]
    source_type: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


@strawberry.type
class ChannelType:
    """Marketing channel definition."""

    id: UUID
    name: str
    display_name: Optional[str]
    description: Optional[str]
    channel_type: str
    spend_column: Optional[str]
    impression_column: Optional[str]
    click_column: Optional[str]
    default_adstock_type: str
    default_saturation_type: str
    dataset_id: UUID
    created_at: datetime
    updated_at: datetime


@strawberry.type
class MetricType:
    """Business metric definition."""

    id: UUID
    name: str
    display_name: Optional[str]
    description: Optional[str]
    metric_type: str
    column_name: str
    aggregation_method: str
    is_target: bool
    dataset_id: UUID
    created_at: datetime
    updated_at: datetime


@strawberry.type
class DatasetType:
    """Dataset type."""

    id: UUID
    name: str
    description: Optional[str]
    is_active: bool
    row_count: Optional[int]
    column_count: Optional[int]
    file_size_bytes: Optional[int]
    start_date: Optional[str]
    end_date: Optional[str]
    time_granularity: Optional[str]
    storage_format: str
    column_names: list[str]
    channels: list[ChannelType]
    metrics: list[MetricType]
    created_at: datetime
    updated_at: datetime


@strawberry.input
class CreateDatasetInput:
    """Input for creating a dataset."""

    name: str
    description: Optional[str] = None
    file_id: str  # Reference to uploaded file
    time_column: str
    target_column: str
    time_granularity: Optional[str] = "daily"


@strawberry.input
class CreateChannelInput:
    """Input for defining a marketing channel."""

    dataset_id: UUID
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    channel_type: str  # paid, organic, owned
    spend_column: Optional[str] = None
    impression_column: Optional[str] = None
    click_column: Optional[str] = None
    default_adstock_type: str = "geometric"
    default_saturation_type: str = "hill"


@strawberry.input
class UpdateChannelInput:
    """Input for updating a channel."""

    name: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    channel_type: Optional[str] = None
    spend_column: Optional[str] = None
    impression_column: Optional[str] = None
    click_column: Optional[str] = None
    default_adstock_type: Optional[str] = None
    default_saturation_type: Optional[str] = None


@strawberry.input
class CreateMetricInput:
    """Input for defining a metric."""

    dataset_id: UUID
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    metric_type: str  # revenue, conversions, leads
    column_name: str
    aggregation_method: str = "sum"
    is_target: bool = False


@strawberry.input
class UpdateMetricInput:
    """Input for updating a metric."""

    name: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    metric_type: Optional[str] = None
    column_name: Optional[str] = None
    aggregation_method: Optional[str] = None
    is_target: Optional[bool] = None


@strawberry.input
class ChannelFilterInput:
    """Input for filtering channels."""

    dataset_id: Optional[UUID] = None
    channel_type: Optional[str] = None


@strawberry.input
class MetricFilterInput:
    """Input for filtering metrics."""

    dataset_id: Optional[UUID] = None
    metric_type: Optional[str] = None
    is_target: Optional[bool] = None


@strawberry.input
class CreateDataConnectorInput:
    """Input for creating a data connector."""

    name: str
    description: Optional[str] = None
    source_type: str  # google_ads, meta_ads, bigquery, snowflake, etc.
    connection_config: strawberry.scalars.JSON


@strawberry.input
class UpdateDataConnectorInput:
    """Input for updating a data connector."""

    name: Optional[str] = None
    description: Optional[str] = None
    connection_config: Optional[strawberry.scalars.JSON] = None
    is_active: Optional[bool] = None


@strawberry.type
class ConnectionTestResult:
    """Result of testing a data connector connection."""

    success: bool
    message: str
    details: Optional[strawberry.scalars.JSON] = None


@strawberry.type
class SyncResult:
    """Result of syncing data from a connector."""

    success: bool
    message: str
    records_synced: Optional[int] = None
    sync_started_at: Optional[datetime] = None
    sync_completed_at: Optional[datetime] = None
