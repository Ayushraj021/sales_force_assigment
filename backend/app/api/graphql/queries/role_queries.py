"""Role and Permission queries."""

from typing import Optional
from uuid import UUID

import strawberry
import structlog
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from strawberry.types import Info

from app.api.graphql.context import get_db_session, get_current_user_from_context
from app.api.graphql.types.auth import PermissionType, RoleType
from app.core.exceptions import NotFoundError
from app.infrastructure.database.models.user import Permission, Role

logger = structlog.get_logger()


def permission_to_graphql(permission: Permission) -> PermissionType:
    """Convert permission to GraphQL type."""
    return PermissionType(
        id=permission.id,
        name=permission.name,
        description=permission.description,
        resource=permission.resource,
        action=permission.action,
    )


def role_to_graphql(role: Role) -> RoleType:
    """Convert role to GraphQL type."""
    return RoleType(
        id=role.id,
        name=role.name,
        description=role.description,
        is_default=role.is_default,
        permissions=[permission_to_graphql(p) for p in role.permissions],
        created_at=role.created_at,
        updated_at=role.updated_at,
    )


@strawberry.type
class RoleQuery:
    """Role and Permission queries."""

    @strawberry.field
    async def roles(
        self,
        info: Info,
        is_default: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[RoleType]:
        """Get all roles."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        query = select(Role).options(selectinload(Role.permissions))

        # Non-superusers only see global roles and their org's roles
        if not current_user.is_superuser:
            query = query.where(
                (Role.organization_id == None) |
                (Role.organization_id == current_user.organization_id)
            )

        if is_default is not None:
            query = query.where(Role.is_default == is_default)

        query = query.order_by(Role.name).offset(offset).limit(limit)

        result = await db.execute(query)
        roles = result.scalars().all()

        return [role_to_graphql(r) for r in roles]

    @strawberry.field
    async def role(
        self,
        info: Info,
        role_id: UUID,
    ) -> RoleType:
        """Get a specific role by ID."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        result = await db.execute(
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.id == role_id)
        )
        role = result.scalar_one_or_none()

        if not role:
            raise NotFoundError("Role", str(role_id))

        # Non-superusers can only view global roles and their org's roles
        if not current_user.is_superuser:
            if role.organization_id and role.organization_id != current_user.organization_id:
                raise NotFoundError("Role", str(role_id))

        return role_to_graphql(role)

    @strawberry.field
    async def permissions(
        self,
        info: Info,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PermissionType]:
        """Get all permissions."""
        db = await get_db_session(info)
        await get_current_user_from_context(info, db)

        query = select(Permission)

        if resource is not None:
            query = query.where(Permission.resource == resource)

        if action is not None:
            query = query.where(Permission.action == action)

        query = query.order_by(Permission.resource, Permission.action).offset(offset).limit(limit)

        result = await db.execute(query)
        permissions = result.scalars().all()

        return [permission_to_graphql(p) for p in permissions]

    @strawberry.field
    async def permission(
        self,
        info: Info,
        permission_id: UUID,
    ) -> PermissionType:
        """Get a specific permission by ID."""
        db = await get_db_session(info)
        await get_current_user_from_context(info, db)

        result = await db.execute(
            select(Permission).where(Permission.id == permission_id)
        )
        permission = result.scalar_one_or_none()

        if not permission:
            raise NotFoundError("Permission", str(permission_id))

        return permission_to_graphql(permission)
