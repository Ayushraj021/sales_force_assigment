"""Geo Experiment GraphQL types."""

from datetime import date, datetime
from typing import Optional
from uuid import UUID

import strawberry
from strawberry.scalars import JSON


from enum import Enum

@strawberry.enum
class GeoExperimentStatusEnum(Enum):
    """Status of a geo experiment."""

    DRAFT = "draft"
    DESIGNING = "designing"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    ANALYZED = "analyzed"
    ARCHIVED = "archived"


@strawberry.type
class GeoExperimentType:
    """Geo-Lift experiment type."""

    id: UUID
    name: str
    description: Optional[str]
    status: GeoExperimentStatusEnum

    # Regions
    test_regions: JSON
    control_regions: JSON
    holdout_regions: Optional[JSON]

    # Timing
    start_date: Optional[date]
    end_date: Optional[date]
    warmup_days: Optional[int]

    # Power analysis
    power_analysis: Optional[JSON]
    minimum_detectable_effect: Optional[float]
    target_power: Optional[float]

    # Results
    results: Optional[JSON]
    absolute_lift: Optional[float]
    relative_lift: Optional[float]
    p_value: Optional[float]
    confidence_interval_lower: Optional[float]
    confidence_interval_upper: Optional[float]

    # Metrics
    primary_metric: Optional[str]
    secondary_metrics: Optional[JSON]

    # Relationships
    organization_id: Optional[UUID]
    created_by_id: Optional[UUID]

    # Timestamps
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]


@strawberry.input
class CreateGeoExperimentInput:
    """Input for creating a geo experiment."""

    name: str
    description: Optional[str] = None
    test_regions: JSON
    control_regions: JSON
    holdout_regions: Optional[JSON] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    warmup_days: int = 7
    minimum_detectable_effect: Optional[float] = None
    target_power: float = 0.8
    primary_metric: Optional[str] = None
    secondary_metrics: Optional[JSON] = None


@strawberry.input
class UpdateGeoExperimentInput:
    """Input for updating a geo experiment."""

    name: Optional[str] = None
    description: Optional[str] = None
    test_regions: Optional[JSON] = None
    control_regions: Optional[JSON] = None
    holdout_regions: Optional[JSON] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    warmup_days: Optional[int] = None
    minimum_detectable_effect: Optional[float] = None
    target_power: Optional[float] = None
    primary_metric: Optional[str] = None
    secondary_metrics: Optional[JSON] = None


@strawberry.input
class GeoExperimentFilterInput:
    """Input for filtering geo experiments."""

    status: Optional[str] = None
    start_date_from: Optional[str] = None
    start_date_to: Optional[str] = None
    primary_metric: Optional[str] = None


@strawberry.type
class PowerAnalysisResult:
    """Power analysis result type."""

    required_sample_size: int
    estimated_power: float
    minimum_detectable_effect: float
    confidence_level: float
    test_regions_count: int
    control_regions_count: int
    recommendations: list[str]


@strawberry.input
class RunPowerAnalysisInput:
    """Input for running power analysis."""

    experiment_id: UUID
    expected_effect_size: Optional[float] = None
    significance_level: float = 0.05


@strawberry.type
class GeoExperimentResultType:
    """Detailed geo experiment result type."""

    experiment_id: UUID
    absolute_lift: float
    relative_lift: float
    p_value: float
    confidence_interval_lower: float
    confidence_interval_upper: float
    is_significant: bool
    test_metric_value: float
    control_metric_value: float
    region_level_results: JSON
    time_series_comparison: JSON
    diagnostics: Optional[JSON]
