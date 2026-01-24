"""JWT token handling."""

from datetime import datetime, timedelta, timezone
from typing import Annotated, Any
from uuid import UUID

import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import AuthenticationError
from app.infrastructure.database.session import get_db

logger = structlog.get_logger()

# Security scheme
security = HTTPBearer(auto_error=False)


class TokenPayload(BaseModel):
    """JWT token payload."""

    sub: str  # user_id
    type: str  # access or refresh
    exp: datetime
    iat: datetime
    org_id: str | None = None
    roles: list[str] = []


class TokenData(BaseModel):
    """Decoded token data."""

    user_id: UUID
    token_type: str
    organization_id: UUID | None = None
    roles: list[str] = []


def create_access_token(
    user_id: UUID,
    organization_id: UUID | None = None,
    roles: list[str] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a new access token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode: dict[str, Any] = {
        "sub": str(user_id),
        "type": "access",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "roles": roles or [],
    }

    if organization_id:
        to_encode["org_id"] = str(organization_id)

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return encoded_jwt


def create_refresh_token(
    user_id: UUID,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a new refresh token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

    to_encode: dict[str, Any] = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> TokenData:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )

        user_id = payload.get("sub")
        if user_id is None:
            raise AuthenticationError("Invalid token: missing subject")

        if payload.get("type") != token_type:
            raise AuthenticationError(f"Invalid token type: expected {token_type}")

        org_id = payload.get("org_id")

        return TokenData(
            user_id=UUID(user_id),
            token_type=payload.get("type", "access"),
            organization_id=UUID(org_id) if org_id else None,
            roles=payload.get("roles", []),
        )

    except JWTError as e:
        logger.warning("Token verification failed", error=str(e))
        raise AuthenticationError(f"Invalid token: {str(e)}")


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: AsyncSession = Depends(get_db),
) -> "User":
    """Get the current authenticated user from the JWT token."""
    from app.infrastructure.database.models.user import User

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        token_data = verify_token(credentials.credentials)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e.message),
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    result = await db.execute(
        select(User).where(User.id == token_data.user_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    return user


async def get_current_active_superuser(
    current_user: Annotated["User", Depends(get_current_user)],
) -> "User":
    """Get the current active superuser."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return current_user


def require_permission(permission: str):
    """Dependency factory for permission-based access control."""
    async def permission_checker(
        current_user: Annotated["User", Depends(get_current_user)],
    ) -> "User":
        if not current_user.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission}",
            )
        return current_user
    return permission_checker


def require_role(role: str):
    """Dependency factory for role-based access control."""
    async def role_checker(
        current_user: Annotated["User", Depends(get_current_user)],
    ) -> "User":
        if not current_user.has_role(role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing role: {role}",
            )
        return current_user
    return role_checker


# Type alias for dependency injection
from app.infrastructure.database.models.user import User  # noqa: E402

CurrentUser = Annotated[User, Depends(get_current_user)]
SuperUser = Annotated[User, Depends(get_current_active_superuser)]
