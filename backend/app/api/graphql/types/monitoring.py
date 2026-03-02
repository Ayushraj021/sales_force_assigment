"""Monitoring GraphQL types."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

import strawberry
from strawberry.scalars import JSON


@strawberry.enum
class AlertSeverityEnum(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@strawberry.enum
class AlertTypeEnum(Enum):
    """Types of monitoring alerts."""
    DRIFT = "drift"
    PERFORMANCE = "performance"
    LATENCY = "latency"
    ERROR_RATE = "error_rate"
    THRESHOLD = "threshold"


@strawberry.type
class MonitorAlertType:
    """Monitoring alert."""
    alert_id: str
    alert_type: str
    severity: str
    model_name: str
    message: str
    metric_name: Optional[str]
    current_value: Optional[float]
    threshold_value: Optional[float]
    timestamp: datetime
    is_acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None


@strawberry.type
class MonitorConfigType:
    """Monitoring configuration."""
    id: UUID
    model_id: UUID
    drift_threshold: float
    performance_threshold: float
    latency_threshold_ms: float
    error_rate_threshold: float
    check_interval_minutes: int
    enabled: bool
    created_at: datetime
    updated_at: datetime


@strawberry.type
class MonitorMetricType:
    """Logged monitoring metric."""
    id: str
    model_name: str
    timestamp: datetime
    prediction: float
    actual: Optional[float]
    latency_ms: float
    error: Optional[float]
    abs_error: Optional[float]
    pct_error: Optional[float]


@strawberry.type
class MonitorSummaryType:
    """Monitoring summary for a model."""
    model_name: str
    total_predictions: int
    recent_predictions: int
    avg_latency_ms: float
    alert_count: int
    critical_alerts: int
    current_mae: Optional[float]
    current_mape: Optional[float]
    status: str


@strawberry.type
class BaselineType:
    """Model baseline for monitoring."""
    id: UUID
    model_id: UUID
    model_name: str
    metrics: JSON
    feature_distributions: Optional[JSON]
    created_at: datetime


@strawberry.type
class DriftCheckResultType:
    """Result of drift check."""
    model_name: str
    checked_at: datetime
    drift_detected: bool
    drifted_features: list[str]
    alerts: list[MonitorAlertType]


@strawberry.type
class PerformanceCheckResultType:
    """Result of performance check."""
    model_name: str
    checked_at: datetime
    degradation_detected: bool
    current_mape: Optional[float]
    baseline_mape: Optional[float]
    degradation_pct: Optional[float]
    alerts: list[MonitorAlertType]


@strawberry.input
class CreateMonitorConfigInput:
    """Input for creating monitor configuration."""
    model_id: UUID
    drift_threshold: float = 0.1
    performance_threshold: float = 0.8
    latency_threshold_ms: float = 1000
    error_rate_threshold: float = 0.05
    check_interval_minutes: int = 60
    enabled: bool = True


@strawberry.input
class UpdateMonitorConfigInput:
    """Input for updating monitor configuration."""
    drift_threshold: Optional[float] = None
    performance_threshold: Optional[float] = None
    latency_threshold_ms: Optional[float] = None
    error_rate_threshold: Optional[float] = None
    check_interval_minutes: Optional[int] = None
    enabled: Optional[bool] = None


@strawberry.input
class LogPredictionInput:
    """Input for logging a prediction."""
    model_name: str
    prediction: float
    actual: Optional[float] = None
    latency_ms: float = 0
    features: Optional[JSON] = None


@strawberry.input
class SetBaselineInput:
    """Input for setting model baseline."""
    model_id: UUID
    model_name: str
    metrics: JSON
    feature_distributions: Optional[JSON] = None


@strawberry.input
class AlertFilterInput:
    """Input for filtering alerts."""
    model_name: Optional[str] = None
    severity: Optional[str] = None
    alert_type: Optional[str] = None
    acknowledged: Optional[bool] = None
    since: Optional[datetime] = None
