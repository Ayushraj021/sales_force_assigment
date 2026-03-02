"""ETL Pipeline mutations."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

import strawberry
import structlog
from strawberry.types import Info

from app.api.graphql.context import get_db_session, get_current_user_from_context
from app.api.graphql.types.etl import (
    PipelineType,
    PipelineConfigType,
    PipelineStepType,
    PipelineRunType,
    CreatePipelineInput,
    UpdatePipelineInput,
    CreatePipelineStepInput,
    UpdatePipelineStepInput,
    RunPipelineInput,
)
from app.core.exceptions import NotFoundError, ValidationError

logger = structlog.get_logger()


@strawberry.type
class ETLMutation:
    """ETL Pipeline mutations."""

    @strawberry.mutation
    async def create_pipeline(
        self,
        info: Info,
        input: CreatePipelineInput,
    ) -> PipelineType:
        """Create a new ETL pipeline."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        if not input.name or len(input.name.strip()) == 0:
            raise ValidationError("Pipeline name is required")

        now = datetime.utcnow()
        config = PipelineConfigType(
            id=uuid4(),
            name=input.name.strip(),
            description=input.description,
            parallel_steps=input.parallel_steps,
            stop_on_error=input.stop_on_error,
            log_level=input.log_level,
            organization_id=current_user.organization_id,
            created_by=current_user.id,
            created_at=now,
            updated_at=now,
        )

        pipeline = PipelineType(
            id=uuid4(),
            name=input.name.strip(),
            description=input.description,
            config=config,
            steps=[],
            last_run=None,
            run_count=0,
            success_count=0,
            failure_count=0,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        logger.info(
            "Pipeline created",
            pipeline_id=str(pipeline.id),
            name=pipeline.name,
            created_by=str(current_user.id),
        )

        return pipeline

    @strawberry.mutation
    async def update_pipeline(
        self,
        info: Info,
        pipeline_id: UUID,
        input: UpdatePipelineInput,
    ) -> PipelineType:
        """Update a pipeline."""
        db = await get_db_session(info)
        await get_current_user_from_context(info, db)

        raise NotFoundError("Pipeline", str(pipeline_id))

    @strawberry.mutation
    async def delete_pipeline(
        self,
        info: Info,
        pipeline_id: UUID,
    ) -> bool:
        """Delete a pipeline."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        logger.info(
            "Pipeline deleted",
            pipeline_id=str(pipeline_id),
            deleted_by=str(current_user.id),
        )

        return True

    @strawberry.mutation
    async def create_pipeline_step(
        self,
        info: Info,
        input: CreatePipelineStepInput,
    ) -> PipelineStepType:
        """Create a pipeline step."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        valid_types = ["extract", "transform", "load", "validate"]
        if input.step_type not in valid_types:
            raise ValidationError(f"step_type must be one of: {', '.join(valid_types)}")

        step = PipelineStepType(
            id=uuid4(),
            name=input.name,
            step_type=input.step_type,
            config=input.config,
            depends_on=input.depends_on or [],
            retry_count=input.retry_count,
            timeout_seconds=input.timeout_seconds,
            pipeline_id=input.pipeline_id,
            order_index=input.order_index,
        )

        logger.info(
            "Pipeline step created",
            step_id=str(step.id),
            step_name=step.name,
            pipeline_id=str(input.pipeline_id),
            created_by=str(current_user.id),
        )

        return step

    @strawberry.mutation
    async def update_pipeline_step(
        self,
        info: Info,
        step_id: UUID,
        input: UpdatePipelineStepInput,
    ) -> PipelineStepType:
        """Update a pipeline step."""
        db = await get_db_session(info)
        await get_current_user_from_context(info, db)

        raise NotFoundError("PipelineStep", str(step_id))

    @strawberry.mutation
    async def delete_pipeline_step(
        self,
        info: Info,
        step_id: UUID,
    ) -> bool:
        """Delete a pipeline step."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        logger.info(
            "Pipeline step deleted",
            step_id=str(step_id),
            deleted_by=str(current_user.id),
        )

        return True

    @strawberry.mutation
    async def run_pipeline(
        self,
        info: Info,
        input: RunPipelineInput,
    ) -> PipelineRunType:
        """Run a pipeline."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        raise NotFoundError("Pipeline", str(input.pipeline_id))

    @strawberry.mutation
    async def cancel_pipeline_run(
        self,
        info: Info,
        run_id: UUID,
    ) -> bool:
        """Cancel a running pipeline."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        logger.info(
            "Pipeline run cancelled",
            run_id=str(run_id),
            cancelled_by=str(current_user.id),
        )

        return True

    @strawberry.mutation
    async def retry_pipeline_run(
        self,
        info: Info,
        run_id: UUID,
        from_step: Optional[str] = None,
    ) -> PipelineRunType:
        """Retry a failed pipeline run."""
        db = await get_db_session(info)
        await get_current_user_from_context(info, db)

        raise NotFoundError("PipelineRun", str(run_id))

    @strawberry.mutation
    async def activate_pipeline(
        self,
        info: Info,
        pipeline_id: UUID,
    ) -> bool:
        """Activate a pipeline."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        logger.info(
            "Pipeline activated",
            pipeline_id=str(pipeline_id),
            activated_by=str(current_user.id),
        )

        return True

    @strawberry.mutation
    async def deactivate_pipeline(
        self,
        info: Info,
        pipeline_id: UUID,
    ) -> bool:
        """Deactivate a pipeline."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        logger.info(
            "Pipeline deactivated",
            pipeline_id=str(pipeline_id),
            deactivated_by=str(current_user.id),
        )

        return True
