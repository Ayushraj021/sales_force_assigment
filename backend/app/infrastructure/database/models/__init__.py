"""Database models."""

from app.infrastructure.database.models.api_key import APIKey
from app.infrastructure.database.models.audit import AuditLog
from app.infrastructure.database.models.base import TimestampMixin, UUIDMixin
from app.infrastructure.database.models.dataset import (
    Channel,
    DataSource,
    Dataset,
    DataVersion,
    Metric,
)
from app.infrastructure.database.models.model import (
    AdstockConfig,
    Experiment,
    ExperimentRun,
    Model,
    ModelParameter,
    ModelVersion,
    SaturationConfig,
)
from app.infrastructure.database.models.optimization import (
    BudgetAllocation,
    BudgetScenario,
    OptimizationConstraint,
    OptimizationResult,
)
from app.infrastructure.database.models.organization import Organization
from app.infrastructure.database.models.report import (
    Dashboard,
    Export,
    Report,
    ScheduledReport,
    Widget,
)
from app.infrastructure.database.models.forecast import Forecast
from app.infrastructure.database.models.user import Permission, Role, User

__all__ = [
    # Base
    "TimestampMixin",
    "UUIDMixin",
    # User & Auth
    "User",
    "Role",
    "Permission",
    "Organization",
    "APIKey",
    "AuditLog",
    # Data
    "DataSource",
    "Dataset",
    "DataVersion",
    "Channel",
    "Metric",
    # Models
    "Model",
    "ModelVersion",
    "ModelParameter",
    "AdstockConfig",
    "SaturationConfig",
    "Experiment",
    "ExperimentRun",
    # Optimization
    "BudgetScenario",
    "OptimizationConstraint",
    "OptimizationResult",
    "BudgetAllocation",
    # Reports
    "Dashboard",
    "Widget",
    "Report",
    "ScheduledReport",
    "Export",
    # Forecasts
    "Forecast",
]
