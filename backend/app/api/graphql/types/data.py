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

    name: str
    display_name: Optional[str] = None
    channel_type: str  # paid, organic, owned
    spend_column: Optional[str] = None
    impression_column: Optional[str] = None
    click_column: Optional[str] = None


@strawberry.input
class CreateMetricInput:
    """Input for defining a metric."""

    name: str
    display_name: Optional[str] = None
    metric_type: str  # revenue, conversions, leads
    column_name: str
    aggregation_method: str = "sum"
    is_target: bool = False
