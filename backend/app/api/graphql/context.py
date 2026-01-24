"""GraphQL context utilities."""

from typing import Any, AsyncIterator

import structlog
from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from strawberry.extensions import SchemaExtension
from strawberry.types import Info

from app.core.exceptions import AuthenticationError
from app.core.security.jwt import verify_token
from app.infrastructure.database.session import AsyncSessionLocal

logger = structlog.get_logger()


class DatabaseSessionExtension(SchemaExtension):
    """Extension to handle database session lifecycle for GraphQL requests."""

    async def on_operation(self) -> AsyncIterator[None]:
        """Called before and after each GraphQL operation."""
        # Before operation - session is already created in context_getter
        yield
        # After operation - cleanup session
        request = self.execution_context.context.get("request")
        if request and hasattr(request.state, "db"):
            session: AsyncSession = request.state.db
            try:
                await session.close()
            except Exception as e:
                logger.warning("Error closing GraphQL database session", error=str(e))
            finally:
                if hasattr(request.state, "db"):
                    delattr(request.state, "db")


async def get_db_session(info: Info) -> AsyncSession:
    """Get database session from GraphQL context.

    Sessions are created in get_context and cleaned up by
    DatabaseSessionExtension after the operation completes.
    """
    request: Request = info.context["request"]

    # Session should already be created by context getter
    if hasattr(request.state, "db"):
        return request.state.db

    # Fallback: create new session if not in context
    session = AsyncSessionLocal()
    request.state.db = session
    return session


async def get_current_user_from_context(info: Info, db: AsyncSession) -> "User":
    """Get current user from GraphQL context."""
    from app.infrastructure.database.models.user import User, Role

    request: Request = info.context["request"]

    # Get authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise AuthenticationError("Missing or invalid authorization header")

    token = auth_header[7:]  # Remove "Bearer " prefix

    # Verify token
    token_data = verify_token(token)

    # Get user from database with eagerly loaded relationships
    result = await db.execute(
        select(User)
        .where(User.id == token_data.user_id)
        .options(
            selectinload(User.organization),
            selectinload(User.roles).selectinload(Role.permissions),
        )
    )
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
    """Create GraphQL context with database session lifecycle management.

    The session is created proactively and stored in request.state for access
    by resolvers. Cleanup is handled by DatabaseSessionExtension.
    """
    # Create session proactively to ensure it's available
    session = AsyncSessionLocal()

    # Store in request state for access by resolvers
    request.state.db = session

    return {
        "request": request,
        "db": session,
    }
