"""
ETL Pipeline

Extract, Transform, Load pipeline implementation.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from enum import Enum
import uuid
import logging
import pandas as pd

logger = logging.getLogger(__name__)


class StepType(str, Enum):
    """Pipeline step types."""
    EXTRACT = "extract"
    TRANSFORM = "transform"
    LOAD = "load"
    VALIDATE = "validate"


class StepStatus(str, Enum):
    """Step execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PipelineStep:
    """A single pipeline step."""
    name: str
    step_type: StepType
    function: Callable
    config: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    retry_count: int = 3
    timeout_seconds: int = 300


@dataclass
class StepResult:
    """Result of a pipeline step."""
    step_name: str
    status: StepStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    output_rows: int = 0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineConfig:
    """Pipeline configuration."""
    name: str = "default_pipeline"
    parallel_steps: bool = False
    stop_on_error: bool = True
    log_level: str = "INFO"


class ETLPipeline:
    """
    ETL Pipeline Framework.

    Features:
    - Step-based execution
    - Dependency management
    - Error handling
    - Progress tracking

    Example:
        pipeline = ETLPipeline()

        pipeline.add_step(PipelineStep(
            name="extract",
            step_type=StepType.EXTRACT,
            function=extract_data,
        ))

        pipeline.add_step(PipelineStep(
            name="transform",
            step_type=StepType.TRANSFORM,
            function=transform_data,
            depends_on=["extract"],
        ))

        result = pipeline.run()
    """

    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()
        self._steps: Dict[str, PipelineStep] = {}
        self._results: Dict[str, StepResult] = {}
        self._data: Dict[str, Any] = {}
        self._run_id: Optional[str] = None

    def add_step(self, step: PipelineStep) -> None:
        """Add a step to the pipeline."""
        self._steps[step.name] = step

    def run(self, initial_data: Optional[Dict[str, Any]] = None) -> Dict[str, StepResult]:
        """
        Run the pipeline.

        Args:
            initial_data: Initial data to pass to first step

        Returns:
            Dict mapping step names to results
        """
        self._run_id = str(uuid.uuid4())
        self._data = initial_data or {}
        self._results = {}

        # Get execution order
        execution_order = self._get_execution_order()

        for step_name in execution_order:
            step = self._steps[step_name]

            # Check dependencies
            if not self._check_dependencies(step):
                self._results[step_name] = StepResult(
                    step_name=step_name,
                    status=StepStatus.SKIPPED,
                    start_time=datetime.utcnow(),
                    end_time=datetime.utcnow(),
                    error_message="Dependencies not met",
                )
                continue

            # Execute step
            result = self._execute_step(step)
            self._results[step_name] = result

            # Stop on error if configured
            if result.status == StepStatus.FAILED and self.config.stop_on_error:
                logger.error(f"Pipeline stopped due to error in step: {step_name}")
                break

        return self._results

    def _get_execution_order(self) -> List[str]:
        """Get topologically sorted execution order."""
        visited = set()
        order = []

        def visit(name):
            if name in visited:
                return
            visited.add(name)
            step = self._steps.get(name)
            if step:
                for dep in step.depends_on:
                    visit(dep)
            order.append(name)

        for name in self._steps:
            visit(name)

        return order

    def _check_dependencies(self, step: PipelineStep) -> bool:
        """Check if all dependencies are completed."""
        for dep in step.depends_on:
            result = self._results.get(dep)
            if not result or result.status != StepStatus.COMPLETED:
                return False
        return True

    def _execute_step(self, step: PipelineStep) -> StepResult:
        """Execute a single step."""
        start_time = datetime.utcnow()

        for attempt in range(step.retry_count):
            try:
                logger.info(f"Executing step: {step.name} (attempt {attempt + 1})")

                # Run the step function
                output = step.function(self._data, step.config)

                # Store output
                if output is not None:
                    self._data[step.name] = output

                output_rows = 0
                if isinstance(output, pd.DataFrame):
                    output_rows = len(output)

                return StepResult(
                    step_name=step.name,
                    status=StepStatus.COMPLETED,
                    start_time=start_time,
                    end_time=datetime.utcnow(),
                    output_rows=output_rows,
                )

            except Exception as e:
                logger.warning(f"Step {step.name} failed (attempt {attempt + 1}): {e}")
                if attempt == step.retry_count - 1:
                    return StepResult(
                        step_name=step.name,
                        status=StepStatus.FAILED,
                        start_time=start_time,
                        end_time=datetime.utcnow(),
                        error_message=str(e),
                    )

        return StepResult(
            step_name=step.name,
            status=StepStatus.FAILED,
            start_time=start_time,
            end_time=datetime.utcnow(),
            error_message="Max retries exceeded",
        )

    def get_data(self, key: str) -> Any:
        """Get data from pipeline context."""
        return self._data.get(key)

    def get_results(self) -> Dict[str, StepResult]:
        """Get all step results."""
        return self._results.copy()

    def get_status(self) -> Dict[str, str]:
        """Get status of all steps."""
        return {name: result.status.value for name, result in self._results.items()}
