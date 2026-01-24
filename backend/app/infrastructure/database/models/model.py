"""ML Model and experiment models."""

import uuid
from enum import Enum

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.models.base import TimestampMixin, UUIDMixin
from app.infrastructure.database.session import Base


class ModelType(str, Enum):
    """Model type enumeration."""

    PYMC_MMM = "pymc_mmm"
    ROBYN_MMM = "robyn_mmm"
    CUSTOM_MMM = "custom_mmm"
    PROPHET = "prophet"
    ARIMA = "arima"
    ENSEMBLE = "ensemble"
    HIERARCHICAL = "hierarchical"


class ModelStatus(str, Enum):
    """Model status enumeration."""

    DRAFT = "draft"
    TRAINING = "training"
    TRAINED = "trained"
    FAILED = "failed"
    DEPLOYED = "deployed"
    ARCHIVED = "archived"


class Model(Base, UUIDMixin, TimestampMixin):
    """ML Model definition."""

    __tablename__ = "models"

    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    model_type: Mapped[str] = mapped_column(String(50), index=True)
    status: Mapped[str] = mapped_column(String(50), default=ModelStatus.DRAFT.value)

    # Configuration
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    hyperparameters: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Relationships
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True
    )
    organization: Mapped["Organization"] = relationship(back_populates="models")

    dataset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.id")
    )

    versions: Mapped[list["ModelVersion"]] = relationship(back_populates="model")
    parameters: Mapped[list["ModelParameter"]] = relationship(back_populates="model")
    adstock_configs: Mapped[list["AdstockConfig"]] = relationship(back_populates="model")
    saturation_configs: Mapped[list["SaturationConfig"]] = relationship(back_populates="model")


class ModelVersion(Base, UUIDMixin, TimestampMixin):
    """Model version for tracking trained models."""

    __tablename__ = "model_versions"

    version: Mapped[str] = mapped_column(String(50), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(50), default=ModelStatus.DRAFT.value)

    # Training info
    training_duration_seconds: Mapped[float | None] = mapped_column(Float)
    trained_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    # MLflow tracking
    mlflow_run_id: Mapped[str | None] = mapped_column(String(100))
    mlflow_model_uri: Mapped[str | None] = mapped_column(String(500))

    # Metrics
    metrics: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Model artifacts
    artifact_path: Mapped[str | None] = mapped_column(String(500))

    # Relationship
    model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("models.id"), index=True
    )
    model: Mapped["Model"] = relationship(back_populates="versions")


class ModelParameter(Base, UUIDMixin, TimestampMixin):
    """Trained model parameters (coefficients, etc.)."""

    __tablename__ = "model_parameters"

    parameter_name: Mapped[str] = mapped_column(String(255), index=True)
    parameter_type: Mapped[str] = mapped_column(String(50))  # coefficient, intercept, etc.

    # Values
    value: Mapped[float | None] = mapped_column(Float)
    std_error: Mapped[float | None] = mapped_column(Float)
    ci_lower: Mapped[float | None] = mapped_column(Float)
    ci_upper: Mapped[float | None] = mapped_column(Float)

    # For Bayesian models
    posterior_mean: Mapped[float | None] = mapped_column(Float)
    posterior_std: Mapped[float | None] = mapped_column(Float)
    hdi_lower: Mapped[float | None] = mapped_column(Float)
    hdi_upper: Mapped[float | None] = mapped_column(Float)

    # Relationship
    model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("models.id"), index=True
    )
    model: Mapped["Model"] = relationship(back_populates="parameters")

    model_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_versions.id")
    )


class AdstockConfig(Base, UUIDMixin, TimestampMixin):
    """Adstock transformation configuration per channel."""

    __tablename__ = "adstock_configs"

    channel_name: Mapped[str] = mapped_column(String(255), index=True)
    adstock_type: Mapped[str] = mapped_column(String(50))  # geometric, weibull, delayed

    # Geometric adstock
    decay_rate: Mapped[float | None] = mapped_column(Float)

    # Weibull adstock
    shape: Mapped[float | None] = mapped_column(Float)
    scale: Mapped[float | None] = mapped_column(Float)

    # General
    max_lag: Mapped[int] = mapped_column(Integer, default=8)
    normalize: Mapped[bool] = mapped_column(Boolean, default=True)

    # Prior configuration (for Bayesian models)
    prior_config: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Fitted values
    fitted_params: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Relationship
    model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("models.id"), index=True
    )
    model: Mapped["Model"] = relationship(back_populates="adstock_configs")


class SaturationConfig(Base, UUIDMixin, TimestampMixin):
    """Saturation curve configuration per channel."""

    __tablename__ = "saturation_configs"

    channel_name: Mapped[str] = mapped_column(String(255), index=True)
    saturation_type: Mapped[str] = mapped_column(String(50))  # hill, logistic, michaelis_menten

    # Hill function
    alpha: Mapped[float | None] = mapped_column(Float)  # steepness
    gamma: Mapped[float | None] = mapped_column(Float)  # inflection point

    # Logistic
    k: Mapped[float | None] = mapped_column(Float)  # carrying capacity
    m: Mapped[float | None] = mapped_column(Float)  # midpoint

    # Michaelis-Menten
    vmax: Mapped[float | None] = mapped_column(Float)
    km: Mapped[float | None] = mapped_column(Float)

    # Prior configuration
    prior_config: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Fitted values
    fitted_params: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Relationship
    model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("models.id"), index=True
    )
    model: Mapped["Model"] = relationship(back_populates="saturation_configs")


class Experiment(Base, UUIDMixin, TimestampMixin):
    """Experiment for comparing models."""

    __tablename__ = "experiments"

    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="active")

    # MLflow
    mlflow_experiment_id: Mapped[str | None] = mapped_column(String(100))

    # Configuration
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    tags: Mapped[list] = mapped_column(JSONB, default=list)

    # Relationships
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True
    )
    organization: Mapped["Organization"] = relationship(back_populates="experiments")

    runs: Mapped[list["ExperimentRun"]] = relationship(back_populates="experiment")


class ExperimentRun(Base, UUIDMixin, TimestampMixin):
    """Individual experiment run."""

    __tablename__ = "experiment_runs"

    run_name: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50), default="pending")

    # MLflow
    mlflow_run_id: Mapped[str | None] = mapped_column(String(100))

    # Configuration
    parameters: Mapped[dict] = mapped_column(JSONB, default=dict)
    hyperparameters: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Results
    metrics: Mapped[dict] = mapped_column(JSONB, default=dict)
    artifacts: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Timing
    duration_seconds: Mapped[float | None] = mapped_column(Float)

    # Relationship
    experiment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("experiments.id"), index=True
    )
    experiment: Mapped["Experiment"] = relationship(back_populates="runs")

    model_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_versions.id")
    )


# Import for type hints
from app.infrastructure.database.models.organization import Organization  # noqa: E402
