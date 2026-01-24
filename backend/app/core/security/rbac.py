"""
Role-Based Access Control (RBAC)

Enhanced permission system with roles, permissions, and resource access.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Any, Optional, Callable, Union
from enum import Enum, auto
from datetime import datetime
import logging
import fnmatch
import re

logger = logging.getLogger(__name__)


class Permission(str, Enum):
    """System permissions."""
    # Read permissions
    READ = "read"
    LIST = "list"
    EXPORT = "export"

    # Write permissions
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"

    # Execute permissions
    EXECUTE = "execute"
    APPROVE = "approve"
    PUBLISH = "publish"

    # Admin permissions
    MANAGE = "manage"
    ADMIN = "admin"


class Resource(str, Enum):
    """System resources."""
    # Analytics
    FORECASTS = "forecasts"
    MODELS = "models"
    REPORTS = "reports"
    DASHBOARDS = "dashboards"

    # Data
    DATASETS = "datasets"
    CONNECTORS = "connectors"
    PIPELINES = "pipelines"

    # Configuration
    SETTINGS = "settings"
    USERS = "users"
    ROLES = "roles"
    ORGANIZATIONS = "organizations"

    # Experiments
    EXPERIMENTS = "experiments"
    CAMPAIGNS = "campaigns"

    # Billing
    BILLING = "billing"
    SUBSCRIPTIONS = "subscriptions"

    # System
    AUDIT_LOGS = "audit_logs"
    API_KEYS = "api_keys"


@dataclass
class PermissionGrant:
    """A permission grant for a resource."""
    resource: Resource
    permissions: Set[Permission]
    conditions: Optional[Dict[str, Any]] = None  # Conditional access
    resource_ids: Optional[Set[str]] = None  # Specific resource IDs


@dataclass
class Role:
    """A role with permissions."""
    name: str
    description: str
    grants: List[PermissionGrant] = field(default_factory=list)
    parent_roles: List[str] = field(default_factory=list)
    is_system_role: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


# Pre-defined system roles
SYSTEM_ROLES = {
    "viewer": Role(
        name="viewer",
        description="Read-only access to analytics",
        grants=[
            PermissionGrant(Resource.FORECASTS, {Permission.READ, Permission.LIST}),
            PermissionGrant(Resource.MODELS, {Permission.READ, Permission.LIST}),
            PermissionGrant(Resource.REPORTS, {Permission.READ, Permission.LIST}),
            PermissionGrant(Resource.DASHBOARDS, {Permission.READ, Permission.LIST}),
        ],
        is_system_role=True,
    ),
    "analyst": Role(
        name="analyst",
        description="Can create and analyze forecasts",
        grants=[
            PermissionGrant(Resource.FORECASTS, {Permission.READ, Permission.LIST, Permission.CREATE, Permission.UPDATE}),
            PermissionGrant(Resource.MODELS, {Permission.READ, Permission.LIST, Permission.EXECUTE}),
            PermissionGrant(Resource.REPORTS, {Permission.READ, Permission.LIST, Permission.CREATE, Permission.EXPORT}),
            PermissionGrant(Resource.DASHBOARDS, {Permission.READ, Permission.LIST, Permission.CREATE, Permission.UPDATE}),
            PermissionGrant(Resource.DATASETS, {Permission.READ, Permission.LIST}),
        ],
        parent_roles=["viewer"],
        is_system_role=True,
    ),
    "data_engineer": Role(
        name="data_engineer",
        description="Can manage data pipelines and connectors",
        grants=[
            PermissionGrant(Resource.DATASETS, {Permission.READ, Permission.LIST, Permission.CREATE, Permission.UPDATE, Permission.DELETE}),
            PermissionGrant(Resource.CONNECTORS, {Permission.READ, Permission.LIST, Permission.CREATE, Permission.UPDATE, Permission.DELETE}),
            PermissionGrant(Resource.PIPELINES, {Permission.READ, Permission.LIST, Permission.CREATE, Permission.UPDATE, Permission.DELETE, Permission.EXECUTE}),
        ],
        parent_roles=["analyst"],
        is_system_role=True,
    ),
    "manager": Role(
        name="manager",
        description="Can manage team and approve actions",
        grants=[
            PermissionGrant(Resource.USERS, {Permission.READ, Permission.LIST}),
            PermissionGrant(Resource.FORECASTS, {Permission.APPROVE, Permission.PUBLISH}),
            PermissionGrant(Resource.REPORTS, {Permission.APPROVE, Permission.PUBLISH}),
            PermissionGrant(Resource.EXPERIMENTS, {Permission.READ, Permission.LIST, Permission.CREATE, Permission.APPROVE}),
        ],
        parent_roles=["analyst"],
        is_system_role=True,
    ),
    "admin": Role(
        name="admin",
        description="Full administrative access",
        grants=[
            PermissionGrant(Resource.USERS, {Permission.MANAGE}),
            PermissionGrant(Resource.ROLES, {Permission.MANAGE}),
            PermissionGrant(Resource.SETTINGS, {Permission.MANAGE}),
            PermissionGrant(Resource.API_KEYS, {Permission.MANAGE}),
            PermissionGrant(Resource.AUDIT_LOGS, {Permission.READ, Permission.LIST}),
        ],
        parent_roles=["manager", "data_engineer"],
        is_system_role=True,
    ),
    "owner": Role(
        name="owner",
        description="Organization owner with full access",
        grants=[
            PermissionGrant(Resource.ORGANIZATIONS, {Permission.ADMIN}),
            PermissionGrant(Resource.BILLING, {Permission.MANAGE}),
            PermissionGrant(Resource.SUBSCRIPTIONS, {Permission.MANAGE}),
        ],
        parent_roles=["admin"],
        is_system_role=True,
    ),
}


@dataclass
class UserPermissions:
    """User's effective permissions."""
    user_id: str
    organization_id: str
    roles: Set[str]
    direct_grants: List[PermissionGrant] = field(default_factory=list)
    denials: List[PermissionGrant] = field(default_factory=list)


class RBACManager:
    """
    Role-Based Access Control Manager.

    Features:
    - Role hierarchy
    - Permission inheritance
    - Conditional access
    - Resource-level permissions
    - Permission caching

    Example:
        rbac = RBACManager()
        rbac.register_role(custom_role)

        if rbac.has_permission(user_perms, Resource.FORECASTS, Permission.CREATE):
            # Allow action
    """

    def __init__(self):
        self._roles: Dict[str, Role] = dict(SYSTEM_ROLES)
        self._permission_cache: Dict[str, Set[tuple]] = {}

    def register_role(self, role: Role) -> None:
        """Register a custom role."""
        if role.is_system_role:
            raise ValueError("Cannot modify system roles")
        self._roles[role.name] = role
        self._invalidate_cache()

    def get_role(self, name: str) -> Optional[Role]:
        """Get role by name."""
        return self._roles.get(name)

    def list_roles(self) -> List[Role]:
        """List all roles."""
        return list(self._roles.values())

    def get_role_hierarchy(self, role_name: str) -> List[str]:
        """Get all roles in hierarchy (including parent roles)."""
        visited = set()
        result = []

        def traverse(name: str):
            if name in visited:
                return
            visited.add(name)
            result.append(name)

            role = self._roles.get(name)
            if role:
                for parent in role.parent_roles:
                    traverse(parent)

        traverse(role_name)
        return result

    def get_effective_permissions(
        self,
        user_perms: UserPermissions,
    ) -> Dict[Resource, Set[Permission]]:
        """
        Calculate effective permissions for a user.

        Args:
            user_perms: User's permissions

        Returns:
            Dict of resource to permissions
        """
        cache_key = f"{user_perms.user_id}:{user_perms.organization_id}"
        if cache_key in self._permission_cache:
            return {
                Resource(r): {Permission(p) for p in perms}
                for r, perms in self._permission_cache[cache_key]
            }

        effective: Dict[Resource, Set[Permission]] = {}

        # Collect permissions from all roles
        all_roles = set()
        for role_name in user_perms.roles:
            all_roles.update(self.get_role_hierarchy(role_name))

        for role_name in all_roles:
            role = self._roles.get(role_name)
            if not role:
                continue

            for grant in role.grants:
                if grant.resource not in effective:
                    effective[grant.resource] = set()
                effective[grant.resource].update(grant.permissions)

        # Add direct grants
        for grant in user_perms.direct_grants:
            if grant.resource not in effective:
                effective[grant.resource] = set()
            effective[grant.resource].update(grant.permissions)

        # Apply denials
        for denial in user_perms.denials:
            if denial.resource in effective:
                effective[denial.resource] -= denial.permissions

        # Handle ADMIN and MANAGE permissions
        for resource, perms in effective.items():
            if Permission.ADMIN in perms:
                perms.update(Permission)
            elif Permission.MANAGE in perms:
                perms.update({Permission.READ, Permission.LIST, Permission.CREATE, Permission.UPDATE, Permission.DELETE})

        # Cache result
        self._permission_cache[cache_key] = {
            (r.value, {p.value for p in perms}) for r, perms in effective.items()
        }

        return effective

    def has_permission(
        self,
        user_perms: UserPermissions,
        resource: Resource,
        permission: Permission,
        resource_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Check if user has a specific permission.

        Args:
            user_perms: User's permissions
            resource: Resource to check
            permission: Permission to check
            resource_id: Specific resource ID
            context: Additional context for conditional access

        Returns:
            True if permitted
        """
        effective = self.get_effective_permissions(user_perms)

        resource_perms = effective.get(resource, set())
        if permission not in resource_perms:
            return False

        # Check resource-specific grants
        if resource_id:
            for grant in user_perms.direct_grants:
                if grant.resource == resource and grant.resource_ids:
                    if resource_id not in grant.resource_ids:
                        continue

            # Check denials for specific resource
            for denial in user_perms.denials:
                if denial.resource == resource and denial.resource_ids:
                    if resource_id in denial.resource_ids:
                        if permission in denial.permissions:
                            return False

        # Check conditions
        if context:
            for role_name in user_perms.roles:
                for role_name in self.get_role_hierarchy(role_name):
                    role = self._roles.get(role_name)
                    if not role:
                        continue
                    for grant in role.grants:
                        if grant.resource == resource and grant.conditions:
                            if not self._evaluate_conditions(grant.conditions, context):
                                return False

        return True

    def _evaluate_conditions(
        self,
        conditions: Dict[str, Any],
        context: Dict[str, Any],
    ) -> bool:
        """Evaluate access conditions."""
        for key, expected in conditions.items():
            actual = context.get(key)

            if isinstance(expected, dict):
                # Complex conditions
                op = expected.get("op", "eq")
                value = expected.get("value")

                if op == "eq" and actual != value:
                    return False
                elif op == "ne" and actual == value:
                    return False
                elif op == "in" and actual not in value:
                    return False
                elif op == "not_in" and actual in value:
                    return False
                elif op == "gt" and not (actual > value):
                    return False
                elif op == "gte" and not (actual >= value):
                    return False
                elif op == "lt" and not (actual < value):
                    return False
                elif op == "lte" and not (actual <= value):
                    return False
                elif op == "match" and not fnmatch.fnmatch(str(actual), value):
                    return False
                elif op == "regex" and not re.match(value, str(actual)):
                    return False
            else:
                # Simple equality
                if actual != expected:
                    return False

        return True

    def _invalidate_cache(self) -> None:
        """Invalidate permission cache."""
        self._permission_cache.clear()

    def check_permissions(
        self,
        user_perms: UserPermissions,
        requirements: List[tuple],
    ) -> bool:
        """
        Check multiple permission requirements (all must pass).

        Args:
            user_perms: User's permissions
            requirements: List of (resource, permission) tuples

        Returns:
            True if all requirements are met
        """
        return all(
            self.has_permission(user_perms, resource, permission)
            for resource, permission in requirements
        )

    def check_any_permission(
        self,
        user_perms: UserPermissions,
        requirements: List[tuple],
    ) -> bool:
        """
        Check if user has any of the permissions.

        Args:
            user_perms: User's permissions
            requirements: List of (resource, permission) tuples

        Returns:
            True if any requirement is met
        """
        return any(
            self.has_permission(user_perms, resource, permission)
            for resource, permission in requirements
        )


# Permission decorators for FastAPI
def require_permission(
    resource: Resource,
    permission: Permission,
    rbac_manager: Optional[RBACManager] = None,
):
    """
    Decorator to require permission for an endpoint.

    Example:
        @router.post("/forecasts")
        @require_permission(Resource.FORECASTS, Permission.CREATE)
        async def create_forecast(current_user: User = Depends(get_current_user)):
            ...
    """
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            # Get current user from kwargs or args
            current_user = kwargs.get("current_user")
            if not current_user:
                raise PermissionError("Authentication required")

            manager = rbac_manager or RBACManager()
            user_perms = UserPermissions(
                user_id=current_user.id,
                organization_id=current_user.organization_id,
                roles=set(current_user.roles),
            )

            if not manager.has_permission(user_perms, resource, permission):
                raise PermissionError(f"Permission denied: {resource.value}:{permission.value}")

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_any_permission(*requirements: tuple):
    """
    Decorator to require any of the specified permissions.

    Example:
        @require_any_permission(
            (Resource.FORECASTS, Permission.READ),
            (Resource.REPORTS, Permission.READ),
        )
        async def get_analytics(...):
            ...
    """
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get("current_user")
            if not current_user:
                raise PermissionError("Authentication required")

            manager = RBACManager()
            user_perms = UserPermissions(
                user_id=current_user.id,
                organization_id=current_user.organization_id,
                roles=set(current_user.roles),
            )

            if not manager.check_any_permission(user_perms, list(requirements)):
                raise PermissionError("Permission denied")

            return await func(*args, **kwargs)
        return wrapper
    return decorator


class PermissionChecker:
    """
    Dependency for checking permissions in FastAPI.

    Example:
        @router.get("/forecasts/{forecast_id}")
        async def get_forecast(
            forecast_id: str,
            _: None = Depends(PermissionChecker(Resource.FORECASTS, Permission.READ))
        ):
            ...
    """

    def __init__(
        self,
        resource: Resource,
        permission: Permission,
        resource_id_param: Optional[str] = None,
    ):
        self.resource = resource
        self.permission = permission
        self.resource_id_param = resource_id_param

    async def __call__(
        self,
        current_user: Any,  # Type depends on your User model
        **path_params,
    ) -> None:
        """Check permission."""
        manager = RBACManager()
        user_perms = UserPermissions(
            user_id=current_user.id,
            organization_id=current_user.organization_id,
            roles=set(current_user.roles),
        )

        resource_id = None
        if self.resource_id_param:
            resource_id = path_params.get(self.resource_id_param)

        if not manager.has_permission(user_perms, self.resource, self.permission, resource_id):
            raise PermissionError(f"Permission denied: {self.resource.value}:{self.permission.value}")
