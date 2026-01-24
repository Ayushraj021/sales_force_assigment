"""Role and Permission management mutations."""

from uuid import UUID, uuid4

import strawberry
import structlog
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from strawberry.types import Info

from app.api.graphql.context import get_db_session, get_current_user_from_context
from app.api.graphql.types.auth import PermissionType, RoleType
from app.api.graphql.types.role import (
    CreatePermissionInput,
    CreateRoleInput,
    UpdateRoleInput,
)
from app.core.exceptions import NotFoundError, ValidationError, AuthorizationError
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
class RoleMutation:
    """Role and Permission management mutations."""

    @strawberry.mutation
    async def create_role(
        self,
        info: Info,
        input: CreateRoleInput,
    ) -> RoleType:
        """Create a new role (admin only)."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Check admin permission
        if not current_user.is_superuser and not current_user.has_role("admin"):
            raise AuthorizationError("Only admins can create roles")

        # Validate name
        if not input.name or len(input.name.strip()) == 0:
            raise ValidationError("Role name is required")

        # Check for duplicate name
        result = await db.execute(
            select(Role).where(Role.name == input.name.strip())
        )
        if result.scalar_one_or_none():
            raise ValidationError(f"Role '{input.name}' already exists")

        # Create role
        role = Role(
            id=uuid4(),
            name=input.name.strip(),
            description=input.description,
            is_default=input.is_default,
            organization_id=current_user.organization_id,
        )
        db.add(role)

        # Add permissions if provided
        if input.permission_ids:
            result = await db.execute(
                select(Permission).where(Permission.id.in_(input.permission_ids))
            )
            permissions = result.scalars().all()
            role.permissions = list(permissions)

        await db.commit()

        # Reload with permissions
        result = await db.execute(
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.id == role.id)
        )
        role = result.scalar_one()

        logger.info(
            "Role created",
            role_id=str(role.id),
            role_name=role.name,
            created_by=str(current_user.id),
        )

        return role_to_graphql(role)

    @strawberry.mutation
    async def update_role(
        self,
        info: Info,
        role_id: UUID,
        input: UpdateRoleInput,
    ) -> RoleType:
        """Update a role (admin only)."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Check admin permission
        if not current_user.is_superuser and not current_user.has_role("admin"):
            raise AuthorizationError("Only admins can update roles")

        # Get role
        result = await db.execute(
            select(Role)
            .options(selectinload(Role.permissions))
            .where(Role.id == role_id)
        )
        role = result.scalar_one_or_none()

        if not role:
            raise NotFoundError("Role", str(role_id))

        # Non-superusers can only update roles in their organization
        if not current_user.is_superuser and role.organization_id != current_user.organization_id:
            raise AuthorizationError("You can only update roles in your organization")

        # Update fields
        if input.name is not None:
            if len(input.name.strip()) == 0:
                raise ValidationError("Role name cannot be empty")

            # Check for duplicate name
            result = await db.execute(
                select(Role).where(
                    Role.name == input.name.strip(),
                    Role.id != role_id,
                )
            )
            if result.scalar_one_or_none():
                raise ValidationError(f"Role '{input.name}' already exists")

            role.name = input.name.strip()

        if input.description is not None:
            role.description = input.description

        if input.is_default is not None:
            # If setting as default, unset other defaults
            if input.is_default:
                result = await db.execute(
                    select(Role).where(Role.is_default == True, Role.id != role_id)
                )
                for other_role in result.scalars().all():
                    other_role.is_default = False
            role.is_default = input.is_default

        if input.permission_ids is not None:
            result = await db.execute(
                select(Permission).where(Permission.id.in_(input.permission_ids))
            )
            permissions = result.scalars().all()
            role.permissions = list(permissions)

        await db.commit()
        await db.refresh(role)

        logger.info(
            "Role updated",
            role_id=str(role.id),
            updated_by=str(current_user.id),
        )

        return role_to_graphql(role)

    @strawberry.mutation
    async def delete_role(
        self,
        info: Info,
        role_id: UUID,
    ) -> bool:
        """Delete a role (admin only)."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Check admin permission
        if not current_user.is_superuser and not current_user.has_role("admin"):
            raise AuthorizationError("Only admins can delete roles")

        # Get role
        result = await db.execute(
            select(Role)
            .options(selectinload(Role.users))
            .where(Role.id == role_id)
        )
        role = result.scalar_one_or_none()

        if not role:
            raise NotFoundError("Role", str(role_id))

        # Non-superusers can only delete roles in their organization
        if not current_user.is_superuser and role.organization_id != current_user.organization_id:
            raise AuthorizationError("You can only delete roles in your organization")

        # Prevent deleting roles that are in use
        if role.users:
            raise ValidationError(
                f"Cannot delete role '{role.name}' - it is assigned to {len(role.users)} user(s)"
            )

        await db.delete(role)
        await db.commit()

        logger.info(
            "Role deleted",
            role_id=str(role_id),
            deleted_by=str(current_user.id),
        )

        return True

    @strawberry.mutation
    async def create_permission(
        self,
        info: Info,
        input: CreatePermissionInput,
    ) -> PermissionType:
        """Create a new permission (superuser only)."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Only superusers can create permissions
        if not current_user.is_superuser:
            raise AuthorizationError("Only superusers can create permissions")

        # Validate name
        if not input.name or len(input.name.strip()) == 0:
            raise ValidationError("Permission name is required")

        # Check for duplicate name
        result = await db.execute(
            select(Permission).where(Permission.name == input.name.strip())
        )
        if result.scalar_one_or_none():
            raise ValidationError(f"Permission '{input.name}' already exists")

        # Create permission
        permission = Permission(
            id=uuid4(),
            name=input.name.strip(),
            description=input.description,
            resource=input.resource,
            action=input.action,
        )
        db.add(permission)

        await db.commit()
        await db.refresh(permission)

        logger.info(
            "Permission created",
            permission_id=str(permission.id),
            permission_name=permission.name,
            created_by=str(current_user.id),
        )

        return permission_to_graphql(permission)
