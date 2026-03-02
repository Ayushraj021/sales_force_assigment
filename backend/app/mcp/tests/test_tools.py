"""
Tests for MCP tools.
"""

from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.mcp.core.auth import MCPTokenClaims
from app.mcp.core.exceptions import MCPError, MCPErrorCode
from app.mcp.tools.base import BaseTool, ToolParameter, ParameterType, ToolResult
from app.mcp.tools.data_tools import ValidateDataTool, CheckDataQualityTool
from app.mcp.tools.model_tools import (
    TrainModelTool,
    GetTrainingStatusTool,
    RunInferenceTool,
    CompareModelsTool,
    PromoteModelTool,
)
from app.mcp.tools.optimization_tools import (
    OptimizeBudgetTool,
    AnalyzeROITool,
    RunWhatIfScenarioTool,
    AnalyzeAttributionTool,
)


class TestToolParameter:
    """Tests for ToolParameter."""

    def test_to_json_schema_basic(self):
        """Test basic parameter schema."""
        param = ToolParameter(
            name="dataset_id",
            param_type=ParameterType.STRING,
            description="Dataset ID",
        )

        schema = param.to_json_schema()

        assert schema["type"] == "string"
        assert schema["description"] == "Dataset ID"

    def test_to_json_schema_with_enum(self):
        """Test parameter with enum values."""
        param = ToolParameter(
            name="model_type",
            param_type=ParameterType.STRING,
            description="Model type",
            enum=["prophet", "pymc_mmm"],
        )

        schema = param.to_json_schema()

        assert "enum" in schema
        assert "prophet" in schema["enum"]

    def test_to_json_schema_with_constraints(self):
        """Test parameter with min/max constraints."""
        param = ToolParameter(
            name="horizon",
            param_type=ParameterType.INTEGER,
            description="Forecast horizon",
            minimum=1,
            maximum=52,
        )

        schema = param.to_json_schema()

        assert schema["minimum"] == 1
        assert schema["maximum"] == 52


class TestValidateDataTool:
    """Tests for ValidateDataTool."""

    @pytest.fixture
    def tool(self):
        """Create tool instance."""
        return ValidateDataTool()

    def test_get_schema(self, tool: ValidateDataTool):
        """Test schema generation."""
        schema = tool.get_schema()

        assert schema["name"] == "validate_data"
        assert "inputSchema" in schema
        assert "dataset_id" in schema["inputSchema"]["properties"]

    @pytest.mark.asyncio
    async def test_execute_success(
        self,
        tool: ValidateDataTool,
        test_user_claims: MCPTokenClaims,
    ):
        """Test successful validation."""
        result = await tool.execute(
            arguments={"dataset_id": "ds-001"},
            claims=test_user_claims,
        )

        assert result.success
        assert result.data is not None
        assert "is_valid" in result.data

    @pytest.mark.asyncio
    async def test_handle_validates_args(
        self,
        tool: ValidateDataTool,
        test_user_claims: MCPTokenClaims,
    ):
        """Test argument validation."""
        # Missing required argument
        with pytest.raises(MCPError) as exc:
            await tool.handle(
                arguments={},
                claims=test_user_claims,
            )

        assert exc.value.code == MCPErrorCode.VALIDATION_ERROR


class TestTrainModelTool:
    """Tests for TrainModelTool."""

    @pytest.fixture
    def tool(self, mock_celery):
        """Create tool with mock Celery."""
        return TrainModelTool(celery=mock_celery)

    def test_is_async(self, tool: TrainModelTool):
        """Test tool is marked as async."""
        assert tool.is_async

    @pytest.mark.asyncio
    async def test_execute_returns_job_id(
        self,
        tool: TrainModelTool,
        test_user_claims: MCPTokenClaims,
    ):
        """Test that execution returns a job ID."""
        result = await tool.execute(
            arguments={
                "model_id": "model-001",
                "dataset_id": "ds-001",
                "target_column": "revenue",
            },
            claims=test_user_claims,
        )

        assert result.success
        assert result.is_async
        assert result.job_id is not None
        assert "job_id" in result.data


class TestGetTrainingStatusTool:
    """Tests for GetTrainingStatusTool."""

    @pytest.fixture
    def tool(self, mock_celery):
        """Create tool with mock Celery."""
        return GetTrainingStatusTool(celery=mock_celery)

    @pytest.mark.asyncio
    async def test_get_status(
        self,
        tool: GetTrainingStatusTool,
        test_user_claims: MCPTokenClaims,
    ):
        """Test getting training status."""
        result = await tool.execute(
            arguments={"job_id": "train-abc123"},
            claims=test_user_claims,
        )

        assert result.success
        assert "status" in result.data


class TestRunInferenceTool:
    """Tests for RunInferenceTool."""

    @pytest.fixture
    def tool(self):
        """Create tool instance."""
        return RunInferenceTool()

    @pytest.mark.asyncio
    async def test_run_inference(
        self,
        tool: RunInferenceTool,
        test_user_claims: MCPTokenClaims,
    ):
        """Test running inference."""
        result = await tool.execute(
            arguments={
                "model_id": "model-001",
                "horizon": 12,
            },
            claims=test_user_claims,
        )

        assert result.success
        assert "predictions" in result.data
        assert len(result.data["predictions"]) == 12


class TestCompareModelsTool:
    """Tests for CompareModelsTool."""

    @pytest.fixture
    def tool(self):
        """Create tool instance."""
        return CompareModelsTool()

    @pytest.mark.asyncio
    async def test_compare_models(
        self,
        tool: CompareModelsTool,
        test_user_claims: MCPTokenClaims,
    ):
        """Test model comparison."""
        result = await tool.execute(
            arguments={
                "model_ids": ["model-001", "model-002"],
            },
            claims=test_user_claims,
        )

        assert result.success
        assert "models" in result.data
        assert "recommendation" in result.data

    @pytest.mark.asyncio
    async def test_compare_requires_two_models(
        self,
        tool: CompareModelsTool,
        test_user_claims: MCPTokenClaims,
    ):
        """Test that comparison requires at least 2 models."""
        with pytest.raises(MCPError) as exc:
            await tool.execute(
                arguments={"model_ids": ["model-001"]},
                claims=test_user_claims,
            )

        assert exc.value.code == MCPErrorCode.INVALID_PARAMS


class TestOptimizeBudgetTool:
    """Tests for OptimizeBudgetTool."""

    @pytest.fixture
    def tool(self):
        """Create tool instance."""
        return OptimizeBudgetTool()

    @pytest.mark.asyncio
    async def test_optimize_budget(
        self,
        tool: OptimizeBudgetTool,
        test_admin_claims: MCPTokenClaims,
    ):
        """Test budget optimization."""
        result = await tool.execute(
            arguments={
                "model_id": "model-001",
                "total_budget": 100000,
            },
            claims=test_admin_claims,
        )

        assert result.success
        assert "summary" in result.data
        assert "top_channels" in result.data


class TestAnalyzeROITool:
    """Tests for AnalyzeROITool."""

    @pytest.fixture
    def tool(self):
        """Create tool instance."""
        return AnalyzeROITool()

    @pytest.mark.asyncio
    async def test_analyze_roi(
        self,
        tool: AnalyzeROITool,
        test_user_claims: MCPTokenClaims,
    ):
        """Test ROI analysis."""
        result = await tool.execute(
            arguments={
                "model_id": "model-001",
            },
            claims=test_user_claims,
        )

        assert result.success
        assert "overall_metrics" in result.data
        assert "channels" in result.data


class TestAnalyzeAttributionTool:
    """Tests for AnalyzeAttributionTool."""

    @pytest.fixture
    def tool(self):
        """Create tool instance."""
        return AnalyzeAttributionTool()

    @pytest.mark.asyncio
    async def test_analyze_attribution(
        self,
        tool: AnalyzeAttributionTool,
        test_user_claims: MCPTokenClaims,
    ):
        """Test attribution analysis."""
        result = await tool.execute(
            arguments={
                "model_type": "markov",
                "dataset_id": "ds-001",
            },
            claims=test_user_claims,
        )

        assert result.success
        assert "channels" in result.data
        assert "methodology" in result.data
