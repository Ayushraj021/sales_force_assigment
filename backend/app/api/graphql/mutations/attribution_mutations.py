"""Attribution Model mutations."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

import strawberry
import structlog
from sqlalchemy import select
from strawberry.types import Info

from app.api.graphql.context import get_db_session, get_current_user_from_context
from app.api.graphql.types.attribution import (
    AttributionModelType,
    AttributionModelTypeEnum,
    AttributionResultType,
    CreateAttributionModelInput,
    RunAttributionInput,
    UpdateAttributionModelInput,
)
from app.core.exceptions import NotFoundError, ValidationError
from app.infrastructure.database.models.experiments import AttributionModel, AttributionModelType as DBAttributionModelType

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


@strawberry.type
class AttributionMutation:
    """Attribution Model mutations."""

    @strawberry.mutation
    async def create_attribution_model(
        self,
        info: Info,
        input: CreateAttributionModelInput,
    ) -> AttributionModelType:
        """Create a new attribution model."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Validate name
        if not input.name or len(input.name.strip()) == 0:
            raise ValidationError("Attribution model name is required")

        # Validate model type
        valid_types = [
            "first_touch", "last_touch", "linear", "time_decay",
            "position_based", "markov", "shapley", "data_driven"
        ]
        if input.model_type not in valid_types:
            raise ValidationError(f"Invalid model type. Must be one of: {', '.join(valid_types)}")

        # Convert string type to enum
        model_type_enum = DBAttributionModelType(input.model_type)

        # Validate position-based weights
        if input.model_type == "position_based":
            first_weight = input.first_touch_weight or 0.4
            last_weight = input.last_touch_weight or 0.4
            if first_weight + last_weight > 1.0:
                raise ValidationError("First touch and last touch weights must sum to <= 1.0")

        # Create model
        model = AttributionModel(
            id=uuid4(),
            name=input.name.strip(),
            description=input.description,
            model_type=model_type_enum,
            lookback_window=input.lookback_window,
            config=input.config,
            time_decay_half_life=input.time_decay_half_life,
            first_touch_weight=input.first_touch_weight,
            last_touch_weight=input.last_touch_weight,
            markov_order=input.markov_order,
            organization_id=current_user.organization_id,
        )
        db.add(model)

        await db.commit()
        await db.refresh(model)

        logger.info(
            "Attribution model created",
            model_id=str(model.id),
            model_name=model.name,
            model_type=input.model_type,
            created_by=str(current_user.id),
        )

        return attribution_model_to_graphql(model)

    @strawberry.mutation
    async def update_attribution_model(
        self,
        info: Info,
        model_id: UUID,
        input: UpdateAttributionModelInput,
    ) -> AttributionModelType:
        """Update an attribution model."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Get model
        result = await db.execute(
            select(AttributionModel).where(
                AttributionModel.id == model_id,
                AttributionModel.organization_id == current_user.organization_id,
            )
        )
        model = result.scalar_one_or_none()

        if not model:
            raise NotFoundError("Attribution model", str(model_id))

        # Update fields
        if input.name is not None:
            if len(input.name.strip()) == 0:
                raise ValidationError("Attribution model name cannot be empty")
            model.name = input.name.strip()
        if input.description is not None:
            model.description = input.description
        if input.lookback_window is not None:
            model.lookback_window = input.lookback_window
        if input.config is not None:
            model.config = input.config
        if input.time_decay_half_life is not None:
            model.time_decay_half_life = input.time_decay_half_life
        if input.first_touch_weight is not None:
            model.first_touch_weight = input.first_touch_weight
        if input.last_touch_weight is not None:
            model.last_touch_weight = input.last_touch_weight
        if input.markov_order is not None:
            model.markov_order = input.markov_order
        if input.is_active is not None:
            model.is_active = input.is_active

        await db.commit()
        await db.refresh(model)

        logger.info(
            "Attribution model updated",
            model_id=str(model.id),
            updated_by=str(current_user.id),
        )

        return attribution_model_to_graphql(model)

    @strawberry.mutation
    async def delete_attribution_model(
        self,
        info: Info,
        model_id: UUID,
    ) -> bool:
        """Delete an attribution model."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Get model
        result = await db.execute(
            select(AttributionModel).where(
                AttributionModel.id == model_id,
                AttributionModel.organization_id == current_user.organization_id,
            )
        )
        model = result.scalar_one_or_none()

        if not model:
            raise NotFoundError("Attribution model", str(model_id))

        await db.delete(model)
        await db.commit()

        logger.info(
            "Attribution model deleted",
            model_id=str(model_id),
            deleted_by=str(current_user.id),
        )

        return True

    @strawberry.mutation
    async def run_attribution(
        self,
        info: Info,
        input: RunAttributionInput,
    ) -> AttributionResultType:
        """Run attribution analysis using a model."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Get model
        result = await db.execute(
            select(AttributionModel).where(
                AttributionModel.id == input.model_id,
                AttributionModel.organization_id == current_user.organization_id,
            )
        )
        model = result.scalar_one_or_none()

        if not model:
            raise NotFoundError("Attribution model", str(input.model_id))

        # Simulated attribution analysis (in production, this would call actual analysis service)
        # Based on model type, calculate channel attribution
        channel_attribution = {}

        if model.model_type == DBAttributionModelType.LAST_TOUCH:
            channel_attribution = {
                "Paid Search": {"conversions": 150, "revenue": 15000, "percentage": 30},
                "Organic Search": {"conversions": 100, "revenue": 10000, "percentage": 20},
                "Social Media": {"conversions": 125, "revenue": 12500, "percentage": 25},
                "Email": {"conversions": 75, "revenue": 7500, "percentage": 15},
                "Direct": {"conversions": 50, "revenue": 5000, "percentage": 10},
            }
        elif model.model_type == DBAttributionModelType.FIRST_TOUCH:
            channel_attribution = {
                "Social Media": {"conversions": 175, "revenue": 17500, "percentage": 35},
                "Paid Search": {"conversions": 125, "revenue": 12500, "percentage": 25},
                "Organic Search": {"conversions": 100, "revenue": 10000, "percentage": 20},
                "Email": {"conversions": 50, "revenue": 5000, "percentage": 10},
                "Direct": {"conversions": 50, "revenue": 5000, "percentage": 10},
            }
        elif model.model_type == DBAttributionModelType.LINEAR:
            channel_attribution = {
                "Paid Search": {"conversions": 133, "revenue": 13300, "percentage": 26.6},
                "Social Media": {"conversions": 150, "revenue": 15000, "percentage": 30},
                "Organic Search": {"conversions": 100, "revenue": 10000, "percentage": 20},
                "Email": {"conversions": 67, "revenue": 6700, "percentage": 13.4},
                "Direct": {"conversions": 50, "revenue": 5000, "percentage": 10},
            }
        else:
            # Default distribution for other models
            channel_attribution = {
                "Paid Search": {"conversions": 140, "revenue": 14000, "percentage": 28},
                "Social Media": {"conversions": 140, "revenue": 14000, "percentage": 28},
                "Organic Search": {"conversions": 100, "revenue": 10000, "percentage": 20},
                "Email": {"conversions": 60, "revenue": 6000, "percentage": 12},
                "Direct": {"conversions": 60, "revenue": 6000, "percentage": 12},
            }

        # Calculate totals
        total_conversions = sum(ch["conversions"] for ch in channel_attribution.values())
        total_revenue = sum(ch["revenue"] for ch in channel_attribution.values())

        # Store results
        model.channel_attribution = channel_attribution
        model.last_run_at = datetime.utcnow()

        await db.commit()

        logger.info(
            "Attribution analysis completed",
            model_id=str(model.id),
            model_type=model.model_type.value if hasattr(model.model_type, 'value') else str(model.model_type),
            total_conversions=total_conversions,
        )

        return AttributionResultType(
            model_id=model.id,
            model_name=model.name,
            model_type=model.model_type.value if hasattr(model.model_type, 'value') else str(model.model_type),
            channel_attribution=channel_attribution,
            total_conversions=total_conversions,
            total_revenue=total_revenue,
            attribution_date=datetime.utcnow(),
            journey_stats={
                "total_journeys": total_conversions,
                "average_touchpoints": 3.5,
                "average_journey_duration_days": 7.2,
            },
        )

    @strawberry.mutation
    async def duplicate_attribution_model(
        self,
        info: Info,
        model_id: UUID,
        new_name: Optional[str] = None,
    ) -> AttributionModelType:
        """Duplicate an attribution model."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Get original model
        result = await db.execute(
            select(AttributionModel).where(
                AttributionModel.id == model_id,
                AttributionModel.organization_id == current_user.organization_id,
            )
        )
        original = result.scalar_one_or_none()

        if not original:
            raise NotFoundError("Attribution model", str(model_id))

        # Create copy
        name = new_name.strip() if new_name else f"{original.name} (Copy)"

        copy = AttributionModel(
            id=uuid4(),
            name=name,
            description=original.description,
            model_type=original.model_type,
            lookback_window=original.lookback_window,
            config=original.config,
            time_decay_half_life=original.time_decay_half_life,
            first_touch_weight=original.first_touch_weight,
            last_touch_weight=original.last_touch_weight,
            markov_order=original.markov_order,
            organization_id=current_user.organization_id,
        )
        db.add(copy)

        await db.commit()
        await db.refresh(copy)

        logger.info(
            "Attribution model duplicated",
            original_id=str(model_id),
            new_id=str(copy.id),
            duplicated_by=str(current_user.id),
        )

        return attribution_model_to_graphql(copy)
