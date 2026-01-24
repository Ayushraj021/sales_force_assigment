"""API Key queries."""

from typing import Optional
from uuid import UUID

import strawberry
import structlog
from sqlalchemy import select
from strawberry.types import Info

from app.api.graphql.context import get_db_session, get_current_user_from_context
from app.api.graphql.types.api_key import APIKeyType
from app.core.exceptions import NotFoundError
from app.infrastructure.database.models.api_key import APIKey

logger = structlog.get_logger()


def api_key_to_graphql(api_key: APIKey) -> APIKeyType:
    """Convert API key to GraphQL type."""
    return APIKeyType(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        description=api_key.description,
        is_active=api_key.is_active,
        expires_at=api_key.expires_at,
        last_used_at=api_key.last_used_at,
        scopes=api_key.scopes or [],
        rate_limit_requests=api_key.rate_limit_requests,
        rate_limit_period=api_key.rate_limit_period,
        created_at=api_key.created_at,
        updated_at=api_key.updated_at,
    )


@strawberry.type
class APIKeyQuery:
    """API Key queries."""

    @strawberry.field
    async def api_keys(
        self,
        info: Info,
        is_active: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[APIKeyType]:
        """Get all API keys for the current user."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        query = select(APIKey).where(APIKey.user_id == current_user.id)

        if is_active is not None:
            query = query.where(APIKey.is_active == is_active)

        query = query.order_by(APIKey.created_at.desc()).offset(offset).limit(limit)

        result = await db.execute(query)
        api_keys = result.scalars().all()

        return [api_key_to_graphql(k) for k in api_keys]

    @strawberry.field
    async def api_key(
        self,
        info: Info,
        api_key_id: UUID,
    ) -> APIKeyType:
        """Get a specific API key by ID."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        result = await db.execute(
            select(APIKey).where(
                APIKey.id == api_key_id,
                APIKey.user_id == current_user.id,
            )
        )
        api_key = result.scalar_one_or_none()

        if not api_key:
            raise NotFoundError("API key", str(api_key_id))

        return api_key_to_graphql(api_key)

    @strawberry.field
    async def api_key_scopes(self) -> list[str]:
        """Get list of available API key scopes."""
        return [
            "*",
            "read",
            "write",
            "models:read",
            "models:write",
            "datasets:read",
            "datasets:write",
            "forecasts:read",
            "forecasts:write",
            "reports:read",
            "reports:write",
        ]
