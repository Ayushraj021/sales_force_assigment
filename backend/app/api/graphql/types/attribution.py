"""Attribution Model GraphQL types."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

import strawberry
from strawberry.scalars import JSON


@strawberry.enum
class AttributionModelTypeEnum(Enum):
    """Types of attribution models."""

    FIRST_TOUCH = "first_touch"
    LAST_TOUCH = "last_touch"
    LINEAR = "linear"
    TIME_DECAY = "time_decay"
    POSITION_BASED = "position_based"
    MARKOV = "markov"
    SHAPLEY = "shapley"
    DATA_DRIVEN = "data_driven"


@strawberry.type
class AttributionModelType:
    """Attribution model type."""

    id: UUID
    name: str
    description: Optional[str]
    model_type: AttributionModelTypeEnum

    # Configuration
    lookback_window: int
    config: Optional[JSON]

    # Time decay settings
    time_decay_half_life: Optional[float]

    # Position-based settings
    first_touch_weight: Optional[float]
    last_touch_weight: Optional[float]

    # Markov settings
    markov_order: Optional[int]

    # Results
    channel_attribution: Optional[JSON]
    last_run_at: Optional[datetime]

    # Metadata
    organization_id: Optional[UUID]
    is_active: bool
    created_at: datetime
    updated_at: datetime


@strawberry.type
class CustomerJourneyType:
    """Customer journey type."""

    id: UUID
    customer_id: str
    anonymous_id: Optional[str]

    # Journey data
    touchpoints: JSON
    n_touchpoints: Optional[int]

    # Conversion
    converted: bool
    conversion_value: Optional[float]
    converted_at: Optional[datetime]
    conversion_type: Optional[str]

    # Journey metadata
    first_touch_at: Optional[datetime]
    last_touch_at: Optional[datetime]
    journey_duration_seconds: Optional[int]

    # Channel summary
    channels_touched: Optional[JSON]
    first_channel: Optional[str]
    last_channel: Optional[str]

    # Timestamps
    created_at: datetime


@strawberry.input
class CreateAttributionModelInput:
    """Input for creating an attribution model."""

    name: str
    description: Optional[str] = None
    model_type: str  # first_touch, last_touch, linear, time_decay, position_based, markov, shapley, data_driven
    lookback_window: int = 30
    config: Optional[JSON] = None

    # Time decay settings
    time_decay_half_life: Optional[float] = None

    # Position-based settings
    first_touch_weight: Optional[float] = None
    last_touch_weight: Optional[float] = None

    # Markov settings
    markov_order: int = 1


@strawberry.input
class UpdateAttributionModelInput:
    """Input for updating an attribution model."""

    name: Optional[str] = None
    description: Optional[str] = None
    lookback_window: Optional[int] = None
    config: Optional[JSON] = None
    time_decay_half_life: Optional[float] = None
    first_touch_weight: Optional[float] = None
    last_touch_weight: Optional[float] = None
    markov_order: Optional[int] = None
    is_active: Optional[bool] = None


@strawberry.input
class AttributionModelFilterInput:
    """Input for filtering attribution models."""

    model_type: Optional[str] = None
    is_active: Optional[bool] = None


@strawberry.type
class AttributionResultType:
    """Attribution analysis result type."""

    model_id: UUID
    model_name: str
    model_type: str
    channel_attribution: JSON
    total_conversions: int
    total_revenue: float
    attribution_date: datetime
    journey_stats: JSON


@strawberry.type
class ChannelAttributionType:
    """Attribution breakdown by channel."""

    channel: str
    attributed_conversions: float
    attributed_revenue: float
    contribution_percentage: float
    first_touch_conversions: int
    last_touch_conversions: int
    average_position_in_journey: float


@strawberry.input
class RunAttributionInput:
    """Input for running attribution analysis."""

    model_id: UUID
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    conversion_type: Optional[str] = None
