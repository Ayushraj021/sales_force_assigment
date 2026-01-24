"""Authentication mutations."""

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

import strawberry
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from strawberry.types import Info

from app.api.graphql.context import get_db_session, get_current_user_from_context
from app.api.graphql.types.auth import (
    AuthPayload,
    ChangePasswordInput,
    ForgotPasswordInput,
    LoginInput,
    PasswordResetResult,
    RegisterInput,
    ResetPasswordInput,
    TokenType,
    UpdateUserInput,
    UserType,
    RoleType,
    PermissionType,
    OrganizationType,
)
from app.config import settings
from app.core.exceptions import AuthenticationError, ConflictError, ValidationError
from app.core.security.jwt import create_access_token, create_refresh_token, verify_token
from app.core.security.password import get_password_hash, verify_password
from app.infrastructure.database.models.organization import Organization
from app.infrastructure.database.models.user import Role, User

logger = structlog.get_logger()


def user_to_graphql(user: User) -> UserType:
    """Convert database user to GraphQL type."""
    org = None
    if user.organization:
        org = OrganizationType(
            id=user.organization.id,
            name=user.organization.name,
            slug=user.organization.slug,
            description=user.organization.description,
            is_active=user.organization.is_active,
            subscription_tier=user.organization.subscription_tier,
            max_users=user.organization.max_users,
            max_models=user.organization.max_models,
            max_datasets=user.organization.max_datasets,
            created_at=user.organization.created_at,
            updated_at=user.organization.updated_at,
        )

    roles = []
    for role in user.roles:
        permissions = [
            PermissionType(
                id=p.id,
                name=p.name,
                description=p.description,
                resource=p.resource,
                action=p.action,
            )
            for p in role.permissions
        ]
        roles.append(
            RoleType(
                id=role.id,
                name=role.name,
                description=role.description,
                is_default=role.is_default,
                permissions=permissions,
            )
        )

    return UserType(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        full_name=user.full_name,
        is_active=user.is_active,
        is_verified=user.is_verified,
        is_superuser=user.is_superuser,
        organization=org,
        roles=roles,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@strawberry.type
class AuthMutation:
    """Authentication mutations."""

    @strawberry.mutation
    async def register(
        self,
        info: Info,
        input: RegisterInput,
    ) -> AuthPayload:
        """Register a new user."""
        db = await get_db_session(info)

        # Check if email exists
        result = await db.execute(
            select(User).where(User.email == input.email)
        )
        if result.scalar_one_or_none():
            raise ConflictError("User with this email already exists")

        # Validate password
        if len(input.password) < 8:
            raise ValidationError("Password must be at least 8 characters")

        # Create organization if provided
        organization = None
        if input.organization_name:
            org_slug = input.organization_name.lower().replace(" ", "-")
            organization = Organization(
                id=uuid4(),
                name=input.organization_name,
                slug=org_slug,
            )
            db.add(organization)

        # Create user
        user = User(
            id=uuid4(),
            email=input.email,
            hashed_password=await get_password_hash(input.password),
            first_name=input.first_name,
            last_name=input.last_name,
            organization_id=organization.id if organization else None,
        )
        db.add(user)

        # Assign default role if exists
        result = await db.execute(
            select(Role).where(Role.is_default == True)
        )
        default_role = result.scalar_one_or_none()
        if default_role:
            user.roles.append(default_role)

        await db.commit()

        # Re-fetch user with relationships for GraphQL response
        result = await db.execute(
            select(User)
            .where(User.id == user.id)
            .options(
                selectinload(User.organization),
                selectinload(User.roles).selectinload(Role.permissions),
            )
        )
        user = result.scalar_one()

        logger.info("User registered", user_id=str(user.id), email=user.email)

        # Create tokens
        access_token = create_access_token(
            user_id=user.id,
            organization_id=user.organization_id,
            roles=[r.name for r in user.roles],
        )
        refresh_token = create_refresh_token(user_id=user.id)

        return AuthPayload(
            token=TokenType(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            ),
            user=user_to_graphql(user),
        )

    @strawberry.mutation
    async def login(
        self,
        info: Info,
        input: LoginInput,
    ) -> AuthPayload:
        """Login with email and password."""
        db = await get_db_session(info)

        # Get user with eagerly loaded relationships
        result = await db.execute(
            select(User)
            .where(User.email == input.email)
            .options(
                selectinload(User.organization),
                selectinload(User.roles).selectinload(Role.permissions),
            )
        )
        user = result.scalar_one_or_none()

        if not user or not await verify_password(input.password, user.hashed_password):
            raise AuthenticationError("Invalid email or password")

        if not user.is_active:
            raise AuthenticationError("Account is disabled")

        # Update last login
        user.last_login = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(user)

        logger.info("User logged in", user_id=str(user.id), email=user.email)

        # Create tokens
        access_token = create_access_token(
            user_id=user.id,
            organization_id=user.organization_id,
            roles=[r.name for r in user.roles],
        )
        refresh_token = create_refresh_token(user_id=user.id)

        return AuthPayload(
            token=TokenType(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            ),
            user=user_to_graphql(user),
        )

    @strawberry.mutation
    async def refresh_token(
        self,
        info: Info,
        refresh_token: str,
    ) -> TokenType:
        """Refresh access token using refresh token."""
        db = await get_db_session(info)

        # Verify refresh token
        token_data = verify_token(refresh_token, token_type="refresh")

        # Get user
        result = await db.execute(
            select(User).where(User.id == token_data.user_id)
        )
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            raise AuthenticationError("Invalid refresh token")

        # Create new tokens
        access_token = create_access_token(
            user_id=user.id,
            organization_id=user.organization_id,
            roles=[r.name for r in user.roles],
        )
        new_refresh_token = create_refresh_token(user_id=user.id)

        return TokenType(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    @strawberry.mutation
    async def update_profile(
        self,
        info: Info,
        input: UpdateUserInput,
    ) -> UserType:
        """Update current user's profile."""
        db = await get_db_session(info)
        user = await get_current_user_from_context(info, db)

        if input.first_name is not None:
            user.first_name = input.first_name
        if input.last_name is not None:
            user.last_name = input.last_name

        await db.commit()

        # Re-fetch user with relationships for GraphQL response
        result = await db.execute(
            select(User)
            .where(User.id == user.id)
            .options(
                selectinload(User.organization),
                selectinload(User.roles).selectinload(Role.permissions),
            )
        )
        user = result.scalar_one()

        return user_to_graphql(user)

    @strawberry.mutation
    async def change_password(
        self,
        info: Info,
        input: ChangePasswordInput,
    ) -> bool:
        """Change current user's password."""
        db = await get_db_session(info)
        user = await get_current_user_from_context(info, db)

        if not await verify_password(input.current_password, user.hashed_password):
            raise AuthenticationError("Current password is incorrect")

        if len(input.new_password) < 8:
            raise ValidationError("New password must be at least 8 characters")

        user.hashed_password = await get_password_hash(input.new_password)
        await db.commit()

        logger.info("Password changed", user_id=str(user.id))
        return True

    @strawberry.mutation
    async def forgot_password(
        self,
        info: Info,
        email: str,
    ) -> PasswordResetResult:
        """Request a password reset email."""
        db = await get_db_session(info)

        # Check if user exists
        result = await db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()

        # Always return success to prevent email enumeration
        if not user:
            logger.warning("Password reset requested for non-existent email", email=email)
            return PasswordResetResult(
                success=True,
                message="If an account exists with this email, a reset link has been sent.",
            )

        if not user.is_active:
            logger.warning("Password reset requested for inactive account", email=email)
            return PasswordResetResult(
                success=True,
                message="If an account exists with this email, a reset link has been sent.",
            )

        # Generate password reset token (valid for 1 hour)
        reset_token = create_access_token(
            user_id=user.id,
            organization_id=user.organization_id,
            roles=["password_reset"],
            expires_delta=timedelta(hours=1),
        )

        # Store the reset token hash in user record
        user.password_reset_token = await get_password_hash(reset_token)
        user.password_reset_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        await db.commit()

        logger.info("Password reset requested", user_id=str(user.id), email=email)

        # TODO: Send email with reset link
        # from app.services.email import send_password_reset_email
        # await send_password_reset_email(user.email, reset_token)

        return PasswordResetResult(
            success=True,
            message="If an account exists with this email, a reset link has been sent.",
        )

    @strawberry.mutation
    async def reset_password(
        self,
        info: Info,
        input: ResetPasswordInput,
    ) -> PasswordResetResult:
        """Reset password using a reset token."""
        db = await get_db_session(info)

        # Validate new password
        if len(input.new_password) < 8:
            raise ValidationError("New password must be at least 8 characters")

        # Verify the reset token
        try:
            token_data = verify_token(input.token)
        except Exception:
            raise ValidationError("Invalid or expired reset token")

        # Check if token is for password reset
        if "password_reset" not in token_data.roles:
            raise ValidationError("Invalid reset token")

        # Get user
        result = await db.execute(
            select(User).where(User.id == token_data.user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise ValidationError("Invalid reset token")

        if not user.is_active:
            raise ValidationError("Account is disabled")

        # Update password
        user.hashed_password = await get_password_hash(input.new_password)
        user.password_reset_token = None
        user.password_reset_expires = None

        await db.commit()

        logger.info("Password reset completed", user_id=str(user.id))

        return PasswordResetResult(
            success=True,
            message="Password has been reset successfully. You can now log in with your new password.",
        )

    @strawberry.mutation
    async def verify_email(
        self,
        info: Info,
        token: str,
    ) -> PasswordResetResult:
        """Verify email address using verification token."""
        db = await get_db_session(info)

        # Verify the token
        try:
            token_data = verify_token(token)
        except Exception:
            raise ValidationError("Invalid or expired verification token")

        # Get user
        result = await db.execute(
            select(User).where(User.id == token_data.user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise ValidationError("Invalid verification token")

        if user.is_verified:
            return PasswordResetResult(
                success=True,
                message="Email is already verified.",
            )

        # Mark user as verified
        user.is_verified = True
        await db.commit()

        logger.info("Email verified", user_id=str(user.id))

        return PasswordResetResult(
            success=True,
            message="Email verified successfully.",
        )
