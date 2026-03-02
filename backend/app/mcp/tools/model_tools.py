"""
Model Tools for MCP.

Provides tools for model training, inference, comparison, and promotion.
"""

import uuid
from typing import Any, Dict, List, Optional

import structlog

from app.mcp.core.auth import MCPTokenClaims
from app.mcp.core.exceptions import MCPError, MCPErrorCode
from app.mcp.formatters.insight_formatter import format_model_performance
from app.mcp.tools.base import (
    AsyncTool,
    BaseTool,
    ParameterType,
    ToolParameter,
    ToolResult,
)

logger = structlog.get_logger("mcp.tools.model")


class TrainModelTool(AsyncTool):
    """
    Start model training job.

    Queues a model training job with specified configuration.
    """

    name = "train_model"
    description = "Start training a new model version with specified configuration"
    required_scope = "models:train"

    parameters = [
        ToolParameter(
            name="model_id",
            param_type=ParameterType.STRING,
            description="ID of the model to train a new version for",
            required=True,
        ),
        ToolParameter(
            name="dataset_id",
            param_type=ParameterType.STRING,
            description="ID of the training dataset",
            required=True,
        ),
        ToolParameter(
            name="model_type",
            param_type=ParameterType.STRING,
            description="Type of model to train",
            required=False,
            default="pymc_mmm",
            enum=["pymc_mmm", "prophet", "neural", "ensemble", "lightweight_mmm"],
        ),
        ToolParameter(
            name="target_column",
            param_type=ParameterType.STRING,
            description="Target column for prediction",
            required=True,
        ),
        ToolParameter(
            name="feature_columns",
            param_type=ParameterType.ARRAY,
            description="Feature columns to use",
            required=False,
        ),
        ToolParameter(
            name="date_column",
            param_type=ParameterType.STRING,
            description="Date/time column for time series",
            required=False,
            default="date",
        ),
        ToolParameter(
            name="hyperparameters",
            param_type=ParameterType.OBJECT,
            description="Optional hyperparameters for training",
            required=False,
        ),
    ]

    async def start_job(
        self,
        arguments: Dict[str, Any],
        claims: Optional[MCPTokenClaims],
    ) -> str:
        """Start training job."""
        model_id = arguments["model_id"]
        dataset_id = arguments["dataset_id"]
        model_type = arguments.get("model_type", "pymc_mmm")
        target_column = arguments["target_column"]
        feature_columns = arguments.get("feature_columns", [])
        date_column = arguments.get("date_column", "date")
        hyperparameters = arguments.get("hyperparameters", {})

        self.logger.info(
            "Starting model training",
            model_id=model_id,
            dataset_id=dataset_id,
            model_type=model_type,
        )

        if not self.celery:
            # Return mock job ID
            return f"train-{uuid.uuid4().hex[:8]}"

        # Queue Celery task
        from app.workers.tasks.training import train_model

        task = train_model.delay(
            model_id=model_id,
            dataset_id=dataset_id,
            model_type=model_type,
            target_column=target_column,
            feature_columns=feature_columns,
            date_column=date_column,
            hyperparameters=hyperparameters,
            organization_id=claims.org_id if claims else None,
            user_id=claims.sub if claims else None,
        )

        return task.id


class GetTrainingStatusTool(BaseTool):
    """
    Check training job status.

    Returns the current status and progress of a training job.
    """

    name = "get_training_status"
    description = "Check the status of a model training job"
    required_scope = "models:read"

    parameters = [
        ToolParameter(
            name="job_id",
            param_type=ParameterType.STRING,
            description="ID of the training job to check",
            required=True,
        ),
    ]

    async def execute(
        self,
        arguments: Dict[str, Any],
        claims: Optional[MCPTokenClaims],
    ) -> ToolResult:
        """Get training status."""
        job_id = arguments["job_id"]

        self.logger.info("Checking training status", job_id=job_id)

        status = await self._get_status(job_id)

        return ToolResult(
            success=True,
            data=status,
        )

    async def _get_status(self, job_id: str) -> Dict[str, Any]:
        """Get job status from Celery or database."""
        if not self.celery:
            # Mock status for various states
            if job_id.startswith("train-"):
                return {
                    "job_id": job_id,
                    "status": "completed",
                    "progress": 100,
                    "message": "Training completed successfully",
                    "result": {
                        "model_version": "2.2.0",
                        "metrics": {
                            "mape": 0.082,
                            "r2": 0.93,
                            "training_time_seconds": 2400,
                        },
                    },
                    "completed_at": "2024-06-20T15:30:00Z",
                }

            return {
                "job_id": job_id,
                "status": "unknown",
                "message": "Job not found",
            }

        # Real Celery status check
        result = self.celery.AsyncResult(job_id)

        if result.ready():
            if result.successful():
                return {
                    "job_id": job_id,
                    "status": "completed",
                    "progress": 100,
                    "result": result.get(),
                }
            else:
                return {
                    "job_id": job_id,
                    "status": "failed",
                    "error": str(result.result),
                }
        else:
            info = result.info or {}
            return {
                "job_id": job_id,
                "status": "running",
                "progress": info.get("progress", 0),
                "message": info.get("message", "Training in progress"),
            }


class RunInferenceTool(BaseTool):
    """
    Generate predictions using a trained model.

    Runs inference to generate forecasts.
    """

    name = "run_inference"
    description = "Generate predictions using a trained model"
    required_scope = "forecast:create"

    parameters = [
        ToolParameter(
            name="model_id",
            param_type=ParameterType.STRING,
            description="ID of the model to use",
            required=True,
        ),
        ToolParameter(
            name="version",
            param_type=ParameterType.STRING,
            description="Model version (latest if not specified)",
            required=False,
        ),
        ToolParameter(
            name="horizon",
            param_type=ParameterType.INTEGER,
            description="Number of periods to forecast",
            required=False,
            default=12,
            minimum=1,
            maximum=52,
        ),
        ToolParameter(
            name="input_data",
            param_type=ParameterType.OBJECT,
            description="Input data for prediction (feature values)",
            required=False,
        ),
        ToolParameter(
            name="confidence_level",
            param_type=ParameterType.NUMBER,
            description="Confidence level for intervals",
            required=False,
            default=0.95,
            minimum=0.5,
            maximum=0.99,
        ),
    ]

    async def execute(
        self,
        arguments: Dict[str, Any],
        claims: Optional[MCPTokenClaims],
    ) -> ToolResult:
        """Run inference."""
        model_id = arguments["model_id"]
        version = arguments.get("version")
        horizon = arguments.get("horizon", 12)
        input_data = arguments.get("input_data", {})
        confidence_level = arguments.get("confidence_level", 0.95)

        self.logger.info(
            "Running inference",
            model_id=model_id,
            horizon=horizon,
        )

        predictions = await self._run_inference(
            model_id=model_id,
            version=version,
            horizon=horizon,
            input_data=input_data,
            confidence_level=confidence_level,
            org_id=claims.org_id if claims else None,
        )

        return ToolResult(
            success=True,
            data=predictions,
        )

    async def _run_inference(
        self,
        model_id: str,
        version: Optional[str],
        horizon: int,
        input_data: Dict[str, Any],
        confidence_level: float,
        org_id: Optional[str],
    ) -> Dict[str, Any]:
        """Run model inference."""
        if not self.db:
            # Mock predictions
            import random

            base_value = 15000
            predictions = []
            for i in range(horizon):
                value = base_value * (1 + random.uniform(-0.1, 0.15))
                predictions.append({
                    "period": i + 1,
                    "date": f"2024-{(7 + i) % 12 + 1:02d}-01",
                    "value": round(value, 2),
                    "lower": round(value * 0.85, 2),
                    "upper": round(value * 1.15, 2),
                })

            return {
                "model_id": model_id,
                "version": version or "2.1.0",
                "horizon": horizon,
                "confidence_level": confidence_level,
                "predictions": predictions,
                "summary": f"Generated {horizon}-period forecast with {confidence_level*100:.0f}% confidence intervals",
                "total_predicted": sum(p["value"] for p in predictions),
            }

        # Real inference implementation
        from app.services.forecast.forecast_service import ForecastService

        service = ForecastService()
        result = await service.run_inference(
            model_id=model_id,
            version=version,
            horizon=horizon,
            input_data=input_data,
            confidence_level=confidence_level,
        )

        return result


class CompareModelsTool(BaseTool):
    """
    Compare performance metrics across models.

    Provides side-by-side comparison of model performance.
    """

    name = "compare_models"
    description = "Compare performance metrics across multiple models"
    required_scope = "models:read"

    parameters = [
        ToolParameter(
            name="model_ids",
            param_type=ParameterType.ARRAY,
            description="List of model IDs to compare",
            required=True,
        ),
        ToolParameter(
            name="metrics",
            param_type=ParameterType.ARRAY,
            description="Metrics to compare",
            required=False,
        ),
    ]

    async def execute(
        self,
        arguments: Dict[str, Any],
        claims: Optional[MCPTokenClaims],
    ) -> ToolResult:
        """Compare models."""
        model_ids = arguments["model_ids"]
        metrics = arguments.get("metrics", ["mape", "r2", "rmse"])

        if len(model_ids) < 2:
            raise MCPError(
                code=MCPErrorCode.INVALID_PARAMS,
                message="At least 2 models required for comparison",
            )

        self.logger.info(
            "Comparing models",
            model_ids=model_ids,
        )

        comparison = await self._compare_models(
            model_ids=model_ids,
            metrics=metrics,
            org_id=claims.org_id if claims else None,
        )

        return ToolResult(
            success=True,
            data=comparison,
        )

    async def _compare_models(
        self,
        model_ids: List[str],
        metrics: List[str],
        org_id: Optional[str],
    ) -> Dict[str, Any]:
        """Compare multiple models."""
        if not self.db:
            # Mock comparison
            models = []
            for i, model_id in enumerate(model_ids):
                models.append({
                    "model_id": model_id,
                    "name": f"Model {i + 1}",
                    "version": f"1.{i}.0",
                    "metrics": {
                        "mape": 0.08 + i * 0.02,
                        "r2": 0.92 - i * 0.03,
                        "rmse": 1000 + i * 200,
                    },
                })

            # Determine winner
            winner = min(models, key=lambda m: m["metrics"]["mape"])

            return {
                "models": models,
                "metrics_compared": metrics,
                "recommendation": {
                    "best_model": winner["model_id"],
                    "reason": f"Lowest MAPE ({winner['metrics']['mape']*100:.1f}%)",
                },
                "summary": f"Compared {len(models)} models. {winner['name']} performs best with {winner['metrics']['mape']*100:.1f}% MAPE.",
            }

        # Real comparison implementation
        return {"models": [], "metrics_compared": metrics}


class PromoteModelTool(BaseTool):
    """
    Promote model to different stage.

    Changes model stage (development -> staging -> production).
    """

    name = "promote_model"
    description = "Promote a model to a different stage (development → staging → production)"
    required_scope = "models:deploy"

    parameters = [
        ToolParameter(
            name="model_id",
            param_type=ParameterType.STRING,
            description="ID of the model to promote",
            required=True,
        ),
        ToolParameter(
            name="version",
            param_type=ParameterType.STRING,
            description="Version to promote",
            required=True,
        ),
        ToolParameter(
            name="target_stage",
            param_type=ParameterType.STRING,
            description="Target stage",
            required=True,
            enum=["staging", "production", "archived"],
        ),
        ToolParameter(
            name="reason",
            param_type=ParameterType.STRING,
            description="Reason for promotion",
            required=False,
        ),
    ]

    async def execute(
        self,
        arguments: Dict[str, Any],
        claims: Optional[MCPTokenClaims],
    ) -> ToolResult:
        """Promote model."""
        model_id = arguments["model_id"]
        version = arguments["version"]
        target_stage = arguments["target_stage"]
        reason = arguments.get("reason", "Promoted via MCP")

        self.logger.info(
            "Promoting model",
            model_id=model_id,
            version=version,
            target_stage=target_stage,
        )

        result = await self._promote_model(
            model_id=model_id,
            version=version,
            target_stage=target_stage,
            reason=reason,
            org_id=claims.org_id if claims else None,
            user_id=claims.sub if claims else None,
        )

        return ToolResult(
            success=True,
            data=result,
        )

    async def _promote_model(
        self,
        model_id: str,
        version: str,
        target_stage: str,
        reason: str,
        org_id: Optional[str],
        user_id: Optional[str],
    ) -> Dict[str, Any]:
        """Promote model to target stage."""
        if not self.db:
            # Mock promotion
            return {
                "model_id": model_id,
                "version": version,
                "previous_stage": "staging",
                "new_stage": target_stage,
                "promoted_at": "2024-06-20T16:00:00Z",
                "promoted_by": user_id,
                "reason": reason,
                "message": f"Model {model_id} version {version} promoted to {target_stage}",
            }

        # Real implementation
        from app.services.model_registry.registry import ModelRegistry

        registry = ModelRegistry(db=self.db)
        result = await registry.promote_version(
            model_id=model_id,
            version=version,
            target_stage=target_stage,
            reason=reason,
            user_id=user_id,
        )

        return result
