"""Model queries."""

from typing import Optional
from uuid import UUID

import strawberry
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from strawberry.types import Info

from app.api.graphql.context import get_db_session, get_current_user_from_context
from app.api.graphql.types.model import (
    ModelType,
    ModelVersionType,
    ModelParameterType,
    AdstockConfigType,
    SaturationConfigType,
    ExperimentType,
    ExperimentRunType,
)
from app.core.exceptions import NotFoundError
from app.infrastructure.database.models.model import (
    Model,
    ModelVersion,
    Experiment,
    ExperimentRun,
)


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
            metrics=v.metrics,
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
            fitted_params=a.fitted_params,
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
            fitted_params=s.fitted_params,
        )
        for s in model.saturation_configs
    ]

    return ModelType(
        id=model.id,
        name=model.name,
        description=model.description,
        model_type=model.model_type,
        status=model.status,
        config=model.config,
        hyperparameters=model.hyperparameters,
        versions=versions,
        parameters=parameters,
        adstock_configs=adstock_configs,
        saturation_configs=saturation_configs,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def experiment_to_graphql(experiment: Experiment) -> ExperimentType:
    """Convert database experiment to GraphQL type."""
    runs = [
        ExperimentRunType(
            id=r.id,
            run_name=r.run_name,
            status=r.status,
            mlflow_run_id=r.mlflow_run_id,
            parameters=r.parameters,
            hyperparameters=r.hyperparameters,
            metrics=r.metrics,
            duration_seconds=r.duration_seconds,
            created_at=r.created_at,
        )
        for r in experiment.runs
    ]

    return ExperimentType(
        id=experiment.id,
        name=experiment.name,
        description=experiment.description,
        status=experiment.status,
        mlflow_experiment_id=experiment.mlflow_experiment_id,
        config=experiment.config,
        runs=runs,
        created_at=experiment.created_at,
        updated_at=experiment.updated_at,
    )


@strawberry.type
class ModelQuery:
    """Model queries."""

    @strawberry.field
    async def model(self, info: Info, id: UUID) -> ModelType:
        """Get a model by ID."""
        db = await get_db_session(info)
        await get_current_user_from_context(info, db)

        query = (
            select(Model)
            .options(
                selectinload(Model.versions),
                selectinload(Model.parameters),
                selectinload(Model.adstock_configs),
                selectinload(Model.saturation_configs),
            )
            .where(Model.id == id)
        )
        result = await db.execute(query)
        model = result.scalar_one_or_none()

        if not model:
            raise NotFoundError("Model", str(id))

        return model_to_graphql(model)

    @strawberry.field
    async def models(
        self,
        info: Info,
        model_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ModelType]:
        """Get list of models."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        query = (
            select(Model)
            .options(
                selectinload(Model.versions),
                selectinload(Model.parameters),
                selectinload(Model.adstock_configs),
                selectinload(Model.saturation_configs),
            )
            .where(Model.organization_id == current_user.organization_id)
        )

        if model_type:
            query = query.where(Model.model_type == model_type)
        if status:
            query = query.where(Model.status == status)

        query = query.limit(limit).offset(offset)
        result = await db.execute(query)
        models = result.scalars().all()

        return [model_to_graphql(m) for m in models]

    @strawberry.field
    async def experiment(self, info: Info, id: UUID) -> ExperimentType:
        """Get an experiment by ID."""
        db = await get_db_session(info)
        await get_current_user_from_context(info, db)

        query = (
            select(Experiment)
            .options(selectinload(Experiment.runs))
            .where(Experiment.id == id)
        )
        result = await db.execute(query)
        experiment = result.scalar_one_or_none()

        if not experiment:
            raise NotFoundError("Experiment", str(id))

        return experiment_to_graphql(experiment)

    @strawberry.field
    async def experiments(
        self,
        info: Info,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ExperimentType]:
        """Get list of experiments."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        query = (
            select(Experiment)
            .options(selectinload(Experiment.runs))
            .where(Experiment.organization_id == current_user.organization_id)
        )

        if status:
            query = query.where(Experiment.status == status)

        query = query.limit(limit).offset(offset)
        result = await db.execute(query)
        experiments = result.scalars().all()

        return [experiment_to_graphql(e) for e in experiments]
