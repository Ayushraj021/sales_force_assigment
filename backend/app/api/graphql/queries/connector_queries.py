"""Data connector queries."""

from typing import Optional
from uuid import UUID

import strawberry
import structlog
from sqlalchemy import select
from strawberry.types import Info

from app.api.graphql.context import get_db_session, get_current_user_from_context
from app.api.graphql.types.data import DataSourceType
from app.core.exceptions import NotFoundError
from app.infrastructure.database.models.dataset import DataSource

logger = structlog.get_logger()


def data_source_to_graphql(source: DataSource) -> DataSourceType:
    """Convert database data source to GraphQL type."""
    return DataSourceType(
        id=source.id,
        name=source.name,
        description=source.description,
        source_type=source.source_type,
        is_active=source.is_active,
        created_at=source.created_at,
        updated_at=source.updated_at,
    )


@strawberry.type
class ConnectorQuery:
    """Data connector queries."""

    @strawberry.field
    async def data_connectors(
        self,
        info: Info,
        source_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DataSourceType]:
        """Get all data connectors for the organization."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        query = select(DataSource).where(
            DataSource.organization_id == current_user.organization_id
        )

        # Apply filters
        if source_type is not None:
            query = query.where(DataSource.source_type == source_type)

        if is_active is not None:
            query = query.where(DataSource.is_active == is_active)

        # Order and paginate
        query = query.order_by(DataSource.created_at.desc()).offset(offset).limit(limit)

        result = await db.execute(query)
        connectors = result.scalars().all()

        return [data_source_to_graphql(c) for c in connectors]

    @strawberry.field
    async def data_connector(
        self,
        info: Info,
        connector_id: UUID,
    ) -> DataSourceType:
        """Get a specific data connector by ID."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        result = await db.execute(
            select(DataSource).where(
                DataSource.id == connector_id,
                DataSource.organization_id == current_user.organization_id,
            )
        )
        connector = result.scalar_one_or_none()

        if not connector:
            raise NotFoundError("Data connector", str(connector_id))

        return data_source_to_graphql(connector)

    @strawberry.field
    async def connector_types(self) -> list[str]:
        """Get list of available connector types."""
        return [
            "google_ads",
            "meta_ads",
            "bigquery",
            "snowflake",
            "redshift",
            "databricks",
            "salesforce",
            "hubspot",
            "google_analytics",
            "file",
            "api",
            "database",
        ]
