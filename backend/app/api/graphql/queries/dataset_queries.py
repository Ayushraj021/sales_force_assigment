"""Dataset query resolvers."""

from typing import Optional
from uuid import UUID

import strawberry
import structlog
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from strawberry.types import Info

from app.api.graphql.context import get_db_session, get_current_user_from_context
from app.api.graphql.mutations.dataset_mutations import dataset_to_graphql
from app.api.graphql.types.data import DatasetType
from app.core.exceptions import NotFoundError
from app.infrastructure.database.models.dataset import Dataset

logger = structlog.get_logger()


@strawberry.type
class DatasetQuery:
    """Dataset query resolvers."""

    @strawberry.field
    async def datasets(
        self,
        info: Info,
        is_active: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DatasetType]:
        """Get list of datasets for the current organization."""
        db = await get_db_session(info)
        user = await get_current_user_from_context(info, db)

        # Build query with eager loading
        query = (
            select(Dataset)
            .options(
                selectinload(Dataset.channels),
                selectinload(Dataset.metrics),
            )
            .where(Dataset.organization_id == user.organization_id)
        )

        # Apply filters
        if is_active is not None:
            query = query.where(Dataset.is_active == is_active)
        else:
            # By default, only show active datasets
            query = query.where(Dataset.is_active == True)

        # Apply pagination and ordering
        query = query.order_by(Dataset.created_at.desc()).limit(limit).offset(offset)

        result = await db.execute(query)
        datasets = result.scalars().all()

        logger.debug(
            "Fetched datasets",
            count=len(datasets),
            user_id=str(user.id),
        )

        return [dataset_to_graphql(d) for d in datasets]

    @strawberry.field
    async def dataset(
        self,
        info: Info,
        id: UUID,
    ) -> DatasetType:
        """Get a specific dataset by ID."""
        db = await get_db_session(info)
        user = await get_current_user_from_context(info, db)

        # Build query with eager loading
        query = (
            select(Dataset)
            .options(
                selectinload(Dataset.channels),
                selectinload(Dataset.metrics),
                selectinload(Dataset.versions),
            )
            .where(
                Dataset.id == id,
                Dataset.organization_id == user.organization_id,
            )
        )

        result = await db.execute(query)
        dataset = result.scalar_one_or_none()

        if not dataset:
            raise NotFoundError("Dataset", str(id))

        logger.debug(
            "Fetched dataset",
            dataset_id=str(dataset.id),
            user_id=str(user.id),
        )

        return dataset_to_graphql(dataset)
