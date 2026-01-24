"""Job Scheduler queries."""

from datetime import datetime
from typing import Optional
from uuid import UUID

import strawberry
import structlog
from strawberry.types import Info

from app.api.graphql.context import get_db_session, get_current_user_from_context
from app.api.graphql.types.scheduler import (
    ScheduledJobType,
    JobRunType,
    JobSummaryType,
    SchedulerStatusType,
    JobFilterInput,
)
from app.core.exceptions import NotFoundError

logger = structlog.get_logger()


@strawberry.type
class SchedulerQuery:
    """Job Scheduler queries."""

    @strawberry.field
    async def scheduled_jobs(
        self,
        info: Info,
        filter: Optional[JobFilterInput] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ScheduledJobType]:
        """Get all scheduled jobs."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        logger.info(
            "Fetching scheduled jobs",
            user_id=str(current_user.id),
            org_id=str(current_user.organization_id),
        )

        return []

    @strawberry.field
    async def scheduled_job(
        self,
        info: Info,
        job_id: UUID,
    ) -> ScheduledJobType:
        """Get a specific scheduled job."""
        db = await get_db_session(info)
        await get_current_user_from_context(info, db)

        raise NotFoundError("ScheduledJob", str(job_id))

    @strawberry.field
    async def job_runs(
        self,
        info: Info,
        job_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[JobRunType]:
        """Get runs for a job."""
        db = await get_db_session(info)
        await get_current_user_from_context(info, db)

        return []

    @strawberry.field
    async def job_run(
        self,
        info: Info,
        run_id: UUID,
    ) -> JobRunType:
        """Get a specific job run."""
        db = await get_db_session(info)
        await get_current_user_from_context(info, db)

        raise NotFoundError("JobRun", str(run_id))

    @strawberry.field
    async def pending_jobs(
        self,
        info: Info,
    ) -> list[ScheduledJobType]:
        """Get all pending jobs."""
        db = await get_db_session(info)
        await get_current_user_from_context(info, db)

        return []

    @strawberry.field
    async def running_jobs(
        self,
        info: Info,
    ) -> list[ScheduledJobType]:
        """Get all currently running jobs."""
        db = await get_db_session(info)
        await get_current_user_from_context(info, db)

        return []

    @strawberry.field
    async def failed_jobs(
        self,
        info: Info,
        since: Optional[datetime] = None,
    ) -> list[ScheduledJobType]:
        """Get failed jobs."""
        db = await get_db_session(info)
        await get_current_user_from_context(info, db)

        return []

    @strawberry.field
    async def job_summaries(
        self,
        info: Info,
    ) -> list[JobSummaryType]:
        """Get job summaries."""
        db = await get_db_session(info)
        await get_current_user_from_context(info, db)

        return []

    @strawberry.field
    async def scheduler_status(
        self,
        info: Info,
    ) -> SchedulerStatusType:
        """Get scheduler status."""
        db = await get_db_session(info)
        await get_current_user_from_context(info, db)

        return SchedulerStatusType(
            running=False,
            total_jobs=0,
            pending_jobs=0,
            running_jobs=0,
            failed_jobs=0,
            paused_jobs=0,
            next_job_at=None,
            last_checked_at=None,
        )

    @strawberry.field
    async def schedule_types(self) -> list[str]:
        """Get available schedule types."""
        return ["once", "interval", "cron", "daily", "weekly"]

    @strawberry.field
    async def job_statuses(self) -> list[str]:
        """Get available job statuses."""
        return ["pending", "running", "completed", "failed", "paused", "cancelled"]
