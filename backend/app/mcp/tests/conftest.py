"""
Pytest fixtures for MCP tests.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.mcp.config import MCPSettings
from app.mcp.core.auth import MCPAuthenticator, MCPTokenClaims
from app.mcp.server import create_mcp_server


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mcp_settings() -> MCPSettings:
    """Create test MCP settings."""
    return MCPSettings(
        MCP_ENABLED=True,
        MCP_REQUIRE_AUTH=False,  # Disable auth for testing
        MCP_RATE_LIMIT_ENABLED=False,
        MCP_CACHE_ENABLED=False,
        MCP_AUDIT_LOGGING_ENABLED=False,
    )


@pytest.fixture
def mock_redis():
    """Create mock Redis client."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis.exists = AsyncMock(return_value=False)
    redis.client = MagicMock()
    redis.client.pipeline = MagicMock(return_value=AsyncMock())
    return redis


@pytest.fixture
def mock_db():
    """Create mock database session factory."""

    async def session_factory():
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    return session_factory


@pytest.fixture
def mock_celery():
    """Create mock Celery app."""
    celery = MagicMock()
    celery.AsyncResult = MagicMock()
    return celery


@pytest.fixture
def test_user_claims() -> MCPTokenClaims:
    """Create test user claims."""
    return MCPTokenClaims(
        sub=str(uuid4()),
        org_id=str(uuid4()),
        scopes={"data:read", "data:write", "models:read", "models:train"},
        exp=datetime.now(timezone.utc) + timedelta(hours=1),
        iat=datetime.now(timezone.utc),
        aud="mcp-server",
        iss="sales-forecast",
        tier="professional",
        roles=["analyst"],
    )


@pytest.fixture
def test_admin_claims() -> MCPTokenClaims:
    """Create test admin claims."""
    return MCPTokenClaims(
        sub=str(uuid4()),
        org_id=str(uuid4()),
        scopes={
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
        },
        exp=datetime.now(timezone.utc) + timedelta(hours=1),
        iat=datetime.now(timezone.utc),
        aud="mcp-server",
        iss="sales-forecast",
        tier="enterprise",
        roles=["admin"],
    )


@pytest.fixture
def mcp_authenticator() -> MCPAuthenticator:
    """Create test authenticator."""
    return MCPAuthenticator(
        secret_key="test-secret-key",
        algorithm="HS256",
    )


@pytest.fixture
def auth_token(mcp_authenticator: MCPAuthenticator, test_user_claims: MCPTokenClaims) -> str:
    """Create valid auth token."""
    return mcp_authenticator.create_mcp_token(
        user_id=test_user_claims.user_id,
        organization_id=test_user_claims.organization_id,
        roles=test_user_claims.roles,
        scopes=test_user_claims.scopes,
        tier=test_user_claims.tier,
    )


@pytest.fixture
def admin_token(mcp_authenticator: MCPAuthenticator, test_admin_claims: MCPTokenClaims) -> str:
    """Create admin auth token."""
    return mcp_authenticator.create_mcp_token(
        user_id=test_admin_claims.user_id,
        organization_id=test_admin_claims.organization_id,
        roles=test_admin_claims.roles,
        scopes=test_admin_claims.scopes,
        tier=test_admin_claims.tier,
    )


@pytest.fixture
def mcp_app(mock_redis, mock_db, mock_celery) -> FastAPI:
    """Create test MCP FastAPI app."""
    app = FastAPI()

    mcp_router = create_mcp_server(
        redis_client=mock_redis,
        db_session=mock_db,
        celery_app=mock_celery,
    )

    app.include_router(mcp_router, prefix="/mcp")

    return app


@pytest.fixture
def mcp_client(mcp_app: FastAPI) -> TestClient:
    """Create test client for MCP app."""
    return TestClient(mcp_app)


@pytest.fixture
def sample_dataset() -> Dict[str, Any]:
    """Sample dataset for testing."""
    return {
        "id": str(uuid4()),
        "name": "Test Sales Data",
        "description": "Test dataset for unit tests",
        "row_count": 1000,
        "column_count": 10,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "status": "ready",
    }


@pytest.fixture
def sample_model() -> Dict[str, Any]:
    """Sample model for testing."""
    return {
        "id": str(uuid4()),
        "name": "Test MMM Model",
        "model_type": "pymc_mmm",
        "stage": "development",
        "version": "1.0.0",
        "metrics": {
            "mape": 0.085,
            "r2": 0.92,
            "rmse": 1234.56,
            "rhat_max": 1.02,
            "ess_min": 450,
        },
    }


@pytest.fixture
def sample_forecast() -> Dict[str, Any]:
    """Sample forecast result for testing."""
    return {
        "model_id": str(uuid4()),
        "horizon": 12,
        "predictions": [
            {"period": i, "value": 15000 + i * 100, "lower": 14000, "upper": 16000}
            for i in range(12)
        ],
        "confidence_level": 0.95,
    }


@pytest.fixture
def sample_optimization() -> Dict[str, Any]:
    """Sample optimization result for testing."""
    return {
        "total_budget": 100000,
        "allocation": {
            "tv_spend": {"amount": 40000, "contribution": 100000},
            "digital_spend": {"amount": 30000, "contribution": 75000},
            "social_spend": {"amount": 20000, "contribution": 40000},
            "email_spend": {"amount": 10000, "contribution": 20000},
        },
        "expected_return": 235000,
        "roi": 1.35,
    }


class MCPTestClient:
    """
    Helper client for testing MCP endpoints.

    Provides convenience methods for common MCP operations.
    """

    def __init__(self, client: TestClient, auth_token: str = None):
        self.client = client
        self.auth_token = auth_token

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers."""
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    def call_method(
        self,
        method: str,
        params: Dict[str, Any] = None,
        server: str = "data",
    ) -> Dict[str, Any]:
        """Make MCP JSON-RPC call."""
        response = self.client.post(
            f"/mcp/{server}",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": method,
                "params": params or {},
            },
            headers=self._get_headers(),
        )
        return response.json()

    def get_resource(self, uri: str, server: str = "data") -> Dict[str, Any]:
        """Get MCP resource."""
        return self.call_method(
            "resources/read",
            {"uri": uri},
            server=server,
        )

    def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        server: str = "data",
    ) -> Dict[str, Any]:
        """Call MCP tool."""
        return self.call_method(
            "tools/call",
            {"name": tool_name, "arguments": arguments},
            server=server,
        )

    def list_resources(self, server: str = "data") -> Dict[str, Any]:
        """List available resources."""
        return self.call_method("resources/list", server=server)

    def list_tools(self, server: str = "data") -> Dict[str, Any]:
        """List available tools."""
        return self.call_method("tools/list", server=server)


@pytest.fixture
def mcp_test_client(mcp_client: TestClient, auth_token: str) -> MCPTestClient:
    """Create MCP test client with authentication."""
    return MCPTestClient(mcp_client, auth_token)
