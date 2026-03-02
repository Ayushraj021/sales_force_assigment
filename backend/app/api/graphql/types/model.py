"""ML Model GraphQL types."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

import strawberry
from strawberry.scalars import JSON


@strawberry.type
class ModelParameterType:
    """Model parameter (coefficient) type."""

    id: UUID
    parameter_name: str
    parameter_type: str
    value: Optional[float]
    std_error: Optional[float]
    ci_lower: Optional[float]
    ci_upper: Optional[float]
    posterior_mean: Optional[float]
    posterior_std: Optional[float]


@strawberry.type
class AdstockConfigType:
    """Adstock transformation configuration."""

    id: UUID
    channel_name: str
    adstock_type: str
    decay_rate: Optional[float]
    shape: Optional[float]
    scale: Optional[float]
    max_lag: int
    normalize: bool
    fitted_params: JSON


@strawberry.type
class SaturationConfigType:
    """Saturation curve configuration."""

    id: UUID
    channel_name: str
    saturation_type: str
    alpha: Optional[float]
    gamma: Optional[float]
    k: Optional[float]
    m: Optional[float]
    vmax: Optional[float]
    km: Optional[float]
    fitted_params: JSON


@strawberry.type
class ModelVersionType:
    """Model version type."""

    id: UUID
    version: str
    description: Optional[str]
    is_current: bool
    status: str
    training_duration_seconds: Optional[float]
    mlflow_run_id: Optional[str]
    metrics: JSON
    created_at: datetime


@strawberry.type
class ModelType:
    """ML Model type."""

    id: UUID
    name: str
    description: Optional[str]
    model_type: str
    status: str
    config: JSON
    hyperparameters: JSON
    versions: list[ModelVersionType]
    parameters: list[ModelParameterType]
    adstock_configs: list[AdstockConfigType]
    saturation_configs: list[SaturationConfigType]
    created_at: datetime
    updated_at: datetime


@strawberry.type
class ExperimentRunType:
    """Experiment run type."""

    id: UUID
    run_name: Optional[str]
    status: str
    mlflow_run_id: Optional[str]
    parameters: JSON
    hyperparameters: JSON
    metrics: JSON
    duration_seconds: Optional[float]
    created_at: datetime


@strawberry.type
class ExperimentType:
    """Experiment type."""

    id: UUID
    name: str
    description: Optional[str]
    status: str
    mlflow_experiment_id: Optional[str]
    config: JSON
    runs: list[ExperimentRunType]
    created_at: datetime
    updated_at: datetime


@strawberry.input
class CreateModelInput:
    """Input for creating a model."""

    name: str
    description: Optional[str] = None
    model_type: str  # pymc_mmm, robyn_mmm, custom_mmm, prophet, etc.
    dataset_id: UUID
    config: Optional[JSON] = None


@strawberry.input
class AdstockConfigInput:
    """Input for adstock configuration."""

    channel_name: str
    adstock_type: str = "geometric"  # geometric, weibull, delayed
    decay_rate: Optional[float] = None
    shape: Optional[float] = None
    scale: Optional[float] = None
    max_lag: int = 8
    normalize: bool = True


@strawberry.input
class SaturationConfigInput:
    """Input for saturation configuration."""

    channel_name: str
    saturation_type: str = "hill"  # hill, logistic, michaelis_menten
    alpha_prior: Optional[float] = None
    gamma_prior: Optional[float] = None


@strawberry.input
class TrainModelInput:
    """Input for training a model."""

    model_id: UUID
    adstock_configs: Optional[list[AdstockConfigInput]] = None
    saturation_configs: Optional[list[SaturationConfigInput]] = None
    hyperparameters: Optional[JSON] = None
    experiment_id: Optional[UUID] = None


@strawberry.input
class CreateExperimentInput:
    """Input for creating an experiment."""

    name: str
    description: Optional[str] = None
    config: Optional[JSON] = None


@strawberry.type
class ForecastType:
    """Forecast result type."""

    id: UUID
    name: str
    description: Optional[str]
    status: str
    model_type: str
    target_metric: str
    horizon: int
    confidence_level: float
    start_date: Optional[str]
    end_date: Optional[str]
    forecast_start_date: Optional[str]
    forecast_end_date: Optional[str]
    predicted_values: JSON
    lower_bounds: JSON
    upper_bounds: JSON
    forecast_dates: JSON
    model_params: JSON
    metrics: JSON
    error_message: Optional[str]
    is_active: bool
    dataset_id: Optional[UUID]
    model_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime


@strawberry.input
class CreateForecastInput:
    """Input for creating a forecast."""

    name: str
    description: Optional[str] = None
    model_type: str  # prophet, arima, ensemble, neural
    target_metric: str
    dataset_id: UUID
    horizon: int = 30
    confidence_level: float = 0.95
    model_params: Optional[JSON] = None


@strawberry.input
class UpdateForecastInput:
    """Input for updating a forecast."""

    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
