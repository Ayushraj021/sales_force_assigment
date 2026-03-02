"""Model inference mutations."""

from typing import Optional
from uuid import UUID

import pandas as pd
import strawberry
import structlog
from sqlalchemy import select
from strawberry.scalars import JSON
from strawberry.types import Info

from app.api.graphql.context import get_db_session, get_current_user_from_context
from app.core.exceptions import NotFoundError, ValidationError
from app.infrastructure.database.models.model import Model, ModelVersion
from app.infrastructure.database.models.forecast import Forecast
from app.infrastructure.database.models.dataset import Dataset
from app.services.forecast.forecast_service import (
    ForecastService,
    ForecastConfig,
    ModelType,
)

logger = structlog.get_logger()


@strawberry.type
class PredictionResult:
    """Model prediction result."""

    model_id: UUID
    model_version: str
    predictions: JSON
    contribution_by_channel: Optional[JSON]
    confidence_intervals: Optional[JSON]


@strawberry.type
class DecompositionResult:
    """Channel contribution decomposition result."""

    model_id: UUID
    model_version: str
    total_contribution: float
    baseline_contribution: float
    channel_contributions: JSON
    time_series_decomposition: Optional[JSON]


@strawberry.input
class PredictInput:
    """Input for model prediction."""

    model_id: UUID
    input_data: JSON
    include_contributions: bool = True
    include_confidence_intervals: bool = True


@strawberry.input
class DecomposeInput:
    """Input for contribution decomposition."""

    model_id: UUID
    start_date: Optional[str] = None
    end_date: Optional[str] = None


@strawberry.type
class InferenceMutation:
    """Model inference mutations."""

    @strawberry.mutation
    async def predict(
        self,
        info: Info,
        input: PredictInput,
    ) -> PredictionResult:
        """Run prediction using a trained model."""
        db = await get_db_session(info)
        user = await get_current_user_from_context(info, db)

        # Get model
        result = await db.execute(
            select(Model).where(Model.id == input.model_id)
        )
        model = result.scalar_one_or_none()

        if not model:
            raise NotFoundError("Model", str(input.model_id))

        if model.status != "trained":
            raise ValidationError(f"Model is not trained. Current status: {model.status}")

        # Get current version
        result = await db.execute(
            select(ModelVersion)
            .where(ModelVersion.model_id == model.id)
            .where(ModelVersion.is_current == True)
        )
        version = result.scalar_one_or_none()

        if not version:
            raise ValidationError("No trained model version found")

        logger.info(
            "Running prediction",
            model_id=str(model.id),
            model_type=model.model_type,
            user_id=str(user.id),
        )

        # Check for existing completed forecast
        existing_forecast = await db.execute(
            select(Forecast).where(
                Forecast.model_id == model.id,
                Forecast.status == "completed",
                Forecast.is_active == True,
            ).order_by(Forecast.created_at.desc())
        )
        completed_forecast = existing_forecast.scalar_one_or_none()

        predictions = {}
        contribution_by_channel = None
        confidence_intervals = None

        if completed_forecast and completed_forecast.predicted_values:
            # Return stored forecast data
            predictions = {
                "predicted_values": completed_forecast.predicted_values,
                "dates": completed_forecast.forecast_dates or [],
            }

            if input.include_confidence_intervals and (completed_forecast.lower_bounds or completed_forecast.upper_bounds):
                confidence_intervals = {
                    "lower": completed_forecast.lower_bounds or [],
                    "upper": completed_forecast.upper_bounds or [],
                }

            logger.info(
                "Returning existing forecast",
                forecast_id=str(completed_forecast.id),
                model_id=str(model.id),
            )
        else:
            # Try to run forecast synchronously if input data is provided
            if input.input_data:
                try:
                    # Convert input data to DataFrame
                    data = pd.DataFrame(input.input_data)

                    # Determine target and date columns
                    target_col = None
                    date_col = "date"
                    numeric_cols = data.select_dtypes(include=['number']).columns.tolist()
                    if numeric_cols:
                        target_col = numeric_cols[0]

                    possible_date_cols = ["date", "ds", "Date", "DATE", "timestamp"]
                    for col in possible_date_cols:
                        if col in data.columns:
                            date_col = col
                            break

                    if target_col:
                        # Map model type to ForecastService model type
                        model_type_map = {
                            "prophet": ModelType.PROPHET,
                            "arima": ModelType.ARIMA,
                            "ensemble": ModelType.ENSEMBLE,
                        }
                        forecast_model_type = model_type_map.get(
                            model.model_type.lower() if model.model_type else "prophet",
                            ModelType.PROPHET
                        )

                        config = ForecastConfig(
                            model_type=forecast_model_type,
                            horizon=30,  # Default horizon
                            confidence_level=0.95,
                        )

                        service = ForecastService()
                        job = service.create_forecast(
                            data=data,
                            target_col=target_col,
                            date_col=date_col,
                            config=config,
                        )

                        if job.result:
                            predictions = {
                                "predicted_values": job.result.get("values", []),
                                "dates": job.result.get("dates", []),
                            }

                            if input.include_confidence_intervals:
                                confidence_intervals = {
                                    "lower": job.result.get("lower", []),
                                    "upper": job.result.get("upper", []),
                                }

                            logger.info(
                                "Generated synchronous forecast",
                                model_id=str(model.id),
                                metrics=job.result.get("metrics"),
                            )
                except Exception as e:
                    logger.error(
                        "Failed to generate forecast",
                        model_id=str(model.id),
                        error=str(e),
                    )
                    predictions = {"predicted_values": [], "dates": []}
            else:
                predictions = {"predicted_values": [], "dates": []}

        if input.include_contributions:
            # Placeholder - would need channel contribution data from the model
            contribution_by_channel = {}

        return PredictionResult(
            model_id=model.id,
            model_version=version.version,
            predictions=predictions,
            contribution_by_channel=contribution_by_channel,
            confidence_intervals=confidence_intervals,
        )

    @strawberry.mutation
    async def decompose_contributions(
        self,
        info: Info,
        input: DecomposeInput,
    ) -> DecompositionResult:
        """Decompose channel contributions from a trained model."""
        db = await get_db_session(info)
        user = await get_current_user_from_context(info, db)

        # Get model
        result = await db.execute(
            select(Model).where(Model.id == input.model_id)
        )
        model = result.scalar_one_or_none()

        if not model:
            raise NotFoundError("Model", str(input.model_id))

        if model.status != "trained":
            raise ValidationError(f"Model is not trained. Current status: {model.status}")

        # Get current version
        result = await db.execute(
            select(ModelVersion)
            .where(ModelVersion.model_id == model.id)
            .where(ModelVersion.is_current == True)
        )
        version = result.scalar_one_or_none()

        if not version:
            raise ValidationError("No trained model version found")

        logger.info(
            "Running decomposition",
            model_id=str(model.id),
            user_id=str(user.id),
        )

        # Placeholder for actual decomposition logic
        total_contribution = 1000000.0
        baseline_contribution = 300000.0
        channel_contributions = {
            "paid_search": {"contribution": 250000.0, "roi": 3.5, "share": 0.25},
            "paid_social": {"contribution": 200000.0, "roi": 2.8, "share": 0.20},
            "display": {"contribution": 150000.0, "roi": 2.0, "share": 0.15},
            "email": {"contribution": 100000.0, "roi": 5.0, "share": 0.10},
        }

        return DecompositionResult(
            model_id=model.id,
            model_version=version.version,
            total_contribution=total_contribution,
            baseline_contribution=baseline_contribution,
            channel_contributions=channel_contributions,
            time_series_decomposition=None,
        )
