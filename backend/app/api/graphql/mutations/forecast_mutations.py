"""Forecast management mutations."""

from typing import Optional
from uuid import UUID, uuid4

import strawberry
import structlog
from sqlalchemy import select
from strawberry.types import Info

from app.api.graphql.context import get_db_session, get_current_user_from_context
from app.api.graphql.types.model import (
    CreateForecastInput,
    ForecastType,
    UpdateForecastInput,
)
from app.core.exceptions import NotFoundError, ValidationError
from app.infrastructure.database.models.forecast import Forecast
from app.infrastructure.database.models.dataset import Dataset

logger = structlog.get_logger()

# Valid forecast model types
VALID_MODEL_TYPES = {
    "prophet",
    "arima",
    "ensemble",
    "neural",
    "deepar",
    "tft",
    "nbeats",
}


def forecast_to_graphql(forecast: Forecast) -> ForecastType:
    """Convert database forecast to GraphQL type."""
    return ForecastType(
        id=forecast.id,
        name=forecast.name,
        description=forecast.description,
        status=forecast.status,
        model_type=forecast.model_type,
        target_metric=forecast.target_metric,
        horizon=forecast.horizon,
        confidence_level=forecast.confidence_level,
        start_date=forecast.start_date,
        end_date=forecast.end_date,
        forecast_start_date=forecast.forecast_start_date,
        forecast_end_date=forecast.forecast_end_date,
        predicted_values=forecast.predicted_values,
        lower_bounds=forecast.lower_bounds,
        upper_bounds=forecast.upper_bounds,
        forecast_dates=forecast.forecast_dates,
        model_params=forecast.model_params,
        metrics=forecast.metrics,
        error_message=forecast.error_message,
        is_active=forecast.is_active,
        dataset_id=forecast.dataset_id,
        model_id=forecast.model_id,
        created_at=forecast.created_at,
        updated_at=forecast.updated_at,
    )


@strawberry.type
class ForecastMutation:
    """Forecast management mutations."""

    @strawberry.mutation
    async def create_forecast(
        self,
        info: Info,
        input: CreateForecastInput,
    ) -> ForecastType:
        """Create a new forecast and queue it for generation."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Validate model type
        if input.model_type not in VALID_MODEL_TYPES:
            raise ValidationError(
                f"Invalid model type '{input.model_type}'. "
                f"Valid types: {', '.join(sorted(VALID_MODEL_TYPES))}"
            )

        # Validate name
        if not input.name or len(input.name.strip()) == 0:
            raise ValidationError("Forecast name is required")

        # Validate horizon
        if input.horizon < 1 or input.horizon > 365:
            raise ValidationError("Horizon must be between 1 and 365 days")

        # Validate confidence level
        if input.confidence_level <= 0 or input.confidence_level >= 1:
            raise ValidationError("Confidence level must be between 0 and 1")

        # Verify dataset exists and belongs to organization
        result = await db.execute(
            select(Dataset).where(
                Dataset.id == input.dataset_id,
                Dataset.organization_id == current_user.organization_id,
            )
        )
        dataset = result.scalar_one_or_none()

        if not dataset:
            raise NotFoundError("Dataset", str(input.dataset_id))

        if not dataset.is_active:
            raise ValidationError("Cannot create forecast from inactive dataset")

        # Create forecast
        forecast = Forecast(
            id=uuid4(),
            name=input.name.strip(),
            description=input.description,
            status="pending",
            model_type=input.model_type,
            target_metric=input.target_metric,
            horizon=input.horizon,
            confidence_level=input.confidence_level,
            model_params=input.model_params or {},
            dataset_id=input.dataset_id,
            organization_id=current_user.organization_id,
            created_by_id=current_user.id,
            is_active=True,
        )
        db.add(forecast)

        await db.commit()
        await db.refresh(forecast)

        logger.info(
            "Forecast created",
            forecast_id=str(forecast.id),
            model_type=input.model_type,
            created_by=str(current_user.id),
        )

        # Queue the forecast generation task
        from app.workers.tasks.forecasting import generate_forecast
        generate_forecast.delay(str(forecast.id))

        return forecast_to_graphql(forecast)

    @strawberry.mutation
    async def update_forecast(
        self,
        info: Info,
        forecast_id: UUID,
        input: UpdateForecastInput,
    ) -> ForecastType:
        """Update a forecast's metadata."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Get forecast
        result = await db.execute(
            select(Forecast).where(
                Forecast.id == forecast_id,
                Forecast.organization_id == current_user.organization_id,
            )
        )
        forecast = result.scalar_one_or_none()

        if not forecast:
            raise NotFoundError("Forecast", str(forecast_id))

        # Update fields
        if input.name is not None:
            if len(input.name.strip()) == 0:
                raise ValidationError("Forecast name cannot be empty")
            forecast.name = input.name.strip()

        if input.description is not None:
            forecast.description = input.description

        if input.is_active is not None:
            forecast.is_active = input.is_active

        await db.commit()
        await db.refresh(forecast)

        logger.info(
            "Forecast updated",
            forecast_id=str(forecast.id),
            updated_by=str(current_user.id),
        )

        return forecast_to_graphql(forecast)

    @strawberry.mutation
    async def delete_forecast(
        self,
        info: Info,
        forecast_id: UUID,
    ) -> bool:
        """Delete a forecast (soft delete)."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Get forecast
        result = await db.execute(
            select(Forecast).where(
                Forecast.id == forecast_id,
                Forecast.organization_id == current_user.organization_id,
            )
        )
        forecast = result.scalar_one_or_none()

        if not forecast:
            raise NotFoundError("Forecast", str(forecast_id))

        # Soft delete
        forecast.is_active = False

        await db.commit()

        logger.info(
            "Forecast deleted",
            forecast_id=str(forecast.id),
            deleted_by=str(current_user.id),
        )

        return True

    @strawberry.mutation
    async def regenerate_forecast(
        self,
        info: Info,
        forecast_id: UUID,
    ) -> ForecastType:
        """Regenerate an existing forecast with the same parameters."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Get forecast
        result = await db.execute(
            select(Forecast).where(
                Forecast.id == forecast_id,
                Forecast.organization_id == current_user.organization_id,
            )
        )
        forecast = result.scalar_one_or_none()

        if not forecast:
            raise NotFoundError("Forecast", str(forecast_id))

        if not forecast.is_active:
            raise ValidationError("Cannot regenerate inactive forecast")

        # Reset status and results
        forecast.status = "pending"
        forecast.predicted_values = []
        forecast.lower_bounds = []
        forecast.upper_bounds = []
        forecast.forecast_dates = []
        forecast.metrics = {}
        forecast.error_message = None

        await db.commit()
        await db.refresh(forecast)

        logger.info(
            "Forecast regeneration queued",
            forecast_id=str(forecast.id),
            queued_by=str(current_user.id),
        )

        # Queue the forecast generation task
        from app.workers.tasks.forecasting import generate_forecast
        generate_forecast.delay(str(forecast.id))

        return forecast_to_graphql(forecast)
