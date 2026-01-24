"""Channel and Metric queries."""

from typing import Optional
from uuid import UUID

import strawberry
import structlog
from sqlalchemy import select
from strawberry.types import Info

from app.api.graphql.context import get_db_session, get_current_user_from_context
from app.api.graphql.types.data import (
    ChannelFilterInput,
    ChannelType,
    MetricFilterInput,
    MetricType,
)
from app.core.exceptions import NotFoundError
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
class ChannelQuery:
    """Channel and Metric queries."""

    @strawberry.field
    async def channels(
        self,
        info: Info,
        filter: Optional[ChannelFilterInput] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ChannelType]:
        """Get marketing channels for the organization."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        query = (
            select(Channel)
            .join(Dataset)
            .where(Dataset.organization_id == current_user.organization_id)
        )

        # Apply filters
        if filter:
            if filter.dataset_id:
                query = query.where(Channel.dataset_id == filter.dataset_id)
            if filter.channel_type:
                query = query.where(Channel.channel_type == filter.channel_type)

        # Order and paginate
        query = query.order_by(Channel.name).offset(offset).limit(limit)

        result = await db.execute(query)
        channels = result.scalars().all()

        return [channel_to_graphql(c) for c in channels]

    @strawberry.field
    async def channel(
        self,
        info: Info,
        channel_id: UUID,
    ) -> ChannelType:
        """Get a specific channel by ID."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        result = await db.execute(
            select(Channel)
            .join(Dataset)
            .where(
                Channel.id == channel_id,
                Dataset.organization_id == current_user.organization_id,
            )
        )
        channel = result.scalar_one_or_none()

        if not channel:
            raise NotFoundError("Channel", str(channel_id))

        return channel_to_graphql(channel)

    @strawberry.field
    async def channels_by_dataset(
        self,
        info: Info,
        dataset_id: UUID,
    ) -> list[ChannelType]:
        """Get all channels for a specific dataset."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Verify dataset access
        result = await db.execute(
            select(Dataset).where(
                Dataset.id == dataset_id,
                Dataset.organization_id == current_user.organization_id,
            )
        )
        if not result.scalar_one_or_none():
            raise NotFoundError("Dataset", str(dataset_id))

        result = await db.execute(
            select(Channel)
            .where(Channel.dataset_id == dataset_id)
            .order_by(Channel.name)
        )
        channels = result.scalars().all()

        return [channel_to_graphql(c) for c in channels]

    @strawberry.field
    async def channel_types(self) -> list[str]:
        """Get list of available channel types."""
        return ["paid", "organic", "owned", "earned"]

    @strawberry.field
    async def adstock_types(self) -> list[str]:
        """Get list of available adstock transformation types."""
        return ["geometric", "weibull", "delayed", "carryover"]

    @strawberry.field
    async def saturation_types(self) -> list[str]:
        """Get list of available saturation curve types."""
        return ["hill", "logistic", "michaelis_menten", "tanh"]

    @strawberry.field
    async def metrics(
        self,
        info: Info,
        filter: Optional[MetricFilterInput] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MetricType]:
        """Get business metrics for the organization."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        query = (
            select(Metric)
            .join(Dataset)
            .where(Dataset.organization_id == current_user.organization_id)
        )

        # Apply filters
        if filter:
            if filter.dataset_id:
                query = query.where(Metric.dataset_id == filter.dataset_id)
            if filter.metric_type:
                query = query.where(Metric.metric_type == filter.metric_type)
            if filter.is_target is not None:
                query = query.where(Metric.is_target == filter.is_target)

        # Order and paginate
        query = query.order_by(Metric.name).offset(offset).limit(limit)

        result = await db.execute(query)
        metrics = result.scalars().all()

        return [metric_to_graphql(m) for m in metrics]

    @strawberry.field
    async def metric(
        self,
        info: Info,
        metric_id: UUID,
    ) -> MetricType:
        """Get a specific metric by ID."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        result = await db.execute(
            select(Metric)
            .join(Dataset)
            .where(
                Metric.id == metric_id,
                Dataset.organization_id == current_user.organization_id,
            )
        )
        metric = result.scalar_one_or_none()

        if not metric:
            raise NotFoundError("Metric", str(metric_id))

        return metric_to_graphql(metric)

    @strawberry.field
    async def metrics_by_dataset(
        self,
        info: Info,
        dataset_id: UUID,
    ) -> list[MetricType]:
        """Get all metrics for a specific dataset."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Verify dataset access
        result = await db.execute(
            select(Dataset).where(
                Dataset.id == dataset_id,
                Dataset.organization_id == current_user.organization_id,
            )
        )
        if not result.scalar_one_or_none():
            raise NotFoundError("Dataset", str(dataset_id))

        result = await db.execute(
            select(Metric)
            .where(Metric.dataset_id == dataset_id)
            .order_by(Metric.name)
        )
        metrics = result.scalars().all()

        return [metric_to_graphql(m) for m in metrics]

    @strawberry.field
    async def target_metric(
        self,
        info: Info,
        dataset_id: UUID,
    ) -> Optional[MetricType]:
        """Get the target metric for a dataset."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Verify dataset access
        result = await db.execute(
            select(Dataset).where(
                Dataset.id == dataset_id,
                Dataset.organization_id == current_user.organization_id,
            )
        )
        if not result.scalar_one_or_none():
            raise NotFoundError("Dataset", str(dataset_id))

        result = await db.execute(
            select(Metric).where(
                Metric.dataset_id == dataset_id,
                Metric.is_target == True,
            )
        )
        metric = result.scalar_one_or_none()

        if not metric:
            return None

        return metric_to_graphql(metric)

    @strawberry.field
    async def metric_types(self) -> list[str]:
        """Get list of available metric types."""
        return ["revenue", "conversions", "leads", "impressions", "clicks", "custom"]

    @strawberry.field
    async def aggregation_methods(self) -> list[str]:
        """Get list of available aggregation methods."""
        return ["sum", "avg", "min", "max", "count", "first", "last"]
