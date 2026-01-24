"""Job Scheduler GraphQL types."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

import strawberry
from strawberry.scalars import JSON


@strawberry.enum
class ScheduleTypeEnum(Enum):
    """Schedule types."""
    ONCE = "once"
    INTERVAL = "interval"
    CRON = "cron"
    DAILY = "daily"
    WEEKLY = "weekly"


@strawberry.enum
class JobStatusEnum(Enum):
    """Job status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


@strawberry.type
class ScheduleConfigType:
    """Schedule configuration."""
    schedule_type: str
    interval_minutes: int
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    cron_expression: Optional[str]
    timezone: str
    max_retries: int
    retry_delay_minutes: int


@strawberry.type
class ScheduledJobType:
    """A scheduled job."""
    id: UUID
    name: str
    description: Optional[str]
    job_type: str
    config: ScheduleConfigType
    status: str
    last_run: Optional[datetime]
    next_run: Optional[datetime]
    run_count: int
    error_count: int
    last_error: Optional[str]
    metadata: Optional[JSON]
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID]


@strawberry.type
class JobRunType:
    """A job run record."""
    id: UUID
    job_id: UUID
    job_name: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]
    error_message: Optional[str]
    output: Optional[JSON]


@strawberry.type
class SchedulerStatusType:
    """Scheduler status."""
    running: bool
    total_jobs: int
    pending_jobs: int
    running_jobs: int
    failed_jobs: int
    paused_jobs: int
    next_job_at: Optional[datetime]
    last_checked_at: Optional[datetime]


@strawberry.type
class JobSummaryType:
    """Summary of a job."""
    id: UUID
    name: str
    status: str
    schedule_type: str
    last_run: Optional[datetime]
    next_run: Optional[datetime]
    success_rate: float
    avg_duration_seconds: Optional[float]


@strawberry.input
class CreateJobInput:
    """Input for creating a scheduled job."""
    name: str
    description: Optional[str] = None
    job_type: str
    schedule_type: str = "interval"
    interval_minutes: int = 60
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    cron_expression: Optional[str] = None
    timezone: str = "UTC"
    max_retries: int = 3
    retry_delay_minutes: int = 5
    metadata: Optional[JSON] = None


@strawberry.input
class UpdateJobInput:
    """Input for updating a scheduled job."""
    name: Optional[str] = None
    description: Optional[str] = None
    schedule_type: Optional[str] = None
    interval_minutes: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    cron_expression: Optional[str] = None
    timezone: Optional[str] = None
    max_retries: Optional[int] = None
    retry_delay_minutes: Optional[int] = None
    metadata: Optional[JSON] = None


@strawberry.input
class JobFilterInput:
    """Input for filtering jobs."""
    name_contains: Optional[str] = None
    status: Optional[str] = None
    job_type: Optional[str] = None
    schedule_type: Optional[str] = None


@strawberry.type
class JobActionResultType:
    """Result of a job action."""
    success: bool
    job_id: UUID
    action: str
    message: Optional[str]
    new_status: Optional[str]
