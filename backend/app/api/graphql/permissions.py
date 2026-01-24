"""GraphQL permission classes for RBAC."""

from typing import Any

import strawberry
from strawberry.permission import BasePermission
from strawberry.types import Info

from app.api.graphql.context import get_db_session, get_current_user_from_context


class IsAuthenticated(BasePermission):
    """Permission class for authenticated users."""

    message = "User is not authenticated"

    async def has_permission(
        self,
        source: Any,
        info: Info,
        **kwargs: Any,
    ) -> bool:
        """Check if user is authenticated."""
        try:
            db = await get_db_session(info)
            await get_current_user_from_context(info, db)
            return True
        except Exception:
            return False


class IsSuperuser(BasePermission):
    """Permission class for superusers."""

    message = "User is not a superuser"

    async def has_permission(
        self,
        source: Any,
        info: Info,
        **kwargs: Any,
    ) -> bool:
        """Check if user is a superuser."""
        try:
            db = await get_db_session(info)
            user = await get_current_user_from_context(info, db)
            return user.is_superuser
        except Exception:
            return False


class HasRole(BasePermission):
    """Permission class for role-based access."""

    message = "User does not have required role"

    def __init__(self, role: str) -> None:
        self.role = role

    async def has_permission(
        self,
        source: Any,
        info: Info,
        **kwargs: Any,
    ) -> bool:
        """Check if user has the required role."""
        try:
            db = await get_db_session(info)
            user = await get_current_user_from_context(info, db)
            return user.has_role(self.role)
        except Exception:
            return False


class HasPermission(BasePermission):
    """Permission class for fine-grained permission checks."""

    message = "User does not have required permission"

    def __init__(self, permission: str) -> None:
        self.permission = permission

    async def has_permission(
        self,
        source: Any,
        info: Info,
        **kwargs: Any,
    ) -> bool:
        """Check if user has the required permission."""
        try:
            db = await get_db_session(info)
            user = await get_current_user_from_context(info, db)
            return user.has_permission(self.permission)
        except Exception:
            return False


class IsOrganizationMember(BasePermission):
    """Permission class for organization membership."""

    message = "User is not a member of this organization"

    async def has_permission(
        self,
        source: Any,
        info: Info,
        **kwargs: Any,
    ) -> bool:
        """Check if user belongs to an organization."""
        try:
            db = await get_db_session(info)
            user = await get_current_user_from_context(info, db)
            return user.organization_id is not None
        except Exception:
            return False


def require_role(role: str) -> list[type[BasePermission]]:
    """Factory function for role permission."""
    class RolePermission(HasRole):
        def __init__(self) -> None:
            super().__init__(role)
    return [IsAuthenticated, RolePermission]


def require_permission(permission: str) -> list[type[BasePermission]]:
    """Factory function for permission check."""
    class PermissionChecker(HasPermission):
        def __init__(self) -> None:
            super().__init__(permission)
    return [IsAuthenticated, PermissionChecker]
