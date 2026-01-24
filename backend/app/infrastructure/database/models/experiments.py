"""
Experiment-related database models.

Models for geo experiments, attribution models, and customer journeys.
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from .base import Base


class GeoExperimentStatus(str, PyEnum):
    """Status of a geo experiment."""

    DRAFT = "draft"
    DESIGNING = "designing"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    ANALYZED = "analyzed"
    ARCHIVED = "archived"


class GeoExperiment(Base):
    """
    Geo-Lift experiment model.

    Stores configuration and results for geographic incrementality tests.
    """

    __tablename__ = "geo_experiments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Status
    status = Column(
        Enum(GeoExperimentStatus),
        default=GeoExperimentStatus.DRAFT,
        nullable=False,
    )

    # Experiment design
    test_regions = Column(JSONB, nullable=False)  # List of test region IDs
    control_regions = Column(JSONB, nullable=False)  # List of control region IDs
    holdout_regions = Column(JSONB)  # Optional holdout regions

    # Timing
    start_date = Column(Date)
    end_date = Column(Date)
    warmup_days = Column(Integer, default=7)

    # Power analysis
    power_analysis = Column(JSONB)  # PowerAnalysisResult serialized
    minimum_detectable_effect = Column(Float)
    target_power = Column(Float, default=0.8)

    # Results
    results = Column(JSONB)  # GeoLiftResult serialized
    absolute_lift = Column(Float)
    relative_lift = Column(Float)
    p_value = Column(Float)
    confidence_interval_lower = Column(Float)
    confidence_interval_upper = Column(Float)

    # Metrics
    primary_metric = Column(String(100))
    secondary_metrics = Column(JSONB)  # List of metric names

    # Relationships
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)


class AttributionModelType(str, PyEnum):
    """Types of attribution models."""

    FIRST_TOUCH = "first_touch"
    LAST_TOUCH = "last_touch"
    LINEAR = "linear"
    TIME_DECAY = "time_decay"
    POSITION_BASED = "position_based"
    MARKOV = "markov"
    SHAPLEY = "shapley"
    DATA_DRIVEN = "data_driven"


class AttributionModel(Base):
    """
    Attribution model configuration.

    Stores settings for multi-touch attribution models.
    """

    __tablename__ = "attribution_models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Model type
    model_type = Column(
        Enum(AttributionModelType),
        nullable=False,
    )

    # Configuration
    lookback_window = Column(Integer, default=30)  # Days
    config = Column(JSONB)  # Model-specific configuration

    # For time decay
    time_decay_half_life = Column(Float)

    # For position-based
    first_touch_weight = Column(Float)
    last_touch_weight = Column(Float)

    # For Markov
    markov_order = Column(Integer, default=1)

    # Results storage
    channel_attribution = Column(JSONB)  # Latest attribution results
    last_run_at = Column(DateTime)

    # Relationships
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"))

    # Metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CustomerJourney(Base):
    """
    Customer journey data.

    Stores touchpoint sequences for attribution analysis.
    """

    __tablename__ = "customer_journeys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Customer identification
    customer_id = Column(String(255), nullable=False, index=True)
    anonymous_id = Column(String(255), index=True)

    # Journey data
    touchpoints = Column(JSONB, nullable=False)  # List of touchpoint dicts

    # Conversion info
    converted = Column(Boolean, default=False, index=True)
    conversion_value = Column(Float)
    converted_at = Column(DateTime)
    conversion_type = Column(String(100))  # e.g., "purchase", "signup"

    # Journey metadata
    first_touch_at = Column(DateTime)
    last_touch_at = Column(DateTime)
    journey_duration_seconds = Column(Integer)
    n_touchpoints = Column(Integer)

    # Channel summary
    channels_touched = Column(JSONB)  # List of unique channels
    first_channel = Column(String(100))
    last_channel = Column(String(100))

    # Relationships
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"))

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)


class DashboardLayout(Base):
    """
    Custom dashboard layout configuration.

    Stores drag-drop dashboard widget layouts.
    """

    __tablename__ = "dashboard_layouts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Layout data (react-grid-layout format)
    layout = Column(JSONB, nullable=False)  # List of layout items

    # Widget configurations
    widgets = Column(JSONB, nullable=False)  # List of widget configs

    # Settings
    is_default = Column(Boolean, default=False)
    is_shared = Column(Boolean, default=False)

    # Relationships
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"))

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ConsentRecord(Base):
    """
    Consent management for GDPR/CCPA compliance.

    Tracks customer consent for data processing.
    """

    __tablename__ = "consent_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Customer identification
    customer_id = Column(String(255), nullable=False, index=True)

    # Consent details
    consent_type = Column(String(100), nullable=False)  # e.g., "analytics", "marketing"
    granted = Column(Boolean, nullable=False)

    # Timing
    granted_at = Column(DateTime)
    revoked_at = Column(DateTime)
    expires_at = Column(DateTime)

    # Source
    consent_source = Column(String(100))  # e.g., "website", "app", "email"
    ip_address = Column(String(45))  # IPv4 or IPv6
    user_agent = Column(Text)

    # Additional data
    metadata = Column(JSONB)

    # Relationships
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"))

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CausalGraph(Base):
    """
    Learned causal graph structure.

    Stores DAG structures from causal discovery algorithms.
    """

    __tablename__ = "causal_graphs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Algorithm used
    algorithm = Column(String(50), nullable=False)  # e.g., "pc", "notears"
    algorithm_params = Column(JSONB)

    # Graph structure
    nodes = Column(JSONB, nullable=False)  # List of node names
    edges = Column(JSONB, nullable=False)  # List of edge dicts
    adjacency_matrix = Column(JSONB)  # Serialized numpy array

    # Metadata
    n_nodes = Column(Integer)
    n_edges = Column(Integer)
    is_dag = Column(Boolean)

    # Data source
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id"))

    # Relationships
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"))

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
