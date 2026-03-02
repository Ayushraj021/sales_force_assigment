"""Dataset management mutations."""

from typing import Optional
from uuid import UUID, uuid4

import strawberry
import structlog
from sqlalchemy import select
from strawberry.types import Info

from app.api.graphql.context import get_db_session, get_current_user_from_context
from app.api.graphql.types.data import (
    CreateDatasetInput,
    DatasetType,
    ChannelType,
    MetricType,
)
from app.core.exceptions import NotFoundError, ValidationError
from app.infrastructure.database.models.dataset import Dataset, Channel, Metric

logger = structlog.get_logger()


def dataset_to_graphql(dataset: Dataset) -> DatasetType:
    """Convert database dataset to GraphQL type."""
    channels = [
        ChannelType(
            id=c.id,
            name=c.name,
            display_name=c.display_name,
            description=c.description,
            channel_type=c.channel_type,
            spend_column=c.spend_column,
            impression_column=c.impression_column,
            click_column=c.click_column,
            default_adstock_type=c.default_adstock_type or "geometric",
            default_saturation_type=c.default_saturation_type or "hill",
            dataset_id=c.dataset_id,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in dataset.channels
    ]

    metrics = [
        MetricType(
            id=m.id,
            name=m.name,
            display_name=m.display_name,
            description=m.description,
            metric_type=m.metric_type,
            column_name=m.column_name,
            aggregation_method=m.aggregation_method or "sum",
            is_target=m.is_target or False,
            dataset_id=m.dataset_id,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )
        for m in dataset.metrics
    ]

    # Extract column names from schema definition
    # Schema can be stored as {"columns": [...]} or as {col_name: type, ...}
    column_names = []
    if dataset.schema_definition:
        if "columns" in dataset.schema_definition:
            # New format: {"columns": ["col1", "col2", ...]}
            column_names = dataset.schema_definition["columns"]
        else:
            # Legacy format: {"col1": "type1", "col2": "type2", ...}
            column_names = list(dataset.schema_definition.keys())

    return DatasetType(
        id=dataset.id,
        name=dataset.name,
        description=dataset.description,
        is_active=dataset.is_active,
        row_count=dataset.row_count,
        column_count=dataset.column_count,
        file_size_bytes=dataset.file_size_bytes,
        start_date=dataset.start_date,
        end_date=dataset.end_date,
        time_granularity=dataset.time_granularity,
        storage_format=dataset.storage_format,
        column_names=column_names,
        channels=channels,
        metrics=metrics,
        created_at=dataset.created_at,
        updated_at=dataset.updated_at,
    )


@strawberry.input
class UpdateDatasetInput:
    """Input for updating a dataset."""

    name: Optional[str] = None
    description: Optional[str] = None
    time_granularity: Optional[str] = None
    is_active: Optional[bool] = None


@strawberry.type
class DatasetMutation:
    """Dataset management mutations."""

    @strawberry.mutation
    async def create_dataset(
        self,
        info: Info,
        input: CreateDatasetInput,
    ) -> DatasetType:
        """Create a new dataset from an uploaded file."""
        db = await get_db_session(info)
        user = await get_current_user_from_context(info, db)

        # Validate input
        if not input.name or len(input.name.strip()) == 0:
            raise ValidationError("Dataset name is required")

        # Create dataset
        dataset = Dataset(
            id=uuid4(),
            name=input.name.strip(),
            description=input.description,
            organization_id=user.organization_id,
            time_granularity=input.time_granularity or "daily",
            storage_format="parquet",
            schema_definition={
                input.time_column: "datetime",
                input.target_column: "numeric",
            },
            extra_metadata={
                "file_id": input.file_id,
                "time_column": input.time_column,
                "target_column": input.target_column,
            },
        )
        db.add(dataset)

        # Create target metric
        target_metric = Metric(
            id=uuid4(),
            name=input.target_column,
            display_name=input.target_column.replace("_", " ").title(),
            metric_type="revenue",
            column_name=input.target_column,
            aggregation_method="sum",
            is_target=True,
            dataset_id=dataset.id,
        )
        db.add(target_metric)

        await db.commit()
        await db.refresh(dataset)

        logger.info(
            "Dataset created",
            dataset_id=str(dataset.id),
            user_id=str(user.id),
            name=dataset.name,
        )

        return dataset_to_graphql(dataset)

    @strawberry.mutation
    async def update_dataset(
        self,
        info: Info,
        id: UUID,
        input: UpdateDatasetInput,
    ) -> DatasetType:
        """Update an existing dataset."""
        db = await get_db_session(info)
        user = await get_current_user_from_context(info, db)

        # Get dataset
        result = await db.execute(
            select(Dataset).where(
                Dataset.id == id,
                Dataset.organization_id == user.organization_id,
            )
        )
        dataset = result.scalar_one_or_none()

        if not dataset:
            raise NotFoundError("Dataset", str(id))

        # Update fields
        if input.name is not None:
            if len(input.name.strip()) == 0:
                raise ValidationError("Dataset name cannot be empty")
            dataset.name = input.name.strip()

        if input.description is not None:
            dataset.description = input.description

        if input.time_granularity is not None:
            if input.time_granularity not in ["daily", "weekly", "monthly"]:
                raise ValidationError("Invalid time granularity. Must be daily, weekly, or monthly")
            dataset.time_granularity = input.time_granularity

        if input.is_active is not None:
            dataset.is_active = input.is_active

        await db.commit()
        await db.refresh(dataset)

        logger.info(
            "Dataset updated",
            dataset_id=str(dataset.id),
            user_id=str(user.id),
        )

        return dataset_to_graphql(dataset)

    @strawberry.mutation
    async def delete_dataset(
        self,
        info: Info,
        id: UUID,
    ) -> bool:
        """Delete a dataset (soft delete by setting is_active=False)."""
        db = await get_db_session(info)
        user = await get_current_user_from_context(info, db)

        # Get dataset
        result = await db.execute(
            select(Dataset).where(
                Dataset.id == id,
                Dataset.organization_id == user.organization_id,
            )
        )
        dataset = result.scalar_one_or_none()

        if not dataset:
            raise NotFoundError("Dataset", str(id))

        # Soft delete
        dataset.is_active = False

        await db.commit()

        logger.info(
            "Dataset deleted",
            dataset_id=str(dataset.id),
            user_id=str(user.id),
        )

        return True
