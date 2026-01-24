"""Experiment management mutations."""

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
    CreateExperimentInput,
    ExperimentRunType,
    ExperimentType,
)
from app.core.exceptions import NotFoundError, ValidationError
from app.infrastructure.database.models.model import Experiment, ExperimentRun

logger = structlog.get_logger()


def run_to_graphql(run: ExperimentRun) -> ExperimentRunType:
    """Convert experiment run to GraphQL type."""
    return ExperimentRunType(
        id=run.id,
        run_name=run.run_name,
        status=run.status,
        mlflow_run_id=run.mlflow_run_id,
        parameters=run.parameters,
        hyperparameters=run.hyperparameters,
        metrics=run.metrics,
        duration_seconds=run.duration_seconds,
        created_at=run.created_at,
    )


def experiment_to_graphql(experiment: Experiment) -> ExperimentType:
    """Convert experiment to GraphQL type."""
    return ExperimentType(
        id=experiment.id,
        name=experiment.name,
        description=experiment.description,
        status=experiment.status,
        mlflow_experiment_id=experiment.mlflow_experiment_id,
        config=experiment.config,
        runs=[run_to_graphql(r) for r in experiment.runs],
        created_at=experiment.created_at,
        updated_at=experiment.updated_at,
    )


@strawberry.input
class UpdateExperimentInput:
    """Input for updating an experiment."""

    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    config: Optional[JSON] = None


@strawberry.input
class RunExperimentInput:
    """Input for running an experiment."""

    experiment_id: UUID
    run_name: Optional[str] = None
    parameters: Optional[JSON] = None
    hyperparameters: Optional[JSON] = None


@strawberry.type
class ExperimentMutation:
    """Experiment management mutations."""

    @strawberry.mutation
    async def create_experiment(
        self,
        info: Info,
        input: CreateExperimentInput,
    ) -> ExperimentType:
        """Create a new experiment."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Validate name
        if not input.name or len(input.name.strip()) == 0:
            raise ValidationError("Experiment name is required")

        # Check for duplicate name in organization
        result = await db.execute(
            select(Experiment).where(
                Experiment.organization_id == current_user.organization_id,
                Experiment.name == input.name.strip(),
            )
        )
        if result.scalar_one_or_none():
            raise ValidationError(f"An experiment named '{input.name}' already exists")

        # Create experiment
        experiment = Experiment(
            id=uuid4(),
            name=input.name.strip(),
            description=input.description,
            status="active",
            config=input.config or {},
            organization_id=current_user.organization_id,
        )
        db.add(experiment)

        await db.commit()

        # Reload with runs
        result = await db.execute(
            select(Experiment)
            .options(selectinload(Experiment.runs))
            .where(Experiment.id == experiment.id)
        )
        experiment = result.scalar_one()

        logger.info(
            "Experiment created",
            experiment_id=str(experiment.id),
            created_by=str(current_user.id),
        )

        return experiment_to_graphql(experiment)

    @strawberry.mutation
    async def update_experiment(
        self,
        info: Info,
        experiment_id: UUID,
        input: UpdateExperimentInput,
    ) -> ExperimentType:
        """Update an experiment."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Get experiment
        result = await db.execute(
            select(Experiment)
            .options(selectinload(Experiment.runs))
            .where(
                Experiment.id == experiment_id,
                Experiment.organization_id == current_user.organization_id,
            )
        )
        experiment = result.scalar_one_or_none()

        if not experiment:
            raise NotFoundError("Experiment", str(experiment_id))

        # Update fields
        if input.name is not None:
            if len(input.name.strip()) == 0:
                raise ValidationError("Experiment name cannot be empty")
            experiment.name = input.name.strip()

        if input.description is not None:
            experiment.description = input.description

        if input.status is not None:
            valid_statuses = {"active", "completed", "archived", "paused"}
            if input.status not in valid_statuses:
                raise ValidationError(f"Invalid status. Valid: {', '.join(valid_statuses)}")
            experiment.status = input.status

        if input.config is not None:
            existing_config = experiment.config or {}
            experiment.config = {**existing_config, **input.config}

        await db.commit()
        await db.refresh(experiment)

        logger.info(
            "Experiment updated",
            experiment_id=str(experiment.id),
            updated_by=str(current_user.id),
        )

        return experiment_to_graphql(experiment)

    @strawberry.mutation
    async def delete_experiment(
        self,
        info: Info,
        experiment_id: UUID,
    ) -> bool:
        """Delete an experiment (archive it)."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Get experiment
        result = await db.execute(
            select(Experiment).where(
                Experiment.id == experiment_id,
                Experiment.organization_id == current_user.organization_id,
            )
        )
        experiment = result.scalar_one_or_none()

        if not experiment:
            raise NotFoundError("Experiment", str(experiment_id))

        # Archive instead of delete
        experiment.status = "archived"

        await db.commit()

        logger.info(
            "Experiment deleted",
            experiment_id=str(experiment.id),
            deleted_by=str(current_user.id),
        )

        return True

    @strawberry.mutation
    async def run_experiment(
        self,
        info: Info,
        input: RunExperimentInput,
    ) -> ExperimentRunType:
        """Start a new run in an experiment."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Get experiment
        result = await db.execute(
            select(Experiment).where(
                Experiment.id == input.experiment_id,
                Experiment.organization_id == current_user.organization_id,
            )
        )
        experiment = result.scalar_one_or_none()

        if not experiment:
            raise NotFoundError("Experiment", str(input.experiment_id))

        if experiment.status == "archived":
            raise ValidationError("Cannot run archived experiment")

        # Count existing runs for auto-naming
        result = await db.execute(
            select(ExperimentRun).where(ExperimentRun.experiment_id == experiment.id)
        )
        existing_runs = result.scalars().all()
        run_number = len(existing_runs) + 1

        # Create experiment run
        run = ExperimentRun(
            id=uuid4(),
            experiment_id=experiment.id,
            run_name=input.run_name or f"Run #{run_number}",
            status="pending",
            parameters=input.parameters or {},
            hyperparameters=input.hyperparameters or {},
        )
        db.add(run)

        await db.commit()
        await db.refresh(run)

        logger.info(
            "Experiment run created",
            run_id=str(run.id),
            experiment_id=str(experiment.id),
            run_by=str(current_user.id),
        )

        # TODO: Queue the experiment run task
        # from app.infrastructure.celery.tasks import run_experiment_task
        # run_experiment_task.delay(str(run.id))

        return run_to_graphql(run)

    @strawberry.mutation
    async def cancel_experiment_run(
        self,
        info: Info,
        run_id: UUID,
    ) -> ExperimentRunType:
        """Cancel a running experiment run."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Get run with experiment join for org check
        result = await db.execute(
            select(ExperimentRun)
            .join(Experiment)
            .where(
                ExperimentRun.id == run_id,
                Experiment.organization_id == current_user.organization_id,
            )
        )
        run = result.scalar_one_or_none()

        if not run:
            raise NotFoundError("Experiment run", str(run_id))

        if run.status not in {"pending", "running"}:
            raise ValidationError(f"Cannot cancel run with status '{run.status}'")

        run.status = "cancelled"

        await db.commit()
        await db.refresh(run)

        logger.info(
            "Experiment run cancelled",
            run_id=str(run.id),
            cancelled_by=str(current_user.id),
        )

        return run_to_graphql(run)
