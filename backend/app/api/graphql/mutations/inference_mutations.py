"""Model inference mutations."""

from typing import Optional
from uuid import UUID

import strawberry
import structlog
from sqlalchemy import select
from strawberry.scalars import JSON
from strawberry.types import Info

from app.api.graphql.context import get_db_session, get_current_user_from_context
from app.core.exceptions import NotFoundError, ValidationError
from app.infrastructure.database.models.model import Model, ModelVersion

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

        # Run prediction based on model type
        predictions = {}
        contribution_by_channel = None
        confidence_intervals = None

        # Placeholder for actual prediction logic
        # This would load the model from MLflow and run inference
        predictions = {
            "predicted_values": [],
            "dates": [],
        }

        if input.include_contributions:
            contribution_by_channel = {
                "channel_1": [],
                "channel_2": [],
            }

        if input.include_confidence_intervals:
            confidence_intervals = {
                "lower": [],
                "upper": [],
            }

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
