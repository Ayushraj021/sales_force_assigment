"""User management mutations for admins."""

from typing import Optional
from uuid import UUID, uuid4

import strawberry
import structlog
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from strawberry.types import Info

from app.api.graphql.context import get_db_session, get_current_user_from_context
from app.api.graphql.mutations.auth_mutations import user_to_graphql
from app.api.graphql.types.auth import UserType
from app.core.exceptions import NotFoundError, ValidationError, ConflictError, AuthorizationError
from app.core.security.password import get_password_hash
from app.infrastructure.database.models.user import User, Role
from app.infrastructure.database.models.organization import Organization

logger = structlog.get_logger()


@strawberry.input
class CreateUserInput:
    """Input for creating/inviting a new user."""

    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role_id: Optional[UUID] = None
    send_invite: bool = True


@strawberry.input
class AdminUpdateUserInput:
    """Input for admin updating a user."""

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role_id: Optional[UUID] = None
    is_active: Optional[bool] = None


@strawberry.type
class UserMutation:
    """User management mutations (admin only)."""

    @strawberry.mutation
    async def create_user(
        self,
        info: Info,
        input: CreateUserInput,
    ) -> UserType:
        """Create/invite a new user to the organization (admin only)."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Check if user has admin permissions
        if not current_user.is_superuser and not current_user.has_role("admin"):
            raise AuthorizationError("Only admins can create users")

        # Validate email
        if not input.email or "@" not in input.email:
            raise ValidationError("Invalid email address")

        # Check if email already exists
        result = await db.execute(
            select(User).where(User.email == input.email.lower())
        )
        if result.scalar_one_or_none():
            raise ConflictError("A user with this email already exists")

        # Check organization user limit
        if current_user.organization:
            result = await db.execute(
                select(Organization)
                .options(selectinload(Organization.users))
                .where(Organization.id == current_user.organization_id)
            )
            org = result.scalar_one_or_none()
            if org and not org.can_add_user():
                raise ValidationError(
                    f"Organization has reached its user limit ({org.max_users}). "
                    "Please upgrade your subscription."
                )

        # Generate temporary password for invited user
        temp_password = uuid4().hex[:12]

        # Create user
        new_user = User(
            id=uuid4(),
            email=input.email.lower(),
            hashed_password=await get_password_hash(temp_password),
            first_name=input.first_name,
            last_name=input.last_name,
            organization_id=current_user.organization_id,
            is_active=True,
            is_verified=False,
        )
        db.add(new_user)

        # Assign role if provided
        if input.role_id:
            result = await db.execute(
                select(Role).where(Role.id == input.role_id)
            )
            role = result.scalar_one_or_none()
            if role:
                new_user.roles.append(role)
        else:
            # Assign default role
            result = await db.execute(
                select(Role).where(Role.is_default == True)
            )
            default_role = result.scalar_one_or_none()
            if default_role:
                new_user.roles.append(default_role)

        await db.commit()

        # Re-fetch user with relationships for GraphQL response
        result = await db.execute(
            select(User)
            .where(User.id == new_user.id)
            .options(
                selectinload(User.organization),
                selectinload(User.roles).selectinload(Role.permissions),
            )
        )
        new_user = result.scalar_one()

        logger.info(
            "User created",
            user_id=str(new_user.id),
            email=new_user.email,
            created_by=str(current_user.id),
        )

        # TODO: Send invite email if send_invite is True
        # if input.send_invite:
        #     from app.services.email import send_invite_email
        #     await send_invite_email(new_user.email, temp_password)

        return user_to_graphql(new_user)

    @strawberry.mutation
    async def admin_update_user(
        self,
        info: Info,
        user_id: UUID,
        input: AdminUpdateUserInput,
    ) -> UserType:
        """Update a user's details (admin only)."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Check if user has admin permissions
        if not current_user.is_superuser and not current_user.has_role("admin"):
            raise AuthorizationError("Only admins can update users")

        # Get target user
        query = (
            select(User)
            .options(
                selectinload(User.organization),
                selectinload(User.roles).selectinload(Role.permissions),
            )
            .where(User.id == user_id)
        )

        # Non-superusers can only update users in their organization
        if not current_user.is_superuser:
            query = query.where(User.organization_id == current_user.organization_id)

        result = await db.execute(query)
        target_user = result.scalar_one_or_none()

        if not target_user:
            raise NotFoundError("User", str(user_id))

        # Prevent demoting yourself
        if target_user.id == current_user.id and input.is_active == False:
            raise ValidationError("You cannot deactivate your own account")

        # Update fields
        if input.first_name is not None:
            target_user.first_name = input.first_name

        if input.last_name is not None:
            target_user.last_name = input.last_name

        if input.is_active is not None:
            # Prevent deactivating superusers unless you're a superuser
            if target_user.is_superuser and not current_user.is_superuser:
                raise AuthorizationError("Cannot modify superuser accounts")
            target_user.is_active = input.is_active

        # Update role if provided
        if input.role_id is not None:
            result = await db.execute(
                select(Role).where(Role.id == input.role_id)
            )
            role = result.scalar_one_or_none()
            if not role:
                raise NotFoundError("Role", str(input.role_id))

            # Clear existing roles and assign new one
            target_user.roles = [role]

        await db.commit()

        # Re-fetch user with relationships for GraphQL response
        result = await db.execute(
            select(User)
            .where(User.id == target_user.id)
            .options(
                selectinload(User.organization),
                selectinload(User.roles).selectinload(Role.permissions),
            )
        )
        target_user = result.scalar_one()

        logger.info(
            "User updated by admin",
            user_id=str(target_user.id),
            updated_by=str(current_user.id),
        )

        return user_to_graphql(target_user)

    @strawberry.mutation
    async def delete_user(
        self,
        info: Info,
        user_id: UUID,
    ) -> bool:
        """Delete/deactivate a user (admin only)."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Check if user has admin permissions
        if not current_user.is_superuser and not current_user.has_role("admin"):
            raise AuthorizationError("Only admins can delete users")

        # Get target user
        query = select(User).where(User.id == user_id)

        # Non-superusers can only delete users in their organization
        if not current_user.is_superuser:
            query = query.where(User.organization_id == current_user.organization_id)

        result = await db.execute(query)
        target_user = result.scalar_one_or_none()

        if not target_user:
            raise NotFoundError("User", str(user_id))

        # Prevent deleting yourself
        if target_user.id == current_user.id:
            raise ValidationError("You cannot delete your own account")

        # Prevent deleting superusers
        if target_user.is_superuser:
            raise AuthorizationError("Cannot delete superuser accounts")

        # Soft delete (deactivate)
        target_user.is_active = False

        await db.commit()

        logger.info(
            "User deleted by admin",
            user_id=str(target_user.id),
            deleted_by=str(current_user.id),
        )

        return True

    @strawberry.mutation
    async def resend_invite(
        self,
        info: Info,
        user_id: UUID,
    ) -> bool:
        """Resend invitation email to a user (admin only)."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Check if user has admin permissions
        if not current_user.is_superuser and not current_user.has_role("admin"):
            raise AuthorizationError("Only admins can resend invites")

        # Get target user
        query = select(User).where(
            User.id == user_id,
            User.organization_id == current_user.organization_id,
        )
        result = await db.execute(query)
        target_user = result.scalar_one_or_none()

        if not target_user:
            raise NotFoundError("User", str(user_id))

        if target_user.is_verified:
            raise ValidationError("User has already verified their email")

        # Generate new temporary password
        temp_password = uuid4().hex[:12]
        target_user.hashed_password = await get_password_hash(temp_password)

        await db.commit()

        logger.info(
            "Invite resent",
            user_id=str(target_user.id),
            resent_by=str(current_user.id),
        )

        # TODO: Send invite email
        # from app.services.email import send_invite_email
        # await send_invite_email(target_user.email, temp_password)

        return True
