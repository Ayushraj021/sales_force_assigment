"""Health check endpoints."""

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.infrastructure.database.session import get_db

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    environment: str


class DetailedHealthResponse(BaseModel):
    """Detailed health check response."""

    status: str
    version: str
    environment: str
    database: str
    redis: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic health check endpoint."""
    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )


@router.get("/health/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> DetailedHealthResponse:
    """Detailed health check including database and Redis status."""
    # Check database
    db_status = "unhealthy"
    try:
        await db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception:
        pass

    # Check Redis
    redis_status = "unhealthy"
    try:
        redis_client = request.app.state.redis
        await redis_client.client.ping()
        redis_status = "healthy"
    except Exception:
        pass

    overall_status = "healthy" if db_status == "healthy" and redis_status == "healthy" else "degraded"

    return DetailedHealthResponse(
        status=overall_status,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        database=db_status,
        redis=redis_status,
    )


@router.get("/health/ready")
async def readiness_check(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Kubernetes readiness probe."""
    try:
        await db.execute(text("SELECT 1"))
        redis_client = request.app.state.redis
        await redis_client.client.ping()
        return {"status": "ready", "ready": True}
    except Exception as e:
        return {"status": "not_ready", "ready": False, "error": str(e)}


@router.get("/health/live")
async def liveness_check() -> dict:
    """Kubernetes liveness probe."""
    return {"status": "alive"}
