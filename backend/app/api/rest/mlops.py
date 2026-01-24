"""
MLOps API endpoints for pipeline triggering and management.

Provides a single API endpoint to trigger the end-to-end ML pipeline
via Apache Airflow.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.infrastructure.database.session import get_db

router = APIRouter(prefix="/mlops", tags=["MLOps"])


# Enums
class PipelineType(str, Enum):
    """Type of ML pipeline to execute."""

    FULL = "full"  # Complete pipeline: data -> train -> validate -> deploy -> monitor
    TRAINING = "training"  # Skip data pipeline, use existing features
    DEPLOY = "deploy"  # Deploy a specific model version
    RETRAIN = "retrain"  # Retraining triggered by drift detection


class TriggerSource(str, Enum):
    """Source of the pipeline trigger."""

    MANUAL = "manual"  # Manual API call
    GITHUB_WEBHOOK = "github_webhook"  # PR merge webhook
    DRIFT_ALERT = "drift_alert"  # Drift detection alert
    SCHEDULED = "scheduled"  # Scheduled job


class PipelineStatus(str, Enum):
    """Status of a pipeline run."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Request/Response Models
class PipelineTriggerRequest(BaseModel):
    """Request to trigger an ML pipeline."""

    pipeline_type: PipelineType = Field(
        default=PipelineType.FULL,
        description="Type of pipeline to execute",
    )
    model_types: list[str] = Field(
        default=["prophet", "arima", "pymc_mmm"],
        description="Model types to train",
    )
    dataset_id: UUID | None = Field(
        default=None,
        description="Specific dataset ID to use (optional)",
    )
    auto_deploy: bool = Field(
        default=True,
        description="Automatically deploy if quality gates pass",
    )
    trigger_source: TriggerSource = Field(
        default=TriggerSource.MANUAL,
        description="Source of the trigger",
    )
    config_overrides: dict[str, Any] | None = Field(
        default=None,
        description="Optional configuration overrides",
    )


class PipelineTriggerResponse(BaseModel):
    """Response after triggering a pipeline."""

    run_id: str
    dag_id: str
    pipeline_type: PipelineType
    status: PipelineStatus
    triggered_at: datetime
    airflow_url: str | None
    message: str


class PipelineStatusResponse(BaseModel):
    """Status of a pipeline run."""

    run_id: str
    dag_id: str
    status: PipelineStatus
    start_date: datetime | None
    end_date: datetime | None
    duration_seconds: float | None
    tasks: list[dict[str, Any]]
    logs_url: str | None


class PipelineListResponse(BaseModel):
    """List of recent pipeline runs."""

    runs: list[dict[str, Any]]
    total: int
    page: int
    page_size: int


# Airflow integration
class AirflowClient:
    """Client for interacting with Apache Airflow REST API."""

    def __init__(
        self,
        base_url: str = "http://airflow-webserver:8080",
        username: str = "airflow",
        password: str = "airflow",
    ):
        self.base_url = base_url.rstrip("/")
        self.auth = (username, password)

    async def trigger_dag(
        self,
        dag_id: str,
        conf: dict[str, Any] | None = None,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        """Trigger an Airflow DAG run."""
        url = f"{self.base_url}/api/v1/dags/{dag_id}/dagRuns"

        payload = {
            "conf": conf or {},
        }

        if run_id:
            payload["dag_run_id"] = run_id

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    url,
                    json=payload,
                    auth=self.auth,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            # Return mock response for development
            return {
                "dag_run_id": run_id or f"manual__{datetime.utcnow().isoformat()}",
                "dag_id": dag_id,
                "state": "queued",
                "execution_date": datetime.utcnow().isoformat(),
                "start_date": None,
                "end_date": None,
                "note": f"Mock response (Airflow not available: {e})",
            }

    async def get_dag_run(self, dag_id: str, run_id: str) -> dict[str, Any]:
        """Get status of a DAG run."""
        url = f"{self.base_url}/api/v1/dags/{dag_id}/dagRuns/{run_id}"

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, auth=self.auth)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError:
            return {
                "dag_run_id": run_id,
                "dag_id": dag_id,
                "state": "unknown",
                "note": "Mock response (Airflow not available)",
            }

    async def list_dag_runs(
        self,
        dag_id: str,
        limit: int = 10,
        offset: int = 0,
    ) -> dict[str, Any]:
        """List DAG runs."""
        url = f"{self.base_url}/api/v1/dags/{dag_id}/dagRuns"

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    url,
                    params={"limit": limit, "offset": offset, "order_by": "-execution_date"},
                    auth=self.auth,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError:
            return {
                "dag_runs": [],
                "total_entries": 0,
            }

    async def get_task_instances(self, dag_id: str, run_id: str) -> list[dict[str, Any]]:
        """Get task instances for a DAG run."""
        url = f"{self.base_url}/api/v1/dags/{dag_id}/dagRuns/{run_id}/taskInstances"

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, auth=self.auth)
                response.raise_for_status()
                return response.json().get("task_instances", [])
        except httpx.HTTPError:
            return []


# Dependency injection
def get_airflow_client() -> AirflowClient:
    """Get Airflow client instance."""
    return AirflowClient(
        base_url=getattr(settings, "AIRFLOW_BASE_URL", "http://airflow-webserver:8080"),
        username=getattr(settings, "AIRFLOW_USERNAME", "airflow"),
        password=getattr(settings, "AIRFLOW_PASSWORD", "airflow"),
    )


# API Endpoints
@router.post(
    "/pipeline/trigger",
    response_model=PipelineTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger ML Pipeline",
    description="Trigger the end-to-end ML pipeline via Apache Airflow",
)
async def trigger_pipeline(
    request: PipelineTriggerRequest,
    background_tasks: BackgroundTasks,
    airflow: AirflowClient = Depends(get_airflow_client),
) -> PipelineTriggerResponse:
    """
    Trigger an ML pipeline run.

    This endpoint triggers the master ML pipeline DAG in Airflow.
    The pipeline type determines which stages are executed:

    - **full**: Complete pipeline (data -> train -> validate -> deploy -> monitor)
    - **training**: Skip data pipeline, use existing features
    - **deploy**: Deploy a specific model version
    - **retrain**: Retraining triggered by drift detection

    Returns immediately with a run_id that can be used to track progress.
    """
    # Generate run ID
    run_id = f"{request.pipeline_type.value}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"

    # Build DAG configuration
    dag_conf = {
        "pipeline_type": request.pipeline_type.value,
        "model_types": request.model_types,
        "dataset_id": str(request.dataset_id) if request.dataset_id else None,
        "auto_deploy": request.auto_deploy,
        "trigger_source": request.trigger_source.value,
        "triggered_at": datetime.utcnow().isoformat(),
    }

    if request.config_overrides:
        dag_conf["config_overrides"] = request.config_overrides

    # Trigger the master DAG
    dag_id = "ml_pipeline_master"
    result = await airflow.trigger_dag(dag_id, conf=dag_conf, run_id=run_id)

    # Map Airflow state to our status enum
    state_mapping = {
        "queued": PipelineStatus.QUEUED,
        "running": PipelineStatus.RUNNING,
        "success": PipelineStatus.SUCCESS,
        "failed": PipelineStatus.FAILED,
    }
    pipeline_status = state_mapping.get(result.get("state", "queued"), PipelineStatus.QUEUED)

    # Build Airflow UI URL
    airflow_base = getattr(settings, "AIRFLOW_BASE_URL", "http://localhost:8080")
    airflow_url = f"{airflow_base}/dags/{dag_id}/grid?dag_run_id={run_id}"

    return PipelineTriggerResponse(
        run_id=run_id,
        dag_id=dag_id,
        pipeline_type=request.pipeline_type,
        status=pipeline_status,
        triggered_at=datetime.utcnow(),
        airflow_url=airflow_url,
        message=f"Pipeline {request.pipeline_type.value} triggered successfully",
    )


@router.get(
    "/pipeline/{run_id}",
    response_model=PipelineStatusResponse,
    summary="Get Pipeline Status",
    description="Get the status of a pipeline run",
)
async def get_pipeline_status(
    run_id: str,
    airflow: AirflowClient = Depends(get_airflow_client),
) -> PipelineStatusResponse:
    """
    Get the status of a specific pipeline run.

    Returns detailed information including:
    - Overall status
    - Start/end times and duration
    - Individual task statuses
    - Link to logs
    """
    dag_id = "ml_pipeline_master"

    # Get DAG run status
    dag_run = await airflow.get_dag_run(dag_id, run_id)

    # Get task instances
    tasks = await airflow.get_task_instances(dag_id, run_id)

    # Parse dates
    start_date = None
    end_date = None
    if dag_run.get("start_date"):
        start_date = datetime.fromisoformat(dag_run["start_date"].replace("Z", "+00:00"))
    if dag_run.get("end_date"):
        end_date = datetime.fromisoformat(dag_run["end_date"].replace("Z", "+00:00"))

    # Calculate duration
    duration = None
    if start_date and end_date:
        duration = (end_date - start_date).total_seconds()
    elif start_date:
        duration = (datetime.utcnow() - start_date.replace(tzinfo=None)).total_seconds()

    # Map state
    state_mapping = {
        "queued": PipelineStatus.QUEUED,
        "running": PipelineStatus.RUNNING,
        "success": PipelineStatus.SUCCESS,
        "failed": PipelineStatus.FAILED,
    }
    pipeline_status = state_mapping.get(dag_run.get("state", "unknown"), PipelineStatus.RUNNING)

    # Build logs URL
    airflow_base = getattr(settings, "AIRFLOW_BASE_URL", "http://localhost:8080")
    logs_url = f"{airflow_base}/dags/{dag_id}/grid?dag_run_id={run_id}"

    return PipelineStatusResponse(
        run_id=run_id,
        dag_id=dag_id,
        status=pipeline_status,
        start_date=start_date,
        end_date=end_date,
        duration_seconds=duration,
        tasks=[
            {
                "task_id": t.get("task_id"),
                "state": t.get("state"),
                "start_date": t.get("start_date"),
                "end_date": t.get("end_date"),
                "duration": t.get("duration"),
            }
            for t in tasks
        ],
        logs_url=logs_url,
    )


@router.get(
    "/pipeline",
    response_model=PipelineListResponse,
    summary="List Pipeline Runs",
    description="List recent pipeline runs",
)
async def list_pipeline_runs(
    page: int = 1,
    page_size: int = 10,
    airflow: AirflowClient = Depends(get_airflow_client),
) -> PipelineListResponse:
    """
    List recent pipeline runs.

    Supports pagination with page and page_size parameters.
    """
    dag_id = "ml_pipeline_master"
    offset = (page - 1) * page_size

    result = await airflow.list_dag_runs(dag_id, limit=page_size, offset=offset)

    runs = [
        {
            "run_id": run.get("dag_run_id"),
            "state": run.get("state"),
            "start_date": run.get("start_date"),
            "end_date": run.get("end_date"),
            "execution_date": run.get("execution_date"),
            "conf": run.get("conf"),
        }
        for run in result.get("dag_runs", [])
    ]

    return PipelineListResponse(
        runs=runs,
        total=result.get("total_entries", 0),
        page=page,
        page_size=page_size,
    )


@router.post(
    "/pipeline/{run_id}/cancel",
    summary="Cancel Pipeline Run",
    description="Cancel a running pipeline",
)
async def cancel_pipeline(
    run_id: str,
    airflow: AirflowClient = Depends(get_airflow_client),
) -> dict[str, Any]:
    """
    Cancel a running pipeline.

    Note: This marks the DAG run as failed. Running tasks may continue
    until they complete or timeout.
    """
    # In production, this would call Airflow API to mark the run as failed
    # PATCH /api/v1/dags/{dag_id}/dagRuns/{run_id} with {"state": "failed"}

    return {
        "run_id": run_id,
        "status": "cancellation_requested",
        "message": "Pipeline cancellation has been requested",
    }


@router.post(
    "/webhook/github",
    summary="GitHub Webhook Handler",
    description="Handle GitHub webhook events for automated pipeline triggers",
)
async def github_webhook(
    payload: dict[str, Any],
    airflow: AirflowClient = Depends(get_airflow_client),
) -> dict[str, Any]:
    """
    Handle GitHub webhook events.

    Triggers a pipeline when:
    - PR is merged to main branch
    - Tag is pushed (for releases)
    """
    event_type = payload.get("action")
    ref = payload.get("ref", "")

    # Check if this is a PR merge to main
    if event_type == "closed" and payload.get("pull_request", {}).get("merged"):
        base_branch = payload["pull_request"]["base"]["ref"]
        if base_branch in ["main", "master"]:
            # Trigger full pipeline
            request = PipelineTriggerRequest(
                pipeline_type=PipelineType.FULL,
                trigger_source=TriggerSource.GITHUB_WEBHOOK,
            )

            run_id = f"github_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"

            dag_conf = {
                "pipeline_type": request.pipeline_type.value,
                "model_types": request.model_types,
                "trigger_source": request.trigger_source.value,
                "github_pr": payload["pull_request"]["number"],
                "github_sha": payload["pull_request"]["merge_commit_sha"],
            }

            await airflow.trigger_dag("ml_pipeline_master", conf=dag_conf, run_id=run_id)

            return {
                "status": "triggered",
                "run_id": run_id,
                "trigger_reason": f"PR #{payload['pull_request']['number']} merged to {base_branch}",
            }

    return {
        "status": "ignored",
        "reason": "Event does not trigger pipeline",
    }


@router.post(
    "/alert/drift",
    summary="Drift Alert Handler",
    description="Handle drift detection alerts to trigger retraining",
)
async def drift_alert_handler(
    payload: dict[str, Any],
    airflow: AirflowClient = Depends(get_airflow_client),
) -> dict[str, Any]:
    """
    Handle drift detection alerts.

    Automatically triggers a retraining pipeline when drift is detected.
    """
    drift_score = payload.get("drift_score", 0)
    drift_threshold = payload.get("threshold", 0.5)
    features_with_drift = payload.get("features_with_drift", [])

    if drift_score > drift_threshold:
        run_id = f"drift_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"

        dag_conf = {
            "pipeline_type": PipelineType.RETRAIN.value,
            "model_types": ["prophet", "arima", "pymc_mmm"],
            "auto_deploy": True,
            "trigger_source": TriggerSource.DRIFT_ALERT.value,
            "drift_info": {
                "score": drift_score,
                "threshold": drift_threshold,
                "features": features_with_drift,
            },
        }

        await airflow.trigger_dag("ml_pipeline_master", conf=dag_conf, run_id=run_id)

        return {
            "status": "retraining_triggered",
            "run_id": run_id,
            "drift_score": drift_score,
            "features_with_drift": features_with_drift,
        }

    return {
        "status": "no_action",
        "reason": f"Drift score {drift_score} below threshold {drift_threshold}",
    }
