"""ETL Pipeline queries."""

from datetime import datetime
from typing import Optional
from uuid import UUID

import strawberry
import structlog
from strawberry.types import Info

from app.api.graphql.context import get_db_session, get_current_user_from_context
from app.api.graphql.types.etl import (
    PipelineType,
    PipelineSummaryType,
    PipelineRunType,
    PipelineStepType,
    StepResultType,
    PipelineFilterInput,
)
from app.core.exceptions import NotFoundError

logger = structlog.get_logger()


@strawberry.type
class ETLQuery:
    """ETL Pipeline queries."""

    @strawberry.field
    async def pipelines(
        self,
        info: Info,
        filter: Optional[PipelineFilterInput] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PipelineSummaryType]:
        """Get all pipelines."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        logger.info(
            "Fetching pipelines",
            user_id=str(current_user.id),
            org_id=str(current_user.organization_id),
        )

        return []

    @strawberry.field
    async def pipeline(
        self,
        info: Info,
        pipeline_id: UUID,
    ) -> PipelineType:
        """Get a specific pipeline by ID."""
        db = await get_db_session(info)
        await get_current_user_from_context(info, db)

        raise NotFoundError("Pipeline", str(pipeline_id))

    @strawberry.field
    async def pipeline_steps(
        self,
        info: Info,
        pipeline_id: UUID,
    ) -> list[PipelineStepType]:
        """Get steps for a pipeline."""
        db = await get_db_session(info)
        await get_current_user_from_context(info, db)

        return []

    @strawberry.field
    async def pipeline_runs(
        self,
        info: Info,
        pipeline_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[PipelineRunType]:
        """Get runs for a pipeline."""
        db = await get_db_session(info)
        await get_current_user_from_context(info, db)

        return []

    @strawberry.field
    async def pipeline_run(
        self,
        info: Info,
        run_id: UUID,
    ) -> PipelineRunType:
        """Get a specific pipeline run."""
        db = await get_db_session(info)
        await get_current_user_from_context(info, db)

        raise NotFoundError("PipelineRun", str(run_id))

    @strawberry.field
    async def step_results(
        self,
        info: Info,
        run_id: UUID,
    ) -> list[StepResultType]:
        """Get step results for a pipeline run."""
        db = await get_db_session(info)
        await get_current_user_from_context(info, db)

        return []

    @strawberry.field
    async def recent_runs(
        self,
        info: Info,
        limit: int = 20,
    ) -> list[PipelineRunType]:
        """Get recent pipeline runs across all pipelines."""
        db = await get_db_session(info)
        await get_current_user_from_context(info, db)

        return []

    @strawberry.field
    async def failed_runs(
        self,
        info: Info,
        since: Optional[datetime] = None,
        limit: int = 50,
    ) -> list[PipelineRunType]:
        """Get failed pipeline runs."""
        db = await get_db_session(info)
        await get_current_user_from_context(info, db)

        return []

    @strawberry.field
    async def step_types(self) -> list[str]:
        """Get available step types."""
        return ["extract", "transform", "load", "validate"]

    @strawberry.field
    async def step_statuses(self) -> list[str]:
        """Get available step statuses."""
        return ["pending", "running", "completed", "failed", "skipped"]
