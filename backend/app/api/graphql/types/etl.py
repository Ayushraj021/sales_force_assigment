"""ETL Pipeline GraphQL types."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

import strawberry
from strawberry.scalars import JSON


@strawberry.enum
class StepTypeEnum(Enum):
    """Pipeline step types."""
    EXTRACT = "extract"
    TRANSFORM = "transform"
    LOAD = "load"
    VALIDATE = "validate"


@strawberry.enum
class StepStatusEnum(Enum):
    """Step execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@strawberry.type
class PipelineStepType:
    """A single pipeline step."""
    id: UUID
    name: str
    step_type: str
    config: Optional[JSON]
    depends_on: list[str]
    retry_count: int
    timeout_seconds: int
    pipeline_id: UUID
    order_index: int


@strawberry.type
class StepResultType:
    """Result of a pipeline step."""
    id: UUID
    step_name: str
    status: str
    start_time: datetime
    end_time: Optional[datetime]
    output_rows: int
    error_message: Optional[str]
    metadata: Optional[JSON]
    run_id: UUID


@strawberry.type
class PipelineConfigType:
    """Pipeline configuration."""
    id: UUID
    name: str
    description: Optional[str]
    parallel_steps: bool
    stop_on_error: bool
    log_level: str
    organization_id: UUID
    created_by: UUID
    created_at: datetime
    updated_at: datetime


@strawberry.type
class PipelineRunType:
    """A pipeline run."""
    id: UUID
    pipeline_id: UUID
    pipeline_name: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    step_results: list[StepResultType]
    total_steps: int
    completed_steps: int
    failed_steps: int
    error_message: Optional[str]
    triggered_by: Optional[str]


@strawberry.type
class PipelineType:
    """Complete pipeline with steps."""
    id: UUID
    name: str
    description: Optional[str]
    config: PipelineConfigType
    steps: list[PipelineStepType]
    last_run: Optional[PipelineRunType]
    run_count: int
    success_count: int
    failure_count: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


@strawberry.type
class PipelineSummaryType:
    """Summary of pipeline."""
    id: UUID
    name: str
    status: str
    step_count: int
    last_run_at: Optional[datetime]
    last_run_status: Optional[str]
    next_run_at: Optional[datetime]
    is_active: bool


@strawberry.input
class CreatePipelineInput:
    """Input for creating a pipeline."""
    name: str
    description: Optional[str] = None
    parallel_steps: bool = False
    stop_on_error: bool = True
    log_level: str = "INFO"


@strawberry.input
class UpdatePipelineInput:
    """Input for updating a pipeline."""
    name: Optional[str] = None
    description: Optional[str] = None
    parallel_steps: Optional[bool] = None
    stop_on_error: Optional[bool] = None
    log_level: Optional[str] = None
    is_active: Optional[bool] = None


@strawberry.input
class CreatePipelineStepInput:
    """Input for creating a pipeline step."""
    pipeline_id: UUID
    name: str
    step_type: str
    config: Optional[JSON] = None
    depends_on: Optional[list[str]] = None
    retry_count: int = 3
    timeout_seconds: int = 300
    order_index: int = 0


@strawberry.input
class UpdatePipelineStepInput:
    """Input for updating a pipeline step."""
    name: Optional[str] = None
    step_type: Optional[str] = None
    config: Optional[JSON] = None
    depends_on: Optional[list[str]] = None
    retry_count: Optional[int] = None
    timeout_seconds: Optional[int] = None
    order_index: Optional[int] = None


@strawberry.input
class PipelineFilterInput:
    """Input for filtering pipelines."""
    name_contains: Optional[str] = None
    is_active: Optional[bool] = None


@strawberry.input
class RunPipelineInput:
    """Input for running a pipeline."""
    pipeline_id: UUID
    initial_data: Optional[JSON] = None
