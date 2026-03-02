"""Security module."""

from app.core.security.jwt import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    verify_token,
)
from app.core.security.password import get_password_hash, verify_password
from app.core.security.rbac import (
    Permission,
    Resource,
    Role,
    PermissionGrant,
    UserPermissions,
    RBACManager,
    SYSTEM_ROLES,
    require_permission,
    require_any_permission,
    PermissionChecker,
)
from app.core.security.row_level import (
    PolicyAction,
    PolicyOperator,
    PolicyCondition,
    PolicyRule,
    SecurityContext,
    FilterResult,
    RLSManager,
    CommonPolicies,
    RLSMiddleware,
)

__all__ = [
    # JWT
    "create_access_token",
    "create_refresh_token",
    "get_current_user",
    "verify_token",
    # Password
    "get_password_hash",
    "verify_password",
    # RBAC
    "Permission",
    "Resource",
    "Role",
    "PermissionGrant",
    "UserPermissions",
    "RBACManager",
    "SYSTEM_ROLES",
    "require_permission",
    "require_any_permission",
    "PermissionChecker",
    # Row-Level Security
    "PolicyAction",
    "PolicyOperator",
    "PolicyCondition",
    "PolicyRule",
    "SecurityContext",
    "FilterResult",
    "RLSManager",
    "CommonPolicies",
    "RLSMiddleware",
]

# Optional SAML support
try:
    from app.core.security.saml import (
        SAMLConfig,
        SAMLUser,
        SAMLResponse,
        SAMLProvider,
        IdentityProviders,
    )
    __all__.extend([
        "SAMLConfig",
        "SAMLUser",
        "SAMLResponse",
        "SAMLProvider",
        "IdentityProviders",
    ])
except ImportError:
    pass

# Optional OAuth support
try:
    from app.core.security.oauth import (
        OAuthProvider,
        OAuthConfig,
        OAuthToken,
        OAuthUser,
        OAuthClient,
        OAuthManager,
    )
    __all__.extend([
        "OAuthProvider",
        "OAuthConfig",
        "OAuthToken",
        "OAuthUser",
        "OAuthClient",
        "OAuthManager",
    ])
except ImportError:
    pass
