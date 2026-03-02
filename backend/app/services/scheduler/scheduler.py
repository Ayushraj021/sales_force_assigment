"""
Job Scheduler

Task scheduling and automation.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
import uuid
import threading
import time
import logging

logger = logging.getLogger(__name__)


class ScheduleType(str, Enum):
    """Schedule types."""
    ONCE = "once"
    INTERVAL = "interval"
    CRON = "cron"
    DAILY = "daily"
    WEEKLY = "weekly"


class JobStatus(str, Enum):
    """Job status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


@dataclass
class ScheduleConfig:
    """Schedule configuration."""
    schedule_type: ScheduleType = ScheduleType.INTERVAL
    interval_minutes: int = 60
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    cron_expression: Optional[str] = None  # e.g., "0 0 * * *"
    timezone: str = "UTC"
    max_retries: int = 3
    retry_delay_minutes: int = 5


@dataclass
class ScheduledJob:
    """A scheduled job."""
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    function: Optional[Callable] = None
    config: ScheduleConfig = field(default_factory=ScheduleConfig)
    status: JobStatus = JobStatus.PENDING
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "name": self.name,
            "status": self.status.value,
            "schedule_type": self.config.schedule_type.value,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "run_count": self.run_count,
            "error_count": self.error_count,
            "last_error": self.last_error,
        }


class JobScheduler:
    """
    Job Scheduling Service.

    Features:
    - Multiple schedule types
    - Job management
    - Error handling
    - Background execution

    Example:
        scheduler = JobScheduler()

        # Schedule a job
        job = scheduler.schedule(
            name="daily_forecast",
            function=run_forecast,
            config=ScheduleConfig(
                schedule_type=ScheduleType.DAILY,
                start_time=datetime.now()
            )
        )

        # Start scheduler
        scheduler.start()
    """

    def __init__(self):
        self._jobs: Dict[str, ScheduledJob] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def schedule(
        self,
        name: str,
        function: Callable,
        config: Optional[ScheduleConfig] = None,
        **metadata,
    ) -> ScheduledJob:
        """
        Schedule a new job.

        Args:
            name: Job name
            function: Function to execute
            config: Schedule configuration
            **metadata: Additional metadata

        Returns:
            ScheduledJob
        """
        config = config or ScheduleConfig()

        job = ScheduledJob(
            name=name,
            function=function,
            config=config,
            metadata=metadata,
        )

        job.next_run = self._calculate_next_run(config)

        with self._lock:
            self._jobs[job.job_id] = job

        logger.info(f"Scheduled job: {name} (next run: {job.next_run})")
        return job

    def _calculate_next_run(
        self,
        config: ScheduleConfig,
        from_time: Optional[datetime] = None,
    ) -> datetime:
        """Calculate next run time."""
        now = from_time or datetime.utcnow()

        if config.start_time and config.start_time > now:
            return config.start_time

        if config.schedule_type == ScheduleType.ONCE:
            return config.start_time or now

        elif config.schedule_type == ScheduleType.INTERVAL:
            return now + timedelta(minutes=config.interval_minutes)

        elif config.schedule_type == ScheduleType.DAILY:
            next_run = now.replace(hour=0, minute=0, second=0, microsecond=0)
            next_run += timedelta(days=1)
            return next_run

        elif config.schedule_type == ScheduleType.WEEKLY:
            days_until_monday = (7 - now.weekday()) % 7 or 7
            next_run = now.replace(hour=0, minute=0, second=0, microsecond=0)
            next_run += timedelta(days=days_until_monday)
            return next_run

        elif config.schedule_type == ScheduleType.CRON and config.cron_expression:
            # Simplified cron parsing (just interval for now)
            return now + timedelta(minutes=60)

        return now + timedelta(minutes=config.interval_minutes)

    def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("Scheduler started")

    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Scheduler stopped")

    def _run_loop(self) -> None:
        """Main scheduler loop."""
        while self._running:
            now = datetime.utcnow()

            with self._lock:
                jobs_to_run = [
                    job for job in self._jobs.values()
                    if (job.status == JobStatus.PENDING and
                        job.next_run and
                        job.next_run <= now)
                ]

            for job in jobs_to_run:
                self._execute_job(job)

            time.sleep(10)  # Check every 10 seconds

    def _execute_job(self, job: ScheduledJob) -> None:
        """Execute a single job."""
        job.status = JobStatus.RUNNING
        job.last_run = datetime.utcnow()

        try:
            logger.info(f"Executing job: {job.name}")

            if job.function:
                job.function()

            job.status = JobStatus.COMPLETED
            job.run_count += 1

            # Schedule next run
            if job.config.schedule_type != ScheduleType.ONCE:
                job.next_run = self._calculate_next_run(job.config, job.last_run)
                job.status = JobStatus.PENDING
            else:
                job.next_run = None

            logger.info(f"Job completed: {job.name}")

        except Exception as e:
            logger.error(f"Job failed: {job.name} - {e}")
            job.status = JobStatus.FAILED
            job.error_count += 1
            job.last_error = str(e)

            # Retry logic
            if job.error_count <= job.config.max_retries:
                job.next_run = datetime.utcnow() + timedelta(
                    minutes=job.config.retry_delay_minutes
                )
                job.status = JobStatus.PENDING

    def run_now(self, job_id: str) -> bool:
        """Run a job immediately."""
        job = self._jobs.get(job_id)
        if job:
            self._execute_job(job)
            return True
        return False

    def pause_job(self, job_id: str) -> bool:
        """Pause a job."""
        job = self._jobs.get(job_id)
        if job:
            job.status = JobStatus.PAUSED
            return True
        return False

    def resume_job(self, job_id: str) -> bool:
        """Resume a paused job."""
        job = self._jobs.get(job_id)
        if job and job.status == JobStatus.PAUSED:
            job.status = JobStatus.PENDING
            job.next_run = self._calculate_next_run(job.config)
            return True
        return False

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job."""
        job = self._jobs.get(job_id)
        if job:
            job.status = JobStatus.CANCELLED
            job.next_run = None
            return True
        return False

    def delete_job(self, job_id: str) -> bool:
        """Delete a job."""
        with self._lock:
            if job_id in self._jobs:
                del self._jobs[job_id]
                return True
        return False

    def get_job(self, job_id: str) -> Optional[ScheduledJob]:
        """Get a job by ID."""
        return self._jobs.get(job_id)

    def list_jobs(
        self,
        status: Optional[JobStatus] = None,
    ) -> List[ScheduledJob]:
        """List all jobs."""
        jobs = list(self._jobs.values())
        if status:
            jobs = [j for j in jobs if j.status == status]
        return jobs

    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        jobs = list(self._jobs.values())
        return {
            "running": self._running,
            "total_jobs": len(jobs),
            "pending": len([j for j in jobs if j.status == JobStatus.PENDING]),
            "running_jobs": len([j for j in jobs if j.status == JobStatus.RUNNING]),
            "failed": len([j for j in jobs if j.status == JobStatus.FAILED]),
            "paused": len([j for j in jobs if j.status == JobStatus.PAUSED]),
        }
