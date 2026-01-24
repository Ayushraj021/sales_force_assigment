"""User and authentication queries."""

from typing import Optional
from uuid import UUID

import strawberry
from sqlalchemy import select
from strawberry.types import Info

from app.api.graphql.context import get_db_session, get_current_user_from_context
from app.api.graphql.mutations.auth_mutations import user_to_graphql
from app.api.graphql.types.auth import UserType, OrganizationType
from app.core.exceptions import NotFoundError
from app.infrastructure.database.models.organization import Organization
from app.infrastructure.database.models.user import User


@strawberry.type
class UserQuery:
    """User queries."""

    @strawberry.field
    async def me(self, info: Info) -> UserType:
        """Get current authenticated user."""
        db = await get_db_session(info)
        user = await get_current_user_from_context(info, db)
        return user_to_graphql(user)

    @strawberry.field
    async def user(self, info: Info, id: UUID) -> UserType:
        """Get a user by ID."""
        db = await get_db_session(info)
        await get_current_user_from_context(info, db)  # Auth check

        result = await db.execute(select(User).where(User.id == id))
        user = result.scalar_one_or_none()

        if not user:
            raise NotFoundError("User", str(id))

        return user_to_graphql(user)

    @strawberry.field
    async def users(
        self,
        info: Info,
        limit: int = 50,
        offset: int = 0,
    ) -> list[UserType]:
        """Get list of users."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Only show users from same organization
        query = select(User)
        if current_user.organization_id:
            query = query.where(User.organization_id == current_user.organization_id)

        query = query.limit(limit).offset(offset)
        result = await db.execute(query)
        users = result.scalars().all()

        return [user_to_graphql(u) for u in users]

    @strawberry.field
    async def organization(
        self,
        info: Info,
        id: Optional[UUID] = None,
    ) -> OrganizationType:
        """Get organization by ID or current user's organization."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        org_id = id or current_user.organization_id
        if not org_id:
            raise NotFoundError("Organization", "current user has no organization")

        result = await db.execute(
            select(Organization).where(Organization.id == org_id)
        )
        org = result.scalar_one_or_none()

        if not org:
            raise NotFoundError("Organization", str(org_id))

        return OrganizationType(
            id=org.id,
            name=org.name,
            slug=org.slug,
            description=org.description,
            is_active=org.is_active,
            subscription_tier=org.subscription_tier,
            max_users=org.max_users,
            max_models=org.max_models,
            max_datasets=org.max_datasets,
            created_at=org.created_at,
            updated_at=org.updated_at,
        )
