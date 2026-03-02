"""Attribution Model queries."""

from typing import Optional
from uuid import UUID

import strawberry
import structlog
from sqlalchemy import select, func
from strawberry.types import Info

from app.api.graphql.context import get_db_session, get_current_user_from_context
from app.api.graphql.types.attribution import (
    AttributionModelFilterInput,
    AttributionModelType,
    AttributionModelTypeEnum,
    ChannelAttributionType,
    CustomerJourneyType,
)
from app.core.exceptions import NotFoundError
from app.infrastructure.database.models.experiments import (
    AttributionModel,
    AttributionModelType as DBAttributionModelType,
    CustomerJourney,
)

logger = structlog.get_logger()


def attribution_model_to_graphql(model: AttributionModel) -> AttributionModelType:
    """Convert attribution model to GraphQL type."""
    type_mapping = {
        DBAttributionModelType.FIRST_TOUCH: AttributionModelTypeEnum.FIRST_TOUCH,
        DBAttributionModelType.LAST_TOUCH: AttributionModelTypeEnum.LAST_TOUCH,
        DBAttributionModelType.LINEAR: AttributionModelTypeEnum.LINEAR,
        DBAttributionModelType.TIME_DECAY: AttributionModelTypeEnum.TIME_DECAY,
        DBAttributionModelType.POSITION_BASED: AttributionModelTypeEnum.POSITION_BASED,
        DBAttributionModelType.MARKOV: AttributionModelTypeEnum.MARKOV,
        DBAttributionModelType.SHAPLEY: AttributionModelTypeEnum.SHAPLEY,
        DBAttributionModelType.DATA_DRIVEN: AttributionModelTypeEnum.DATA_DRIVEN,
    }

    return AttributionModelType(
        id=model.id,
        name=model.name,
        description=model.description,
        model_type=type_mapping.get(model.model_type, AttributionModelTypeEnum.LAST_TOUCH),
        lookback_window=model.lookback_window or 30,
        config=model.config,
        time_decay_half_life=model.time_decay_half_life,
        first_touch_weight=model.first_touch_weight,
        last_touch_weight=model.last_touch_weight,
        markov_order=model.markov_order,
        channel_attribution=model.channel_attribution,
        last_run_at=model.last_run_at,
        organization_id=model.organization_id,
        is_active=model.is_active if model.is_active is not None else True,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def customer_journey_to_graphql(journey: CustomerJourney) -> CustomerJourneyType:
    """Convert customer journey to GraphQL type."""
    return CustomerJourneyType(
        id=journey.id,
        customer_id=journey.customer_id,
        anonymous_id=journey.anonymous_id,
        touchpoints=journey.touchpoints,
        n_touchpoints=journey.n_touchpoints,
        converted=journey.converted or False,
        conversion_value=journey.conversion_value,
        converted_at=journey.converted_at,
        conversion_type=journey.conversion_type,
        first_touch_at=journey.first_touch_at,
        last_touch_at=journey.last_touch_at,
        journey_duration_seconds=journey.journey_duration_seconds,
        channels_touched=journey.channels_touched,
        first_channel=journey.first_channel,
        last_channel=journey.last_channel,
        created_at=journey.created_at,
    )


@strawberry.type
class AttributionQuery:
    """Attribution Model queries."""

    @strawberry.field
    async def attribution_models(
        self,
        info: Info,
        filter: Optional[AttributionModelFilterInput] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AttributionModelType]:
        """Get attribution models for the organization."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        query = select(AttributionModel).where(
            AttributionModel.organization_id == current_user.organization_id
        )

        # Apply filters
        if filter:
            if filter.model_type:
                try:
                    model_type_enum = DBAttributionModelType(filter.model_type)
                    query = query.where(AttributionModel.model_type == model_type_enum)
                except ValueError:
                    pass
            if filter.is_active is not None:
                query = query.where(AttributionModel.is_active == filter.is_active)

        # Order by name and paginate
        query = query.order_by(AttributionModel.name).offset(offset).limit(limit)

        result = await db.execute(query)
        models = result.scalars().all()

        return [attribution_model_to_graphql(m) for m in models]

    @strawberry.field
    async def attribution_model(
        self,
        info: Info,
        model_id: UUID,
    ) -> AttributionModelType:
        """Get a specific attribution model by ID."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        result = await db.execute(
            select(AttributionModel).where(
                AttributionModel.id == model_id,
                AttributionModel.organization_id == current_user.organization_id,
            )
        )
        model = result.scalar_one_or_none()

        if not model:
            raise NotFoundError("Attribution model", str(model_id))

        return attribution_model_to_graphql(model)

    @strawberry.field
    async def attribution_model_types(self) -> list[str]:
        """Get list of available attribution model types."""
        return [
            "first_touch",
            "last_touch",
            "linear",
            "time_decay",
            "position_based",
            "markov",
            "shapley",
            "data_driven",
        ]

    @strawberry.field
    async def customer_journeys(
        self,
        info: Info,
        converted_only: bool = False,
        conversion_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CustomerJourneyType]:
        """Get customer journeys for the organization."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        query = select(CustomerJourney).where(
            CustomerJourney.organization_id == current_user.organization_id
        )

        if converted_only:
            query = query.where(CustomerJourney.converted == True)

        if conversion_type:
            query = query.where(CustomerJourney.conversion_type == conversion_type)

        query = query.order_by(CustomerJourney.created_at.desc()).offset(offset).limit(limit)

        result = await db.execute(query)
        journeys = result.scalars().all()

        return [customer_journey_to_graphql(j) for j in journeys]

    @strawberry.field
    async def customer_journey(
        self,
        info: Info,
        journey_id: UUID,
    ) -> CustomerJourneyType:
        """Get a specific customer journey by ID."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        result = await db.execute(
            select(CustomerJourney).where(
                CustomerJourney.id == journey_id,
                CustomerJourney.organization_id == current_user.organization_id,
            )
        )
        journey = result.scalar_one_or_none()

        if not journey:
            raise NotFoundError("Customer journey", str(journey_id))

        return customer_journey_to_graphql(journey)

    @strawberry.field
    async def channel_attribution_summary(
        self,
        info: Info,
        model_id: UUID,
    ) -> list[ChannelAttributionType]:
        """Get channel attribution breakdown from a model's latest run."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        result = await db.execute(
            select(AttributionModel).where(
                AttributionModel.id == model_id,
                AttributionModel.organization_id == current_user.organization_id,
            )
        )
        model = result.scalar_one_or_none()

        if not model:
            raise NotFoundError("Attribution model", str(model_id))

        if not model.channel_attribution:
            return []

        channel_list = []
        total_conversions = sum(
            ch.get("conversions", 0) for ch in model.channel_attribution.values()
        )

        for channel, data in model.channel_attribution.items():
            channel_list.append(
                ChannelAttributionType(
                    channel=channel,
                    attributed_conversions=data.get("conversions", 0),
                    attributed_revenue=data.get("revenue", 0),
                    contribution_percentage=data.get("percentage", 0),
                    first_touch_conversions=data.get("first_touch", 0),
                    last_touch_conversions=data.get("last_touch", 0),
                    average_position_in_journey=data.get("avg_position", 0),
                )
            )

        return channel_list

    @strawberry.field
    async def journey_stats(
        self,
        info: Info,
    ) -> strawberry.scalars.JSON:
        """Get journey statistics for the organization."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Total journeys
        total_result = await db.execute(
            select(func.count(CustomerJourney.id)).where(
                CustomerJourney.organization_id == current_user.organization_id
            )
        )
        total_journeys = total_result.scalar() or 0

        # Converted journeys
        converted_result = await db.execute(
            select(func.count(CustomerJourney.id)).where(
                CustomerJourney.organization_id == current_user.organization_id,
                CustomerJourney.converted == True,
            )
        )
        converted_journeys = converted_result.scalar() or 0

        # Average touchpoints
        avg_touchpoints_result = await db.execute(
            select(func.avg(CustomerJourney.n_touchpoints)).where(
                CustomerJourney.organization_id == current_user.organization_id
            )
        )
        avg_touchpoints = avg_touchpoints_result.scalar() or 0

        # Average journey duration
        avg_duration_result = await db.execute(
            select(func.avg(CustomerJourney.journey_duration_seconds)).where(
                CustomerJourney.organization_id == current_user.organization_id,
                CustomerJourney.converted == True,
            )
        )
        avg_duration = avg_duration_result.scalar() or 0

        return {
            "total_journeys": total_journeys,
            "converted_journeys": converted_journeys,
            "conversion_rate": (converted_journeys / total_journeys * 100) if total_journeys > 0 else 0,
            "average_touchpoints": float(avg_touchpoints) if avg_touchpoints else 0,
            "average_journey_duration_seconds": float(avg_duration) if avg_duration else 0,
        }
