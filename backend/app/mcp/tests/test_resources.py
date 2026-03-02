"""
Tests for MCP resources.
"""

from typing import Dict, Any
from unittest.mock import AsyncMock, patch

import pytest

from app.mcp.core.auth import MCPTokenClaims
from app.mcp.core.exceptions import MCPError, MCPErrorCode
from app.mcp.resources.data_resources import (
    DatasetsResource,
    DatasetSchemaResource,
    DatasetQualityResource,
    DatasetPreviewResource,
)
from app.mcp.resources.model_resources import (
    ModelRegistryResource,
    ModelDetailResource,
    ModelPerformanceResource,
)


class TestDatasetsResource:
    """Tests for DatasetsResource."""

    @pytest.fixture
    def resource(self):
        """Create resource instance."""
        return DatasetsResource()

    @pytest.mark.asyncio
    async def test_fetch_datasets(
        self,
        resource: DatasetsResource,
        test_user_claims: MCPTokenClaims,
    ):
        """Test fetching datasets list."""
        result = await resource.fetch(
            uri="data://org123/datasets",
            claims=test_user_claims,
        )

        assert "datasets" in result
        assert isinstance(result["datasets"], list)

    @pytest.mark.asyncio
    async def test_fetch_requires_auth(
        self,
        resource: DatasetsResource,
    ):
        """Test that fetching requires authentication."""
        with pytest.raises(MCPError) as exc:
            await resource.fetch(
                uri="data://org123/datasets",
                claims=None,
            )

        assert exc.value.code == MCPErrorCode.AUTHENTICATION_REQUIRED

    @pytest.mark.asyncio
    async def test_handle_caches_result(
        self,
        resource: DatasetsResource,
        test_user_claims: MCPTokenClaims,
    ):
        """Test that handle caches the result."""
        # First call
        result1 = await resource.handle(
            uri="data://org123/datasets",
            claims=test_user_claims,
        )

        # Should have uri in response
        assert "uri" in result1

    def test_generate_summary(
        self,
        resource: DatasetsResource,
    ):
        """Test dataset summary generation."""
        dataset = {
            "name": "Test Dataset",
            "row_count": 10000,
            "column_count": 15,
        }

        summary = resource._generate_summary(dataset)

        assert "Test Dataset" in summary
        assert "10,000" in summary
        assert "15" in summary


class TestDatasetSchemaResource:
    """Tests for DatasetSchemaResource."""

    @pytest.fixture
    def resource(self):
        """Create resource instance."""
        return DatasetSchemaResource()

    @pytest.mark.asyncio
    async def test_fetch_schema(
        self,
        resource: DatasetSchemaResource,
        test_user_claims: MCPTokenClaims,
    ):
        """Test fetching dataset schema."""
        result = await resource.fetch(
            uri="data://org123/datasets/ds-001/schema",
            claims=test_user_claims,
        )

        assert "columns" in result
        assert "dataset_id" in result

    @pytest.mark.asyncio
    async def test_fetch_requires_dataset_id(
        self,
        resource: DatasetSchemaResource,
        test_user_claims: MCPTokenClaims,
    ):
        """Test that dataset ID is required."""
        with pytest.raises(MCPError) as exc:
            await resource.fetch(
                uri="data://org123/datasets//schema",
                claims=test_user_claims,
            )

        assert exc.value.code == MCPErrorCode.INVALID_PARAMS


class TestDatasetQualityResource:
    """Tests for DatasetQualityResource."""

    @pytest.fixture
    def resource(self):
        """Create resource instance."""
        return DatasetQualityResource()

    @pytest.mark.asyncio
    async def test_fetch_quality(
        self,
        resource: DatasetQualityResource,
        test_user_claims: MCPTokenClaims,
    ):
        """Test fetching quality report."""
        result = await resource.fetch(
            uri="data://org123/datasets/ds-001/quality",
            claims=test_user_claims,
        )

        assert "quality_level" in result
        assert "overall_score" in result
        assert "recommendations" in result


class TestDatasetPreviewResource:
    """Tests for DatasetPreviewResource."""

    @pytest.fixture
    def resource(self):
        """Create resource instance."""
        return DatasetPreviewResource()

    @pytest.mark.asyncio
    async def test_fetch_preview(
        self,
        resource: DatasetPreviewResource,
        test_user_claims: MCPTokenClaims,
    ):
        """Test fetching data preview."""
        result = await resource.fetch(
            uri="data://org123/datasets/ds-001/preview",
            claims=test_user_claims,
        )

        assert "columns" in result
        assert "rows" in result
        assert "preview_rows" in result


class TestModelRegistryResource:
    """Tests for ModelRegistryResource."""

    @pytest.fixture
    def resource(self):
        """Create resource instance."""
        return ModelRegistryResource()

    @pytest.mark.asyncio
    async def test_fetch_registry(
        self,
        resource: ModelRegistryResource,
        test_user_claims: MCPTokenClaims,
    ):
        """Test fetching model registry."""
        result = await resource.fetch(
            uri="models://org123/registry",
            claims=test_user_claims,
        )

        assert "models" in result
        assert "by_stage" in result
        assert "summary" in result


class TestModelDetailResource:
    """Tests for ModelDetailResource."""

    @pytest.fixture
    def resource(self):
        """Create resource instance."""
        return ModelDetailResource()

    @pytest.mark.asyncio
    async def test_fetch_model_detail(
        self,
        resource: ModelDetailResource,
        test_user_claims: MCPTokenClaims,
    ):
        """Test fetching model details."""
        result = await resource.fetch(
            uri="models://org123/registry/model-001",
            claims=test_user_claims,
        )

        assert "id" in result
        assert "name" in result
        assert "versions" in result


class TestModelPerformanceResource:
    """Tests for ModelPerformanceResource."""

    @pytest.fixture
    def resource(self):
        """Create resource instance."""
        return ModelPerformanceResource()

    @pytest.mark.asyncio
    async def test_fetch_performance(
        self,
        resource: ModelPerformanceResource,
        test_user_claims: MCPTokenClaims,
    ):
        """Test fetching performance metrics."""
        result = await resource.fetch(
            uri="models://org123/registry/model-001/performance",
            claims=test_user_claims,
        )

        assert "performance_grade" in result
        assert "key_metrics" in result
        assert "recommendations" in result
