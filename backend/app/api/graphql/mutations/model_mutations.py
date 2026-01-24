"""Model management mutations."""

from typing import Optional
from uuid import UUID, uuid4

import strawberry
import structlog
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from strawberry.scalars import JSON
from strawberry.types import Info

from app.api.graphql.context import get_db_session, get_current_user_from_context
from app.api.graphql.types.model import (
    CreateModelInput,
    ModelType,
    ModelVersionType,
    ModelParameterType,
    AdstockConfigType,
    SaturationConfigType,
    AdstockConfigInput,
    SaturationConfigInput,
)
from app.core.exceptions import NotFoundError, ValidationError, ConflictError
from app.infrastructure.database.models.dataset import Dataset
from app.infrastructure.database.models.model import (
    Model,
    ModelVersion,
    ModelStatus,
    AdstockConfig,
    SaturationConfig,
)

logger = structlog.get_logger()


def model_to_graphql(model: Model) -> ModelType:
    """Convert database model to GraphQL type."""
    versions = [
        ModelVersionType(
            id=v.id,
            version=v.version,
            description=v.description,
            is_current=v.is_current,
            status=v.status,
            training_duration_seconds=v.training_duration_seconds,
            mlflow_run_id=v.mlflow_run_id,
            metrics=v.metrics or {},
            created_at=v.created_at,
        )
        for v in model.versions
    ]

    parameters = [
        ModelParameterType(
            id=p.id,
            parameter_name=p.parameter_name,
            parameter_type=p.parameter_type,
            value=p.value,
            std_error=p.std_error,
            ci_lower=p.ci_lower,
            ci_upper=p.ci_upper,
            posterior_mean=p.posterior_mean,
            posterior_std=p.posterior_std,
        )
        for p in model.parameters
    ]

    adstock_configs = [
        AdstockConfigType(
            id=a.id,
            channel_name=a.channel_name,
            adstock_type=a.adstock_type,
            decay_rate=a.decay_rate,
            shape=a.shape,
            scale=a.scale,
            max_lag=a.max_lag,
            normalize=a.normalize,
            fitted_params=a.fitted_params or {},
        )
        for a in model.adstock_configs
    ]

    saturation_configs = [
        SaturationConfigType(
            id=s.id,
            channel_name=s.channel_name,
            saturation_type=s.saturation_type,
            alpha=s.alpha,
            gamma=s.gamma,
            k=s.k,
            m=s.m,
            vmax=s.vmax,
            km=s.km,
            fitted_params=s.fitted_params or {},
        )
        for s in model.saturation_configs
    ]

    return ModelType(
        id=model.id,
        name=model.name,
        description=model.description,
        model_type=model.model_type,
        status=model.status,
        config=model.config or {},
        hyperparameters=model.hyperparameters or {},
        versions=versions,
        parameters=parameters,
        adstock_configs=adstock_configs,
        saturation_configs=saturation_configs,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


@strawberry.input
class UpdateModelInput:
    """Input for updating a model."""

    name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[JSON] = None
    hyperparameters: Optional[JSON] = None


@strawberry.input
class TrainModelRequestInput:
    """Input for starting model training."""

    adstock_configs: Optional[list[AdstockConfigInput]] = None
    saturation_configs: Optional[list[SaturationConfigInput]] = None
    hyperparameters: Optional[JSON] = None


@strawberry.type
class TrainingJobResult:
    """Result of starting a training job."""

    model_id: UUID
    version_id: UUID
    status: str
    message: str


@strawberry.type
class ModelMutation:
    """Model management mutations."""

    @strawberry.mutation
    async def create_model(
        self,
        info: Info,
        input: CreateModelInput,
    ) -> ModelType:
        """Create a new model."""
        db = await get_db_session(info)
        user = await get_current_user_from_context(info, db)

        # Validate input
        if not input.name or len(input.name.strip()) == 0:
            raise ValidationError("Model name is required")

        # Validate model type
        valid_types = ["pymc_mmm", "robyn_mmm", "custom_mmm", "prophet", "arima", "ensemble", "hierarchical"]
        if input.model_type not in valid_types:
            raise ValidationError(f"Invalid model type. Must be one of: {', '.join(valid_types)}")

        # Validate dataset exists
        result = await db.execute(
            select(Dataset).where(
                Dataset.id == input.dataset_id,
                Dataset.organization_id == user.organization_id,
                Dataset.is_active == True,
            )
        )
        dataset = result.scalar_one_or_none()

        if not dataset:
            raise NotFoundError("Dataset", str(input.dataset_id))

        # Create model
        model = Model(
            id=uuid4(),
            name=input.name.strip(),
            description=input.description,
            model_type=input.model_type,
            status=ModelStatus.DRAFT.value,
            dataset_id=input.dataset_id,
            organization_id=user.organization_id,
            config=input.config or {},
            hyperparameters={},
        )
        db.add(model)

        await db.commit()

        # Re-fetch model with all relationships eagerly loaded
        query = (
            select(Model)
            .options(
                selectinload(Model.versions),
                selectinload(Model.parameters),
                selectinload(Model.adstock_configs),
                selectinload(Model.saturation_configs),
            )
            .where(Model.id == model.id)
        )
        result = await db.execute(query)
        model = result.scalar_one()

        logger.info(
            "Model created",
            model_id=str(model.id),
            user_id=str(user.id),
            model_type=model.model_type,
        )

        return model_to_graphql(model)

    @strawberry.mutation
    async def update_model(
        self,
        info: Info,
        id: UUID,
        input: UpdateModelInput,
    ) -> ModelType:
        """Update an existing model."""
        db = await get_db_session(info)
        user = await get_current_user_from_context(info, db)

        # Get model with relationships
        query = (
            select(Model)
            .options(
                selectinload(Model.versions),
                selectinload(Model.parameters),
                selectinload(Model.adstock_configs),
                selectinload(Model.saturation_configs),
            )
            .where(
                Model.id == id,
                Model.organization_id == user.organization_id,
            )
        )
        result = await db.execute(query)
        model = result.scalar_one_or_none()

        if not model:
            raise NotFoundError("Model", str(id))

        # Check if model is in a state that allows updates
        if model.status == ModelStatus.TRAINING.value:
            raise ConflictError("Cannot update model while training is in progress")

        # Update fields
        if input.name is not None:
            if len(input.name.strip()) == 0:
                raise ValidationError("Model name cannot be empty")
            model.name = input.name.strip()

        if input.description is not None:
            model.description = input.description

        if input.config is not None:
            model.config = input.config

        if input.hyperparameters is not None:
            model.hyperparameters = input.hyperparameters

        await db.commit()

        # Re-fetch model with all relationships eagerly loaded
        query = (
            select(Model)
            .options(
                selectinload(Model.versions),
                selectinload(Model.parameters),
                selectinload(Model.adstock_configs),
                selectinload(Model.saturation_configs),
            )
            .where(Model.id == model.id)
        )
        result = await db.execute(query)
        model = result.scalar_one()

        logger.info(
            "Model updated",
            model_id=str(model.id),
            user_id=str(user.id),
        )

        return model_to_graphql(model)

    @strawberry.mutation
    async def delete_model(
        self,
        info: Info,
        id: UUID,
    ) -> bool:
        """Delete a model (archives it)."""
        db = await get_db_session(info)
        user = await get_current_user_from_context(info, db)

        # Get model
        result = await db.execute(
            select(Model).where(
                Model.id == id,
                Model.organization_id == user.organization_id,
            )
        )
        model = result.scalar_one_or_none()

        if not model:
            raise NotFoundError("Model", str(id))

        # Check if model is training
        if model.status == ModelStatus.TRAINING.value:
            raise ConflictError("Cannot delete model while training is in progress")

        # Archive the model
        model.status = ModelStatus.ARCHIVED.value

        await db.commit()

        logger.info(
            "Model deleted (archived)",
            model_id=str(model.id),
            user_id=str(user.id),
        )

        return True

    @strawberry.mutation
    async def train_model(
        self,
        info: Info,
        model_id: UUID,
        input: Optional[TrainModelRequestInput] = None,
    ) -> TrainingJobResult:
        """Start training a model."""
        db = await get_db_session(info)
        user = await get_current_user_from_context(info, db)

        # Get model
        query = (
            select(Model)
            .options(
                selectinload(Model.versions),
                selectinload(Model.adstock_configs),
                selectinload(Model.saturation_configs),
            )
            .where(
                Model.id == model_id,
                Model.organization_id == user.organization_id,
            )
        )
        result = await db.execute(query)
        model = result.scalar_one_or_none()

        if not model:
            raise NotFoundError("Model", str(model_id))

        # Check if model is already training
        if model.status == ModelStatus.TRAINING.value:
            raise ConflictError("Model is already being trained")

        # Check if dataset is set
        if not model.dataset_id:
            raise ValidationError("Model must have a dataset before training")

        # Calculate next version number
        existing_versions = len(model.versions)
        next_version = f"v{existing_versions + 1}"

        # Create new version
        version = ModelVersion(
            id=uuid4(),
            model_id=model.id,
            version=next_version,
            description=f"Training started by {user.email}",
            is_current=False,
            status=ModelStatus.TRAINING.value,
            trained_by_user_id=user.id,
        )
        db.add(version)

        # Update model status
        model.status = ModelStatus.TRAINING.value

        # Store adstock configs if provided
        if input and input.adstock_configs:
            for ac in input.adstock_configs:
                adstock = AdstockConfig(
                    id=uuid4(),
                    model_id=model.id,
                    channel_name=ac.channel_name,
                    adstock_type=ac.adstock_type,
                    decay_rate=ac.decay_rate,
                    shape=ac.shape,
                    scale=ac.scale,
                    max_lag=ac.max_lag,
                    normalize=ac.normalize,
                )
                db.add(adstock)

        # Store saturation configs if provided
        if input and input.saturation_configs:
            for sc in input.saturation_configs:
                saturation = SaturationConfig(
                    id=uuid4(),
                    model_id=model.id,
                    channel_name=sc.channel_name,
                    saturation_type=sc.saturation_type,
                    alpha=sc.alpha_prior,
                    gamma=sc.gamma_prior,
                )
                db.add(saturation)

        # Update hyperparameters if provided
        if input and input.hyperparameters:
            model.hyperparameters = {**model.hyperparameters, **input.hyperparameters}

        await db.commit()

        logger.info(
            "Model training started",
            model_id=str(model.id),
            version_id=str(version.id),
            user_id=str(user.id),
        )

        # Build training config
        # Config may have camelCase (from frontend) or snake_case keys
        config = model.config or {}
        target_column = config.get("targetColumn") or config.get("target_column")
        date_column = config.get("dateColumn") or config.get("date_column")
        channel_columns = config.get("channelColumns") or config.get("channel_columns") or []
        control_columns = config.get("controlColumns") or config.get("control_columns") or []

        training_config = {
            "model_type": model.model_type,
            "version_id": str(version.id),
            "target_column": target_column,
            "date_column": date_column,
            "channel_columns": channel_columns,
            "channels": [],
            "control_columns": control_columns,
            **(model.hyperparameters or {}),
        }

        # Add channel configs from adstock configs if present
        for ac in model.adstock_configs:
            training_config["channels"].append({
                "name": ac.channel_name,
                "spend_column": ac.channel_name,
                "adstock_type": ac.adstock_type,
                "decay_rate": ac.decay_rate,
                "max_lag": ac.max_lag,
            })

        # If no adstock configs, create channels from channelColumns
        if not training_config["channels"] and channel_columns:
            for col in channel_columns:
                training_config["channels"].append({
                    "name": col,
                    "spend_column": col,
                    "adstock_type": "geometric",
                    "saturation_type": "hill",
                })

        # Dispatch Celery task for actual training
        from app.workers.tasks.training import train_mmm_model
        task = train_mmm_model.delay(
            model_id=str(model.id),
            dataset_id=str(model.dataset_id),
            config=training_config,
            user_id=str(user.id),
        )

        logger.info(
            "Training task dispatched",
            model_id=str(model.id),
            task_id=task.id,
        )

        return TrainingJobResult(
            model_id=model.id,
            version_id=version.id,
            status="training",
            message=f"Training job started for model '{model.name}' version {next_version}",
        )

    @strawberry.mutation
    async def cancel_training(
        self,
        info: Info,
        model_id: UUID,
    ) -> bool:
        """Cancel ongoing model training."""
        db = await get_db_session(info)
        user = await get_current_user_from_context(info, db)

        # Get model
        query = (
            select(Model)
            .options(selectinload(Model.versions))
            .where(
                Model.id == model_id,
                Model.organization_id == user.organization_id,
            )
        )
        result = await db.execute(query)
        model = result.scalar_one_or_none()

        if not model:
            raise NotFoundError("Model", str(model_id))

        if model.status != ModelStatus.TRAINING.value:
            raise ConflictError("Model is not currently training")

        # Update model and version status
        model.status = ModelStatus.FAILED.value

        # Find the training version and mark as failed
        for version in model.versions:
            if version.status == ModelStatus.TRAINING.value:
                version.status = ModelStatus.FAILED.value
                version.description = "Training cancelled by user"

        await db.commit()

        logger.info(
            "Model training cancelled",
            model_id=str(model.id),
            user_id=str(user.id),
        )

        # TODO: Actually cancel the Celery task
        # from app.core.celery.app import celery_app
        # celery_app.control.revoke(task_id, terminate=True)

        return True
