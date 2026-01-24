"""Authentication and user GraphQL types."""

from datetime import datetime
from uuid import UUID

import strawberry
from typing import Optional


@strawberry.type
class TokenType:
    """JWT token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


@strawberry.type
class PermissionType:
    """Permission type."""

    id: UUID
    name: str
    description: Optional[str]
    resource: str
    action: str


@strawberry.type
class RoleType:
    """Role type."""

    id: UUID
    name: str
    description: Optional[str]
    is_default: bool
    permissions: list[PermissionType]


@strawberry.type
class OrganizationType:
    """Organization type."""

    id: UUID
    name: str
    slug: str
    description: Optional[str]
    is_active: bool
    subscription_tier: str
    max_users: int
    max_models: int
    max_datasets: int
    created_at: datetime
    updated_at: datetime


@strawberry.type
class UserType:
    """User type."""

    id: UUID
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    full_name: str
    is_active: bool
    is_verified: bool
    is_superuser: bool
    organization: Optional[OrganizationType]
    roles: list[RoleType]
    created_at: datetime
    updated_at: datetime


@strawberry.type
class AuthPayload:
    """Authentication payload returned after login/register."""

    token: TokenType
    user: UserType


@strawberry.input
class RegisterInput:
    """Input for user registration."""

    email: str
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    organization_name: Optional[str] = None


@strawberry.input
class LoginInput:
    """Input for user login."""

    email: str
    password: str


@strawberry.input
class UpdateUserInput:
    """Input for updating user profile."""

    first_name: Optional[str] = None
    last_name: Optional[str] = None


@strawberry.input
class ChangePasswordInput:
    """Input for changing password."""

    current_password: str
    new_password: str
