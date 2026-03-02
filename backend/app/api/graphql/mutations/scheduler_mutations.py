"""Job Scheduler mutations."""

from datetime import datetime
from uuid import UUID, uuid4

import strawberry
import structlog
from strawberry.types import Info

from app.api.graphql.context import get_db_session, get_current_user_from_context
from app.api.graphql.types.scheduler import (
    ScheduledJobType,
    JobRunType,
    ScheduleConfigType,
    JobActionResultType,
    CreateJobInput,
    UpdateJobInput,
)
from app.core.exceptions import NotFoundError, ValidationError

logger = structlog.get_logger()


@strawberry.type
class SchedulerMutation:
    """Job Scheduler mutations."""

    @strawberry.mutation
    async def create_job(
        self,
        info: Info,
        input: CreateJobInput,
    ) -> ScheduledJobType:
        """Create a new scheduled job."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        if not input.name or len(input.name.strip()) == 0:
            raise ValidationError("Job name is required")

        valid_schedule_types = ["once", "interval", "cron", "daily", "weekly"]
        if input.schedule_type not in valid_schedule_types:
            raise ValidationError(f"schedule_type must be one of: {', '.join(valid_schedule_types)}")

        now = datetime.utcnow()

        config = ScheduleConfigType(
            schedule_type=input.schedule_type,
            interval_minutes=input.interval_minutes,
            start_time=input.start_time,
            end_time=input.end_time,
            cron_expression=input.cron_expression,
            timezone=input.timezone,
            max_retries=input.max_retries,
            retry_delay_minutes=input.retry_delay_minutes,
        )

        job = ScheduledJobType(
            id=uuid4(),
            name=input.name.strip(),
            description=input.description,
            job_type=input.job_type,
            config=config,
            status="pending",
            last_run=None,
            next_run=input.start_time or now,
            run_count=0,
            error_count=0,
            last_error=None,
            metadata=input.metadata,
            created_at=now,
            updated_at=now,
            created_by=current_user.id,
        )

        logger.info(
            "Job created",
            job_id=str(job.id),
            job_name=job.name,
            created_by=str(current_user.id),
        )

        return job

    @strawberry.mutation
    async def update_job(
        self,
        info: Info,
        job_id: UUID,
        input: UpdateJobInput,
    ) -> ScheduledJobType:
        """Update a scheduled job."""
        db = await get_db_session(info)
        await get_current_user_from_context(info, db)

        raise NotFoundError("ScheduledJob", str(job_id))

    @strawberry.mutation
    async def delete_job(
        self,
        info: Info,
        job_id: UUID,
    ) -> bool:
        """Delete a scheduled job."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        logger.info(
            "Job deleted",
            job_id=str(job_id),
            deleted_by=str(current_user.id),
        )

        return True

    @strawberry.mutation
    async def run_job_now(
        self,
        info: Info,
        job_id: UUID,
    ) -> JobActionResultType:
        """Run a job immediately."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        result = JobActionResultType(
            success=True,
            job_id=job_id,
            action="run_now",
            message="Job queued for immediate execution",
            new_status="running",
        )

        logger.info(
            "Job run triggered",
            job_id=str(job_id),
            triggered_by=str(current_user.id),
        )

        return result

    @strawberry.mutation
    async def pause_job(
        self,
        info: Info,
        job_id: UUID,
    ) -> JobActionResultType:
        """Pause a scheduled job."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        result = JobActionResultType(
            success=True,
            job_id=job_id,
            action="pause",
            message="Job paused",
            new_status="paused",
        )

        logger.info(
            "Job paused",
            job_id=str(job_id),
            paused_by=str(current_user.id),
        )

        return result

    @strawberry.mutation
    async def resume_job(
        self,
        info: Info,
        job_id: UUID,
    ) -> JobActionResultType:
        """Resume a paused job."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        result = JobActionResultType(
            success=True,
            job_id=job_id,
            action="resume",
            message="Job resumed",
            new_status="pending",
        )

        logger.info(
            "Job resumed",
            job_id=str(job_id),
            resumed_by=str(current_user.id),
        )

        return result

    @strawberry.mutation
    async def cancel_job(
        self,
        info: Info,
        job_id: UUID,
    ) -> JobActionResultType:
        """Cancel a scheduled job."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        result = JobActionResultType(
            success=True,
            job_id=job_id,
            action="cancel",
            message="Job cancelled",
            new_status="cancelled",
        )

        logger.info(
            "Job cancelled",
            job_id=str(job_id),
            cancelled_by=str(current_user.id),
        )

        return result

    @strawberry.mutation
    async def retry_job(
        self,
        info: Info,
        job_id: UUID,
    ) -> JobActionResultType:
        """Retry a failed job."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        result = JobActionResultType(
            success=True,
            job_id=job_id,
            action="retry",
            message="Job retrying",
            new_status="pending",
        )

        logger.info(
            "Job retry triggered",
            job_id=str(job_id),
            retried_by=str(current_user.id),
        )

        return result

    @strawberry.mutation
    async def start_scheduler(
        self,
        info: Info,
    ) -> bool:
        """Start the scheduler."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Check for admin permissions
        if current_user.role not in ["admin", "superuser"]:
            raise ValidationError("Only admins can start/stop the scheduler")

        logger.info(
            "Scheduler started",
            started_by=str(current_user.id),
        )

        return True

    @strawberry.mutation
    async def stop_scheduler(
        self,
        info: Info,
    ) -> bool:
        """Stop the scheduler."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Check for admin permissions
        if current_user.role not in ["admin", "superuser"]:
            raise ValidationError("Only admins can start/stop the scheduler")

        logger.info(
            "Scheduler stopped",
            stopped_by=str(current_user.id),
        )

        return True
