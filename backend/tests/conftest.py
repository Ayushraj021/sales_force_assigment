"""Pytest configuration and fixtures for backend tests."""

import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.infrastructure.database.models.base import Base
from app.infrastructure.database.session import get_db
from app.main import create_application


# Use in-memory SQLite for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
def app(db_session: AsyncSession) -> FastAPI:
    """Create a test FastAPI application."""
    application = create_application()

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    application.dependency_overrides[get_db] = override_get_db
    return application


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing."""
    async with AsyncClient(
        app=app,
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
def mock_redis() -> MagicMock:
    """Create a mock Redis client."""
    redis = MagicMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis.exists = AsyncMock(return_value=0)
    redis.expire = AsyncMock(return_value=True)
    return redis


@pytest.fixture
def sample_user_data() -> dict:
    """Sample user data for testing."""
    return {
        "email": "test@example.com",
        "password": "SecurePassword123!",
        "first_name": "Test",
        "last_name": "User",
    }


@pytest.fixture
def sample_dataset_data() -> dict:
    """Sample dataset data for testing."""
    return {
        "name": "Test Dataset",
        "description": "A test dataset for unit tests",
        "source_type": "csv",
        "file_path": "/tmp/test_data.csv",
    }


@pytest.fixture
def sample_model_config() -> dict:
    """Sample model configuration for testing."""
    return {
        "name": "Test MMM Model",
        "model_type": "pymc_mmm",
        "target_column": "sales",
        "date_column": "date",
        "channel_columns": ["tv_spend", "digital_spend", "radio_spend"],
        "control_columns": ["price", "seasonality"],
        "adstock_config": {
            "type": "geometric",
            "max_lag": 8,
            "decay_rate": 0.5,
        },
        "saturation_config": {
            "type": "hill",
            "half_saturation": 1.0,
            "slope": 1.0,
        },
    }


@pytest.fixture
def sample_optimization_config() -> dict:
    """Sample optimization configuration for testing."""
    return {
        "total_budget": 1000000.0,
        "channels": ["tv", "digital", "radio"],
        "min_spend": {"tv": 50000, "digital": 100000, "radio": 25000},
        "max_spend": {"tv": 500000, "digital": 400000, "radio": 200000},
        "objective": "maximize_roi",
    }
