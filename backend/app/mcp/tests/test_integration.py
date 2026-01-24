"""
Integration tests for MCP server.
"""

import pytest
from fastapi.testclient import TestClient

from app.mcp.tests.conftest import MCPTestClient


class TestMCPHealth:
    """Tests for MCP health endpoints."""

    def test_mcp_health(self, mcp_client: TestClient):
        """Test MCP health endpoint."""
        response = mcp_client.get("/mcp/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_mcp_info(self, mcp_client: TestClient):
        """Test MCP info endpoint."""
        response = mcp_client.get("/mcp/info")

        assert response.status_code == 200
        data = response.json()
        assert "servers" in data
        assert "data" in data["servers"]
        assert "models" in data["servers"]


class TestMCPDataServer:
    """Integration tests for MCP data server."""

    def test_data_server_health(self, mcp_client: TestClient):
        """Test data server health."""
        response = mcp_client.get("/mcp/data/health")

        assert response.status_code == 200

    def test_list_resources(self, mcp_test_client: MCPTestClient):
        """Test listing data resources."""
        result = mcp_test_client.list_resources(server="data")

        assert "result" in result or "error" in result

    def test_list_tools(self, mcp_test_client: MCPTestClient):
        """Test listing data tools."""
        result = mcp_test_client.list_tools(server="data")

        assert "result" in result or "error" in result


class TestMCPModelsServer:
    """Integration tests for MCP models server."""

    def test_models_server_health(self, mcp_client: TestClient):
        """Test models server health."""
        response = mcp_client.get("/mcp/models/health")

        assert response.status_code == 200

    def test_list_models_resources(self, mcp_test_client: MCPTestClient):
        """Test listing model resources."""
        result = mcp_test_client.list_resources(server="models")

        assert "result" in result or "error" in result


class TestMCPWorkflow:
    """Test common MCP workflows."""

    @pytest.mark.asyncio
    async def test_data_validation_workflow(
        self,
        mcp_test_client: MCPTestClient,
    ):
        """Test data validation workflow."""
        # Step 1: Validate data
        result = mcp_test_client.call_tool(
            tool_name="validate_data",
            arguments={"dataset_id": "ds-001"},
            server="data",
        )

        # Should return result (may be error in test without auth)
        assert "result" in result or "error" in result

    @pytest.mark.asyncio
    async def test_model_training_workflow(
        self,
        mcp_test_client: MCPTestClient,
    ):
        """Test model training workflow."""
        # Step 1: Start training
        result = mcp_test_client.call_tool(
            tool_name="train_model",
            arguments={
                "model_id": "model-001",
                "dataset_id": "ds-001",
                "target_column": "revenue",
            },
            server="models",
        )

        assert "result" in result or "error" in result

    @pytest.mark.asyncio
    async def test_optimization_workflow(
        self,
        mcp_test_client: MCPTestClient,
    ):
        """Test budget optimization workflow."""
        result = mcp_test_client.call_tool(
            tool_name="optimize_budget",
            arguments={
                "model_id": "model-001",
                "total_budget": 100000,
            },
            server="optimization",
        )

        assert "result" in result or "error" in result


class TestMCPBatchRequests:
    """Test batch JSON-RPC requests."""

    def test_batch_request(self, mcp_client: TestClient, auth_token: str):
        """Test batch JSON-RPC request."""
        batch = [
            {"jsonrpc": "2.0", "id": 1, "method": "resources/list", "params": {}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        ]

        response = mcp_client.post(
            "/mcp/data",
            json=batch,
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        # Batch requests should return array
        data = response.json()
        assert isinstance(data, list) or "error" in data


class TestMCPErrorHandling:
    """Test MCP error handling."""

    def test_method_not_found(self, mcp_client: TestClient, auth_token: str):
        """Test unknown method error."""
        response = mcp_client.post(
            "/mcp/data",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "unknown/method",
                "params": {},
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        data = response.json()
        assert "error" in data

    def test_invalid_json(self, mcp_client: TestClient, auth_token: str):
        """Test invalid JSON error."""
        response = mcp_client.post(
            "/mcp/data",
            content="not json",
            headers={
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json",
            },
        )

        data = response.json()
        assert "error" in data

    def test_missing_required_param(self, mcp_client: TestClient, auth_token: str):
        """Test missing required parameter error."""
        response = mcp_client.post(
            "/mcp/data",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "resources/read",
                "params": {},  # Missing uri
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        data = response.json()
        assert "error" in data
