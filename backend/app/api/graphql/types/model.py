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
