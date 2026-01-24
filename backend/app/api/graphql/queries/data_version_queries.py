"""DataVersion queries."""

from typing import Optional
from uuid import UUID

import strawberry
import structlog
from sqlalchemy import select
from strawberry.types import Info

from app.api.graphql.context import get_db_session, get_current_user_from_context
from app.api.graphql.types.data_version import (
    DataVersionComparisonType,
    DataVersionFilterInput,
    DataVersionType,
)
from app.core.exceptions import NotFoundError
from app.infrastructure.database.models.dataset import Dataset, DataVersion

logger = structlog.get_logger()


def data_version_to_graphql(version: DataVersion) -> DataVersionType:
    """Convert data version to GraphQL type."""
    return DataVersionType(
        id=version.id,
        version=version.version,
        description=version.description,
        is_current=version.is_current or False,
        dvc_hash=version.dvc_hash,
        dvc_path=version.dvc_path,
        changes_summary=version.changes_summary or {},
        row_count=version.row_count,
        checksum=version.checksum,
        dataset_id=version.dataset_id,
        created_at=version.created_at,
        updated_at=version.updated_at,
    )


@strawberry.type
class DataVersionQuery:
    """DataVersion queries (read-only for compliance)."""

    @strawberry.field
    async def data_versions(
        self,
        info: Info,
        filter: Optional[DataVersionFilterInput] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DataVersionType]:
        """Get data versions for the organization's datasets."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        query = (
            select(DataVersion)
            .join(Dataset)
            .where(Dataset.organization_id == current_user.organization_id)
        )

        # Apply filters
        if filter:
            if filter.dataset_id:
                query = query.where(DataVersion.dataset_id == filter.dataset_id)
            if filter.is_current is not None:
                query = query.where(DataVersion.is_current == filter.is_current)

        # Order by creation date descending and paginate
        query = query.order_by(DataVersion.created_at.desc()).offset(offset).limit(limit)

        result = await db.execute(query)
        versions = result.scalars().all()

        return [data_version_to_graphql(v) for v in versions]

    @strawberry.field
    async def data_version(
        self,
        info: Info,
        version_id: UUID,
    ) -> DataVersionType:
        """Get a specific data version by ID."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        result = await db.execute(
            select(DataVersion)
            .join(Dataset)
            .where(
                DataVersion.id == version_id,
                Dataset.organization_id == current_user.organization_id,
            )
        )
        version = result.scalar_one_or_none()

        if not version:
            raise NotFoundError("Data version", str(version_id))

        return data_version_to_graphql(version)

    @strawberry.field
    async def dataset_versions(
        self,
        info: Info,
        dataset_id: UUID,
    ) -> list[DataVersionType]:
        """Get all versions for a specific dataset."""
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
            select(DataVersion)
            .where(DataVersion.dataset_id == dataset_id)
            .order_by(DataVersion.created_at.desc())
        )
        versions = result.scalars().all()

        return [data_version_to_graphql(v) for v in versions]

    @strawberry.field
    async def current_dataset_version(
        self,
        info: Info,
        dataset_id: UUID,
    ) -> Optional[DataVersionType]:
        """Get the current version for a dataset."""
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
            select(DataVersion).where(
                DataVersion.dataset_id == dataset_id,
                DataVersion.is_current == True,
            )
        )
        version = result.scalar_one_or_none()

        if not version:
            return None

        return data_version_to_graphql(version)

    @strawberry.field
    async def compare_versions(
        self,
        info: Info,
        from_version_id: UUID,
        to_version_id: UUID,
    ) -> DataVersionComparisonType:
        """Compare two data versions."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Get from version
        result = await db.execute(
            select(DataVersion)
            .join(Dataset)
            .where(
                DataVersion.id == from_version_id,
                Dataset.organization_id == current_user.organization_id,
            )
        )
        from_version = result.scalar_one_or_none()

        if not from_version:
            raise NotFoundError("Data version", str(from_version_id))

        # Get to version
        result = await db.execute(
            select(DataVersion)
            .join(Dataset)
            .where(
                DataVersion.id == to_version_id,
                Dataset.organization_id == current_user.organization_id,
            )
        )
        to_version = result.scalar_one_or_none()

        if not to_version:
            raise NotFoundError("Data version", str(to_version_id))

        # Verify both versions belong to same dataset
        if from_version.dataset_id != to_version.dataset_id:
            raise ValueError("Versions must belong to the same dataset")

        # Calculate differences
        from_rows = from_version.row_count or 0
        to_rows = to_version.row_count or 0
        row_count_diff = to_rows - from_rows

        # Build comparison summary
        changes_summary = {
            "from_version": from_version.version,
            "to_version": to_version.version,
            "row_count_change": row_count_diff,
            "row_count_change_pct": (
                round((row_count_diff / from_rows) * 100, 2) if from_rows > 0 else 0
            ),
            "from_checksum": from_version.checksum,
            "to_checksum": to_version.checksum,
            "checksums_match": from_version.checksum == to_version.checksum,
        }

        return DataVersionComparisonType(
            from_version=data_version_to_graphql(from_version),
            to_version=data_version_to_graphql(to_version),
            row_count_diff=row_count_diff,
            changes_summary=changes_summary,
        )

    @strawberry.field
    async def version_history_summary(
        self,
        info: Info,
        dataset_id: UUID,
    ) -> strawberry.scalars.JSON:
        """Get summary of version history for a dataset."""
        from sqlalchemy import func

        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Verify dataset access
        result = await db.execute(
            select(Dataset).where(
                Dataset.id == dataset_id,
                Dataset.organization_id == current_user.organization_id,
            )
        )
        dataset = result.scalar_one_or_none()
        if not dataset:
            raise NotFoundError("Dataset", str(dataset_id))

        # Get version count
        count_result = await db.execute(
            select(func.count(DataVersion.id)).where(
                DataVersion.dataset_id == dataset_id
            )
        )
        version_count = count_result.scalar() or 0

        # Get first and latest versions
        first_result = await db.execute(
            select(DataVersion)
            .where(DataVersion.dataset_id == dataset_id)
            .order_by(DataVersion.created_at.asc())
            .limit(1)
        )
        first_version = first_result.scalar_one_or_none()

        latest_result = await db.execute(
            select(DataVersion)
            .where(DataVersion.dataset_id == dataset_id)
            .order_by(DataVersion.created_at.desc())
            .limit(1)
        )
        latest_version = latest_result.scalar_one_or_none()

        # Get current version
        current_result = await db.execute(
            select(DataVersion).where(
                DataVersion.dataset_id == dataset_id,
                DataVersion.is_current == True,
            )
        )
        current_version = current_result.scalar_one_or_none()

        return {
            "dataset_id": str(dataset_id),
            "dataset_name": dataset.name,
            "total_versions": version_count,
            "first_version": first_version.version if first_version else None,
            "first_version_date": first_version.created_at.isoformat() if first_version else None,
            "latest_version": latest_version.version if latest_version else None,
            "latest_version_date": latest_version.created_at.isoformat() if latest_version else None,
            "current_version": current_version.version if current_version else None,
            "current_version_id": str(current_version.id) if current_version else None,
        }
