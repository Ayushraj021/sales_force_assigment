"""Channel and Metric mutations."""

from uuid import UUID, uuid4

import strawberry
import structlog
from sqlalchemy import select
from strawberry.types import Info

from app.api.graphql.context import get_db_session, get_current_user_from_context
from app.api.graphql.types.data import (
    ChannelType,
    CreateChannelInput,
    CreateMetricInput,
    MetricType,
    UpdateChannelInput,
    UpdateMetricInput,
)
from app.core.exceptions import NotFoundError, ValidationError
from app.infrastructure.database.models.dataset import Channel, Dataset, Metric

logger = structlog.get_logger()


def channel_to_graphql(channel: Channel) -> ChannelType:
    """Convert channel to GraphQL type."""
    return ChannelType(
        id=channel.id,
        name=channel.name,
        display_name=channel.display_name,
        description=channel.description,
        channel_type=channel.channel_type,
        spend_column=channel.spend_column,
        impression_column=channel.impression_column,
        click_column=channel.click_column,
        default_adstock_type=channel.default_adstock_type or "geometric",
        default_saturation_type=channel.default_saturation_type or "hill",
        dataset_id=channel.dataset_id,
        created_at=channel.created_at,
        updated_at=channel.updated_at,
    )


def metric_to_graphql(metric: Metric) -> MetricType:
    """Convert metric to GraphQL type."""
    return MetricType(
        id=metric.id,
        name=metric.name,
        display_name=metric.display_name,
        description=metric.description,
        metric_type=metric.metric_type,
        column_name=metric.column_name,
        aggregation_method=metric.aggregation_method or "sum",
        is_target=metric.is_target or False,
        dataset_id=metric.dataset_id,
        created_at=metric.created_at,
        updated_at=metric.updated_at,
    )


@strawberry.type
class ChannelMutation:
    """Channel and Metric mutations."""

    @strawberry.mutation
    async def create_channel(
        self,
        info: Info,
        input: CreateChannelInput,
    ) -> ChannelType:
        """Create a new marketing channel."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Validate name
        if not input.name or len(input.name.strip()) == 0:
            raise ValidationError("Channel name is required")

        # Validate channel type
        valid_types = ["paid", "organic", "owned", "earned"]
        if input.channel_type not in valid_types:
            raise ValidationError(f"channel_type must be one of: {', '.join(valid_types)}")

        # Verify dataset exists and user has access
        result = await db.execute(
            select(Dataset).where(
                Dataset.id == input.dataset_id,
                Dataset.organization_id == current_user.organization_id,
            )
        )
        dataset = result.scalar_one_or_none()
        if not dataset:
            raise NotFoundError("Dataset", str(input.dataset_id))

        # Check for duplicate name within dataset
        result = await db.execute(
            select(Channel).where(
                Channel.dataset_id == input.dataset_id,
                Channel.name == input.name.strip(),
            )
        )
        if result.scalar_one_or_none():
            raise ValidationError(f"Channel '{input.name}' already exists in this dataset")

        # Create channel
        channel = Channel(
            id=uuid4(),
            name=input.name.strip(),
            display_name=input.display_name,
            description=input.description,
            channel_type=input.channel_type,
            spend_column=input.spend_column,
            impression_column=input.impression_column,
            click_column=input.click_column,
            default_adstock_type=input.default_adstock_type,
            default_saturation_type=input.default_saturation_type,
            dataset_id=input.dataset_id,
        )
        db.add(channel)

        await db.commit()
        await db.refresh(channel)

        logger.info(
            "Channel created",
            channel_id=str(channel.id),
            channel_name=channel.name,
            dataset_id=str(input.dataset_id),
            created_by=str(current_user.id),
        )

        return channel_to_graphql(channel)

    @strawberry.mutation
    async def update_channel(
        self,
        info: Info,
        channel_id: UUID,
        input: UpdateChannelInput,
    ) -> ChannelType:
        """Update a marketing channel."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Get channel with dataset verification
        result = await db.execute(
            select(Channel).join(Dataset).where(
                Channel.id == channel_id,
                Dataset.organization_id == current_user.organization_id,
            )
        )
        channel = result.scalar_one_or_none()

        if not channel:
            raise NotFoundError("Channel", str(channel_id))

        # Update fields
        if input.name is not None:
            if len(input.name.strip()) == 0:
                raise ValidationError("Channel name cannot be empty")
            # Check for duplicate name
            result = await db.execute(
                select(Channel).where(
                    Channel.dataset_id == channel.dataset_id,
                    Channel.name == input.name.strip(),
                    Channel.id != channel_id,
                )
            )
            if result.scalar_one_or_none():
                raise ValidationError(f"Channel '{input.name}' already exists in this dataset")
            channel.name = input.name.strip()
        if input.display_name is not None:
            channel.display_name = input.display_name
        if input.description is not None:
            channel.description = input.description
        if input.channel_type is not None:
            valid_types = ["paid", "organic", "owned", "earned"]
            if input.channel_type not in valid_types:
                raise ValidationError(f"channel_type must be one of: {', '.join(valid_types)}")
            channel.channel_type = input.channel_type
        if input.spend_column is not None:
            channel.spend_column = input.spend_column
        if input.impression_column is not None:
            channel.impression_column = input.impression_column
        if input.click_column is not None:
            channel.click_column = input.click_column
        if input.default_adstock_type is not None:
            channel.default_adstock_type = input.default_adstock_type
        if input.default_saturation_type is not None:
            channel.default_saturation_type = input.default_saturation_type

        await db.commit()
        await db.refresh(channel)

        logger.info(
            "Channel updated",
            channel_id=str(channel.id),
            updated_by=str(current_user.id),
        )

        return channel_to_graphql(channel)

    @strawberry.mutation
    async def delete_channel(
        self,
        info: Info,
        channel_id: UUID,
    ) -> bool:
        """Delete a marketing channel."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Get channel with dataset verification
        result = await db.execute(
            select(Channel).join(Dataset).where(
                Channel.id == channel_id,
                Dataset.organization_id == current_user.organization_id,
            )
        )
        channel = result.scalar_one_or_none()

        if not channel:
            raise NotFoundError("Channel", str(channel_id))

        await db.delete(channel)
        await db.commit()

        logger.info(
            "Channel deleted",
            channel_id=str(channel_id),
            deleted_by=str(current_user.id),
        )

        return True

    @strawberry.mutation
    async def create_metric(
        self,
        info: Info,
        input: CreateMetricInput,
    ) -> MetricType:
        """Create a new business metric."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Validate name
        if not input.name or len(input.name.strip()) == 0:
            raise ValidationError("Metric name is required")

        # Validate metric type
        valid_types = ["revenue", "conversions", "leads", "impressions", "clicks", "custom"]
        if input.metric_type not in valid_types:
            raise ValidationError(f"metric_type must be one of: {', '.join(valid_types)}")

        # Validate aggregation method
        valid_agg = ["sum", "avg", "min", "max", "count", "first", "last"]
        if input.aggregation_method not in valid_agg:
            raise ValidationError(f"aggregation_method must be one of: {', '.join(valid_agg)}")

        # Verify dataset exists and user has access
        result = await db.execute(
            select(Dataset).where(
                Dataset.id == input.dataset_id,
                Dataset.organization_id == current_user.organization_id,
            )
        )
        dataset = result.scalar_one_or_none()
        if not dataset:
            raise NotFoundError("Dataset", str(input.dataset_id))

        # Check for duplicate name within dataset
        result = await db.execute(
            select(Metric).where(
                Metric.dataset_id == input.dataset_id,
                Metric.name == input.name.strip(),
            )
        )
        if result.scalar_one_or_none():
            raise ValidationError(f"Metric '{input.name}' already exists in this dataset")

        # If setting as target, unset other targets in this dataset
        if input.is_target:
            result = await db.execute(
                select(Metric).where(
                    Metric.dataset_id == input.dataset_id,
                    Metric.is_target == True,
                )
            )
            for other in result.scalars().all():
                other.is_target = False

        # Create metric
        metric = Metric(
            id=uuid4(),
            name=input.name.strip(),
            display_name=input.display_name,
            description=input.description,
            metric_type=input.metric_type,
            column_name=input.column_name,
            aggregation_method=input.aggregation_method,
            is_target=input.is_target,
            dataset_id=input.dataset_id,
        )
        db.add(metric)

        await db.commit()
        await db.refresh(metric)

        logger.info(
            "Metric created",
            metric_id=str(metric.id),
            metric_name=metric.name,
            dataset_id=str(input.dataset_id),
            created_by=str(current_user.id),
        )

        return metric_to_graphql(metric)

    @strawberry.mutation
    async def update_metric(
        self,
        info: Info,
        metric_id: UUID,
        input: UpdateMetricInput,
    ) -> MetricType:
        """Update a business metric."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Get metric with dataset verification
        result = await db.execute(
            select(Metric).join(Dataset).where(
                Metric.id == metric_id,
                Dataset.organization_id == current_user.organization_id,
            )
        )
        metric = result.scalar_one_or_none()

        if not metric:
            raise NotFoundError("Metric", str(metric_id))

        # Update fields
        if input.name is not None:
            if len(input.name.strip()) == 0:
                raise ValidationError("Metric name cannot be empty")
            # Check for duplicate name
            result = await db.execute(
                select(Metric).where(
                    Metric.dataset_id == metric.dataset_id,
                    Metric.name == input.name.strip(),
                    Metric.id != metric_id,
                )
            )
            if result.scalar_one_or_none():
                raise ValidationError(f"Metric '{input.name}' already exists in this dataset")
            metric.name = input.name.strip()
        if input.display_name is not None:
            metric.display_name = input.display_name
        if input.description is not None:
            metric.description = input.description
        if input.metric_type is not None:
            valid_types = ["revenue", "conversions", "leads", "impressions", "clicks", "custom"]
            if input.metric_type not in valid_types:
                raise ValidationError(f"metric_type must be one of: {', '.join(valid_types)}")
            metric.metric_type = input.metric_type
        if input.column_name is not None:
            metric.column_name = input.column_name
        if input.aggregation_method is not None:
            valid_agg = ["sum", "avg", "min", "max", "count", "first", "last"]
            if input.aggregation_method not in valid_agg:
                raise ValidationError(f"aggregation_method must be one of: {', '.join(valid_agg)}")
            metric.aggregation_method = input.aggregation_method
        if input.is_target is not None:
            # If setting as target, unset other targets
            if input.is_target:
                result = await db.execute(
                    select(Metric).where(
                        Metric.dataset_id == metric.dataset_id,
                        Metric.is_target == True,
                        Metric.id != metric_id,
                    )
                )
                for other in result.scalars().all():
                    other.is_target = False
            metric.is_target = input.is_target

        await db.commit()
        await db.refresh(metric)

        logger.info(
            "Metric updated",
            metric_id=str(metric.id),
            updated_by=str(current_user.id),
        )

        return metric_to_graphql(metric)

    @strawberry.mutation
    async def delete_metric(
        self,
        info: Info,
        metric_id: UUID,
    ) -> bool:
        """Delete a business metric."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Get metric with dataset verification
        result = await db.execute(
            select(Metric).join(Dataset).where(
                Metric.id == metric_id,
                Dataset.organization_id == current_user.organization_id,
            )
        )
        metric = result.scalar_one_or_none()

        if not metric:
            raise NotFoundError("Metric", str(metric_id))

        await db.delete(metric)
        await db.commit()

        logger.info(
            "Metric deleted",
            metric_id=str(metric_id),
            deleted_by=str(current_user.id),
        )

        return True

    @strawberry.mutation
    async def set_target_metric(
        self,
        info: Info,
        metric_id: UUID,
    ) -> MetricType:
        """Set a metric as the target metric for its dataset."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Get metric with dataset verification
        result = await db.execute(
            select(Metric).join(Dataset).where(
                Metric.id == metric_id,
                Dataset.organization_id == current_user.organization_id,
            )
        )
        metric = result.scalar_one_or_none()

        if not metric:
            raise NotFoundError("Metric", str(metric_id))

        # Unset other targets in this dataset
        result = await db.execute(
            select(Metric).where(
                Metric.dataset_id == metric.dataset_id,
                Metric.is_target == True,
            )
        )
        for other in result.scalars().all():
            other.is_target = False

        # Set this metric as target
        metric.is_target = True

        await db.commit()
        await db.refresh(metric)

        logger.info(
            "Target metric set",
            metric_id=str(metric.id),
            dataset_id=str(metric.dataset_id),
            set_by=str(current_user.id),
        )

        return metric_to_graphql(metric)
