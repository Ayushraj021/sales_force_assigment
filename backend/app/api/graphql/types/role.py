"""Role and Permission input types."""

from typing import Optional
from uuid import UUID

import strawberry

# Note: RoleType and PermissionType are defined in auth.py


@strawberry.input
class CreateRoleInput:
    """Input for creating a role."""

    name: str
    description: Optional[str] = None
    is_default: bool = False
    permission_ids: Optional[list[UUID]] = None


@strawberry.input
class UpdateRoleInput:
    """Input for updating a role."""

    name: Optional[str] = None
    description: Optional[str] = None
    is_default: Optional[bool] = None
    permission_ids: Optional[list[UUID]] = None


@strawberry.input
class CreatePermissionInput:
    """Input for creating a permission."""

    name: str
    description: Optional[str] = None
    resource: str
    action: str
