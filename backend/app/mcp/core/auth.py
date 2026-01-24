"""
MCP OAuth 2.1 Authentication Module.

Provides authentication and authorization for MCP servers,
integrating with the existing RBAC system.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, Dict, List, Optional, Set, Tuple
from uuid import UUID

import structlog
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.config import settings
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.security.rbac import (
    Permission,
    RBACManager,
    Resource,
    UserPermissions,
)
from app.mcp.core.exceptions import (
    MCPError,
    MCPErrorCode,
    authentication_required,
    insufficient_scope,
)

logger = structlog.get_logger("mcp.auth")

# MCP-specific security scheme
mcp_security = HTTPBearer(auto_error=False)


@dataclass
class MCPTokenClaims:
    """
    OAuth 2.1 token claims for MCP.

    Extends standard JWT claims with MCP-specific fields.

    Attributes:
        sub: User ID (subject)
        org_id: Organization ID
        scopes: Set of granted MCP scopes
        exp: Expiration timestamp
        iat: Issued at timestamp
        aud: Audience (MCP server identifier)
        iss: Token issuer
        tier: Subscription tier for rate limiting
        roles: User roles from RBAC system
    """

    sub: str
    org_id: str
    scopes: Set[str]
    exp: datetime
    iat: datetime
    aud: str = "mcp-server"
    iss: str = "sales-forecast"
    tier: str = "professional"
    roles: List[str] = None

    def __post_init__(self):
        if self.roles is None:
            self.roles = []

    def has_scope(self, scope: str) -> bool:
        """Check if token has a specific scope."""
        return scope in self.scopes

    def has_any_scope(self, scopes: List[str]) -> bool:
        """Check if token has any of the specified scopes."""
        return bool(self.scopes.intersection(scopes))

    def has_all_scopes(self, scopes: List[str]) -> bool:
        """Check if token has all specified scopes."""
        return all(scope in self.scopes for scope in scopes)

    @property
    def user_id(self) -> UUID:
        """Get user ID as UUID."""
        return UUID(self.sub)

    @property
    def organization_id(self) -> UUID:
        """Get organization ID as UUID."""
        return UUID(self.org_id)

    def is_expired(self) -> bool:
        """Check if token is expired."""
        return datetime.now(timezone.utc) > self.exp


# MCP Scopes mapping to existing RBAC permissions
MCP_SCOPES: Dict[str, List[Tuple[Resource, Permission]]] = {
    # Data scopes
    "data:read": [
        (Resource.DATASETS, Permission.READ),
        (Resource.DATASETS, Permission.LIST),
    ],
    "data:write": [
        (Resource.DATASETS, Permission.CREATE),
        (Resource.DATASETS, Permission.UPDATE),
    ],
    "data:delete": [
        (Resource.DATASETS, Permission.DELETE),
    ],
    # Model scopes
    "models:read": [
        (Resource.MODELS, Permission.READ),
        (Resource.MODELS, Permission.LIST),
    ],
    "models:train": [
        (Resource.MODELS, Permission.EXECUTE),
    ],
    "models:deploy": [
        (Resource.MODELS, Permission.PUBLISH),
    ],
    # Forecast scopes
    "forecast:read": [
        (Resource.FORECASTS, Permission.READ),
        (Resource.FORECASTS, Permission.LIST),
    ],
    "forecast:create": [
        (Resource.FORECASTS, Permission.CREATE),
    ],
    # Optimization scopes
    "optimize:read": [
        (Resource.FORECASTS, Permission.READ),
    ],
    "optimize:execute": [
        (Resource.FORECASTS, Permission.EXECUTE),
    ],
    # Pipeline scopes
    "pipeline:read": [
        (Resource.PIPELINES, Permission.READ),
        (Resource.PIPELINES, Permission.LIST),
    ],
    "pipeline:execute": [
        (Resource.PIPELINES, Permission.EXECUTE),
    ],
    # Report scopes
    "reports:read": [
        (Resource.REPORTS, Permission.READ),
        (Resource.REPORTS, Permission.LIST),
    ],
    "reports:create": [
        (Resource.REPORTS, Permission.CREATE),
    ],
}

# Default scopes for different roles
ROLE_DEFAULT_SCOPES: Dict[str, Set[str]] = {
    "viewer": {"data:read", "models:read", "forecast:read", "reports:read"},
    "analyst": {
        "data:read",
        "models:read",
        "models:train",
        "forecast:read",
        "forecast:create",
        "optimize:read",
        "reports:read",
        "reports:create",
    },
    "data_engineer": {
        "data:read",
        "data:write",
        "pipeline:read",
        "pipeline:execute",
    },
    "manager": {
        "data:read",
        "models:read",
        "models:deploy",
        "forecast:read",
        "optimize:read",
        "optimize:execute",
        "reports:read",
    },
    "admin": {
        "data:read",
        "data:write",
        "data:delete",
        "models:read",
        "models:train",
        "models:deploy",
        "forecast:read",
        "forecast:create",
        "optimize:read",
        "optimize:execute",
        "pipeline:read",
        "pipeline:execute",
        "reports:read",
        "reports:create",
    },
    "owner": {
        "data:read",
        "data:write",
        "data:delete",
        "models:read",
        "models:train",
        "models:deploy",
        "forecast:read",
        "forecast:create",
        "optimize:read",
        "optimize:execute",
        "pipeline:read",
        "pipeline:execute",
        "reports:read",
        "reports:create",
    },
}


class MCPAuthenticator:
    """
    OAuth 2.1 authenticator for MCP servers.

    Integrates with existing JWT and RBAC systems to provide
    MCP-specific authentication and authorization.

    Example:
        auth = MCPAuthenticator(secret_key=settings.SECRET_KEY)

        # Validate token
        claims = await auth.validate_token(token)

        # Check scope
        if await auth.check_scope(claims, "models:train"):
            # Allow training
    """

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        rbac: Optional[RBACManager] = None,
    ):
        """
        Initialize the authenticator.

        Args:
            secret_key: JWT signing key
            algorithm: JWT algorithm (default: HS256)
            rbac: RBAC manager instance (creates new if not provided)
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.rbac = rbac or RBACManager()

    async def validate_token(
        self,
        token: str,
        required_audience: Optional[str] = None,
    ) -> MCPTokenClaims:
        """
        Validate and decode an OAuth token.

        Args:
            token: JWT token string
            required_audience: Expected audience claim

        Returns:
            MCPTokenClaims with decoded token data

        Raises:
            MCPError: If token is invalid or expired
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
            )

            # Extract and validate required fields
            sub = payload.get("sub")
            if not sub:
                raise MCPError(
                    code=MCPErrorCode.AUTHENTICATION_REQUIRED,
                    message="Invalid token: missing subject",
                )

            org_id = payload.get("org_id")
            if not org_id:
                raise MCPError(
                    code=MCPErrorCode.AUTHENTICATION_REQUIRED,
                    message="Invalid token: missing organization",
                )

            # Validate token type
            token_type = payload.get("type", "access")
            if token_type != "access":
                raise MCPError(
                    code=MCPErrorCode.AUTHENTICATION_REQUIRED,
                    message="Invalid token type: MCP requires access token",
                )

            # Validate audience if specified
            aud = payload.get("aud", "mcp-server")
            if required_audience and aud != required_audience:
                raise MCPError(
                    code=MCPErrorCode.AUTHENTICATION_REQUIRED,
                    message=f"Invalid audience: expected {required_audience}",
                )

            # Extract roles and derive scopes
            roles = payload.get("roles", [])
            scopes = self._derive_scopes_from_roles(roles)

            # Add explicitly granted scopes
            explicit_scopes = payload.get("scopes", [])
            if isinstance(explicit_scopes, list):
                scopes.update(explicit_scopes)

            # Parse timestamps
            exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
            iat = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)

            # Check expiration
            if datetime.now(timezone.utc) > exp:
                raise MCPError(
                    code=MCPErrorCode.AUTHENTICATION_REQUIRED,
                    message="Token has expired",
                    recovery_suggestions=[
                        "Obtain a new access token using your refresh token",
                        "Re-authenticate to get a new token",
                    ],
                )

            return MCPTokenClaims(
                sub=sub,
                org_id=org_id,
                scopes=scopes,
                exp=exp,
                iat=iat,
                aud=aud,
                iss=payload.get("iss", "sales-forecast"),
                tier=payload.get("tier", "professional"),
                roles=roles,
            )

        except JWTError as e:
            logger.warning("MCP token validation failed", error=str(e))
            raise MCPError(
                code=MCPErrorCode.AUTHENTICATION_REQUIRED,
                message=f"Invalid token: {str(e)}",
                recovery_suggestions=[
                    "Ensure the token is correctly formatted",
                    "Obtain a new token if the current one is corrupted",
                ],
            )

    def _derive_scopes_from_roles(self, roles: List[str]) -> Set[str]:
        """Derive MCP scopes from user roles."""
        scopes: Set[str] = set()
        for role in roles:
            role_scopes = ROLE_DEFAULT_SCOPES.get(role, set())
            scopes.update(role_scopes)
        return scopes

    async def check_scope(
        self,
        claims: MCPTokenClaims,
        required_scope: str,
    ) -> bool:
        """
        Check if token has the required scope.

        Args:
            claims: Decoded token claims
            required_scope: Required MCP scope

        Returns:
            True if scope is granted
        """
        if claims.has_scope(required_scope):
            return True

        # Check if user has underlying RBAC permissions
        if required_scope in MCP_SCOPES:
            user_perms = UserPermissions(
                user_id=claims.sub,
                organization_id=claims.org_id,
                roles=set(claims.roles),
            )

            for resource, permission in MCP_SCOPES[required_scope]:
                if not self.rbac.has_permission(user_perms, resource, permission):
                    return False
            return True

        return False

    async def require_scope(
        self,
        claims: MCPTokenClaims,
        required_scope: str,
        request_id: Optional[str] = None,
    ) -> None:
        """
        Require a specific scope, raising error if not present.

        Args:
            claims: Decoded token claims
            required_scope: Required MCP scope
            request_id: Request ID for error correlation

        Raises:
            MCPError: If scope is not granted
        """
        if not await self.check_scope(claims, required_scope):
            raise insufficient_scope(
                required_scope=required_scope,
                available_scopes=list(claims.scopes),
                request_id=request_id,
            )

    async def require_any_scope(
        self,
        claims: MCPTokenClaims,
        scopes: List[str],
        request_id: Optional[str] = None,
    ) -> None:
        """
        Require any of the specified scopes.

        Args:
            claims: Decoded token claims
            scopes: List of acceptable scopes
            request_id: Request ID for error correlation

        Raises:
            MCPError: If no scope is granted
        """
        for scope in scopes:
            if await self.check_scope(claims, scope):
                return

        raise MCPError(
            code=MCPErrorCode.INSUFFICIENT_SCOPE,
            message=f"Token requires one of: {', '.join(scopes)}",
            data={
                "required_scopes": scopes,
                "available_scopes": list(claims.scopes),
            },
            request_id=request_id,
        )

    def get_www_authenticate_header(
        self,
        realm: str = "mcp",
        error: Optional[str] = None,
        error_description: Optional[str] = None,
    ) -> str:
        """
        Return proper WWW-Authenticate header for 401 responses.

        Args:
            realm: Authentication realm
            error: OAuth error code
            error_description: Human-readable error description

        Returns:
            WWW-Authenticate header value
        """
        header = f'Bearer realm="{realm}"'
        if error:
            header += f', error="{error}"'
        if error_description:
            header += f', error_description="{error_description}"'
        return header

    def create_mcp_token(
        self,
        user_id: UUID,
        organization_id: UUID,
        roles: List[str],
        scopes: Optional[Set[str]] = None,
        tier: str = "professional",
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """
        Create an MCP-specific access token.

        Args:
            user_id: User UUID
            organization_id: Organization UUID
            roles: User roles
            scopes: Explicit scopes to grant (derived from roles if not provided)
            tier: Subscription tier
            expires_delta: Token expiration delta

        Returns:
            Encoded JWT token
        """
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=30)

        # Derive scopes from roles if not explicitly provided
        if scopes is None:
            scopes = self._derive_scopes_from_roles(roles)

        payload: Dict[str, Any] = {
            "sub": str(user_id),
            "org_id": str(organization_id),
            "type": "access",
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "aud": "mcp-server",
            "iss": "sales-forecast",
            "roles": roles,
            "scopes": list(scopes),
            "tier": tier,
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)


# FastAPI dependency for MCP authentication
async def get_mcp_claims(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(mcp_security)
    ],
) -> MCPTokenClaims:
    """
    FastAPI dependency to get MCP token claims.

    Usage:
        @router.get("/resource")
        async def get_resource(claims: MCPTokenClaims = Depends(get_mcp_claims)):
            ...
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": 'Bearer realm="mcp"'},
        )

    auth = MCPAuthenticator(secret_key=settings.SECRET_KEY)

    try:
        claims = await auth.validate_token(credentials.credentials)
        return claims
    except MCPError as e:
        raise HTTPException(
            status_code=e.http_status,
            detail=e.message,
            headers={"WWW-Authenticate": auth.get_www_authenticate_header(
                error="invalid_token",
                error_description=e.message,
            )},
        )


async def get_optional_mcp_claims(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(mcp_security)
    ],
) -> Optional[MCPTokenClaims]:
    """
    FastAPI dependency for optional MCP authentication.

    Returns None if no token is provided, claims if valid.
    """
    if credentials is None:
        return None

    auth = MCPAuthenticator(secret_key=settings.SECRET_KEY)

    try:
        return await auth.validate_token(credentials.credentials)
    except MCPError:
        return None


def require_mcp_scope(scope: str):
    """
    Dependency factory for scope-based access control.

    Usage:
        @router.post("/train")
        async def train_model(
            _: None = Depends(require_mcp_scope("models:train")),
            claims: MCPTokenClaims = Depends(get_mcp_claims),
        ):
            ...
    """

    async def scope_checker(
        claims: MCPTokenClaims = Depends(get_mcp_claims),
    ) -> MCPTokenClaims:
        auth = MCPAuthenticator(secret_key=settings.SECRET_KEY)
        await auth.require_scope(claims, scope)
        return claims

    return scope_checker


def require_any_mcp_scope(*scopes: str):
    """
    Dependency factory requiring any of the specified scopes.

    Usage:
        @router.get("/data")
        async def get_data(
            claims: MCPTokenClaims = Depends(
                require_any_mcp_scope("data:read", "data:write")
            ),
        ):
            ...
    """

    async def scope_checker(
        claims: MCPTokenClaims = Depends(get_mcp_claims),
    ) -> MCPTokenClaims:
        auth = MCPAuthenticator(secret_key=settings.SECRET_KEY)
        await auth.require_any_scope(claims, list(scopes))
        return claims

    return scope_checker


# Type aliases for dependency injection
MCPClaims = Annotated[MCPTokenClaims, Depends(get_mcp_claims)]
OptionalMCPClaims = Annotated[Optional[MCPTokenClaims], Depends(get_optional_mcp_claims)]
