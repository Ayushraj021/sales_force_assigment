"""API Key management mutations."""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import strawberry
import structlog
from sqlalchemy import select
from strawberry.types import Info

from app.api.graphql.context import get_db_session, get_current_user_from_context
from app.api.graphql.types.api_key import (
    APIKeyCreatedType,
    APIKeyType,
    CreateAPIKeyInput,
    UpdateAPIKeyInput,
)
from app.core.exceptions import NotFoundError, ValidationError
from app.core.security.password import get_password_hash
from app.infrastructure.database.models.api_key import APIKey, generate_api_key

logger = structlog.get_logger()

# Valid API scopes
VALID_SCOPES = {
    "*",  # All access
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
}


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
class APIKeyMutation:
    """API Key management mutations."""

    @strawberry.mutation
    async def create_api_key(
        self,
        info: Info,
        input: CreateAPIKeyInput,
    ) -> APIKeyCreatedType:
        """Create a new API key."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Validate name
        if not input.name or len(input.name.strip()) == 0:
            raise ValidationError("API key name is required")

        # Validate scopes
        if input.scopes:
            invalid_scopes = set(input.scopes) - VALID_SCOPES
            if invalid_scopes:
                raise ValidationError(
                    f"Invalid scopes: {', '.join(invalid_scopes)}. "
                    f"Valid scopes: {', '.join(sorted(VALID_SCOPES))}"
                )

        # Generate API key
        raw_key = generate_api_key()
        key_hash = await get_password_hash(raw_key)
        key_prefix = raw_key[:10]  # First 10 chars for identification

        # Calculate expiration
        expires_at = None
        if input.expires_in_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=input.expires_in_days)

        # Create API key
        api_key = APIKey(
            id=uuid4(),
            name=input.name.strip(),
            key_hash=key_hash,
            key_prefix=key_prefix,
            description=input.description,
            is_active=True,
            expires_at=expires_at,
            scopes=input.scopes or ["*"],
            rate_limit_requests=input.rate_limit_requests,
            rate_limit_period=input.rate_limit_period,
            user_id=current_user.id,
        )
        db.add(api_key)

        await db.commit()
        await db.refresh(api_key)

        logger.info(
            "API key created",
            api_key_id=str(api_key.id),
            key_prefix=key_prefix,
            created_by=str(current_user.id),
        )

        # Return with full key (only time it's visible)
        return APIKeyCreatedType(
            id=api_key.id,
            name=api_key.name,
            key=raw_key,
            key_prefix=api_key.key_prefix,
            description=api_key.description,
            expires_at=api_key.expires_at,
            scopes=api_key.scopes or [],
            created_at=api_key.created_at,
        )

    @strawberry.mutation
    async def update_api_key(
        self,
        info: Info,
        api_key_id: UUID,
        input: UpdateAPIKeyInput,
    ) -> APIKeyType:
        """Update an API key."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Get API key
        result = await db.execute(
            select(APIKey).where(
                APIKey.id == api_key_id,
                APIKey.user_id == current_user.id,
            )
        )
        api_key = result.scalar_one_or_none()

        if not api_key:
            raise NotFoundError("API key", str(api_key_id))

        # Update fields
        if input.name is not None:
            if len(input.name.strip()) == 0:
                raise ValidationError("API key name cannot be empty")
            api_key.name = input.name.strip()

        if input.description is not None:
            api_key.description = input.description

        if input.is_active is not None:
            api_key.is_active = input.is_active

        if input.scopes is not None:
            invalid_scopes = set(input.scopes) - VALID_SCOPES
            if invalid_scopes:
                raise ValidationError(f"Invalid scopes: {', '.join(invalid_scopes)}")
            api_key.scopes = input.scopes

        if input.rate_limit_requests is not None:
            api_key.rate_limit_requests = input.rate_limit_requests

        if input.rate_limit_period is not None:
            api_key.rate_limit_period = input.rate_limit_period

        await db.commit()
        await db.refresh(api_key)

        logger.info(
            "API key updated",
            api_key_id=str(api_key.id),
            updated_by=str(current_user.id),
        )

        return api_key_to_graphql(api_key)

    @strawberry.mutation
    async def revoke_api_key(
        self,
        info: Info,
        api_key_id: UUID,
    ) -> bool:
        """Revoke an API key."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Get API key
        result = await db.execute(
            select(APIKey).where(
                APIKey.id == api_key_id,
                APIKey.user_id == current_user.id,
            )
        )
        api_key = result.scalar_one_or_none()

        if not api_key:
            raise NotFoundError("API key", str(api_key_id))

        # Revoke (deactivate)
        api_key.is_active = False

        await db.commit()

        logger.info(
            "API key revoked",
            api_key_id=str(api_key.id),
            revoked_by=str(current_user.id),
        )

        return True

    @strawberry.mutation
    async def delete_api_key(
        self,
        info: Info,
        api_key_id: UUID,
    ) -> bool:
        """Permanently delete an API key."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Get API key
        result = await db.execute(
            select(APIKey).where(
                APIKey.id == api_key_id,
                APIKey.user_id == current_user.id,
            )
        )
        api_key = result.scalar_one_or_none()

        if not api_key:
            raise NotFoundError("API key", str(api_key_id))

        await db.delete(api_key)
        await db.commit()

        logger.info(
            "API key deleted",
            api_key_id=str(api_key_id),
            deleted_by=str(current_user.id),
        )

        return True
