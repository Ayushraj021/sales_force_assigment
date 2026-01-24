"""Forecast queries."""

from typing import Optional
from uuid import UUID

import strawberry
import structlog
from sqlalchemy import select
from strawberry.types import Info

from app.api.graphql.context import get_db_session, get_current_user_from_context
from app.api.graphql.types.model import ForecastType
from app.core.exceptions import NotFoundError
from app.infrastructure.database.models.forecast import Forecast

logger = structlog.get_logger()


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
class ForecastQuery:
    """Forecast queries."""

    @strawberry.field
    async def forecasts(
        self,
        info: Info,
        status: Optional[str] = None,
        model_type: Optional[str] = None,
        dataset_id: Optional[UUID] = None,
        is_active: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ForecastType]:
        """Get all forecasts for the organization."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        query = select(Forecast).where(
            Forecast.organization_id == current_user.organization_id
        )

        # Apply filters
        if status is not None:
            query = query.where(Forecast.status == status)

        if model_type is not None:
            query = query.where(Forecast.model_type == model_type)

        if dataset_id is not None:
            query = query.where(Forecast.dataset_id == dataset_id)

        if is_active is not None:
            query = query.where(Forecast.is_active == is_active)

        # Order and paginate
        query = query.order_by(Forecast.created_at.desc()).offset(offset).limit(limit)

        result = await db.execute(query)
        forecasts = result.scalars().all()

        return [forecast_to_graphql(f) for f in forecasts]

    @strawberry.field
    async def forecast(
        self,
        info: Info,
        forecast_id: UUID,
    ) -> ForecastType:
        """Get a specific forecast by ID."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        result = await db.execute(
            select(Forecast).where(
                Forecast.id == forecast_id,
                Forecast.organization_id == current_user.organization_id,
            )
        )
        forecast = result.scalar_one_or_none()

        if not forecast:
            raise NotFoundError("Forecast", str(forecast_id))

        return forecast_to_graphql(forecast)

    @strawberry.field
    async def forecast_model_types(self) -> list[str]:
        """Get list of available forecast model types."""
        return [
            "prophet",
            "arima",
            "ensemble",
            "neural",
            "deepar",
            "tft",
            "nbeats",
        ]
