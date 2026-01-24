"""GraphQL context utilities."""

from typing import Any

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from strawberry.types import Info

from app.core.exceptions import AuthenticationError
from app.core.security.jwt import verify_token
from app.infrastructure.database.session import AsyncSessionLocal


async def get_db_session(info: Info) -> AsyncSession:
    """Get database session from GraphQL context."""
    request: Request = info.context["request"]

    # Check if we already have a session
    if hasattr(request.state, "db"):
        return request.state.db

    # Create new session
    session = AsyncSessionLocal()
    request.state.db = session
    return session


async def get_current_user_from_context(info: Info, db: AsyncSession) -> "User":
    """Get current user from GraphQL context."""
    from app.infrastructure.database.models.user import User

    request: Request = info.context["request"]

    # Get authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise AuthenticationError("Missing or invalid authorization header")

    token = auth_header[7:]  # Remove "Bearer " prefix

    # Verify token
    token_data = verify_token(token)

    # Get user from database
    result = await db.execute(select(User).where(User.id == token_data.user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise AuthenticationError("User not found")

    if not user.is_active:
        raise AuthenticationError("Account is disabled")

    return user


def get_request(info: Info) -> Request:
    """Get FastAPI request from GraphQL context."""
    return info.context["request"]


async def get_context(request: Request) -> dict[str, Any]:
    """Create GraphQL context."""
    return {
        "request": request,
    }
