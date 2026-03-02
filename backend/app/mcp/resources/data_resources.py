"""
Data Resources for MCP.

Provides read-only access to datasets, schemas, quality reports, and previews.
"""

import json
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog

from app.mcp.core.auth import MCPTokenClaims
from app.mcp.core.exceptions import MCPError, MCPErrorCode, resource_not_found
from app.mcp.formatters.insight_formatter import format_data_quality
from app.mcp.resources.base import BaseResource, PaginatedResource

logger = structlog.get_logger("mcp.resources.data")


class DatasetsResource(PaginatedResource):
    """
    List datasets with summaries.

    URI Pattern: data://{org}/datasets
    Scope: data:read
    """

    resource_type = "datasets_list"
    uri_template = "data://{org}/datasets"
    description = "List all datasets with summaries"
    required_scope = "data:read"

    async def fetch(
        self,
        uri: str,
        claims: Optional[MCPTokenClaims],
    ) -> Dict[str, Any]:
        """Fetch list of datasets."""
        if not claims:
            raise MCPError(
                code=MCPErrorCode.AUTHENTICATION_REQUIRED,
                message="Authentication required to list datasets",
            )

        org_id = claims.org_id

        # Query datasets from database
        datasets = await self._get_datasets(org_id)

        # Format for LLM consumption
        formatted = []
        for ds in datasets:
            formatted.append({
                "id": str(ds.get("id", "")),
                "name": ds.get("name", "Unnamed"),
                "description": ds.get("description", ""),
                "row_count": ds.get("row_count", 0),
                "column_count": ds.get("column_count", 0),
                "created_at": ds.get("created_at", ""),
                "updated_at": ds.get("updated_at", ""),
                "status": ds.get("status", "unknown"),
                "summary": self._generate_summary(ds),
            })

        return {
            "datasets": formatted,
            "total_count": len(formatted),
            "organization_id": org_id,
        }

    async def _get_datasets(self, org_id: str) -> List[Dict[str, Any]]:
        """Get datasets from database."""
        if not self.db:
            # Return mock data for development
            return [
                {
                    "id": "ds-001",
                    "name": "Sales Data 2024",
                    "description": "Historical sales data for forecasting",
                    "row_count": 52000,
                    "column_count": 15,
                    "created_at": "2024-01-15T10:00:00Z",
                    "updated_at": "2024-06-20T14:30:00Z",
                    "status": "ready",
                },
                {
                    "id": "ds-002",
                    "name": "Marketing Spend",
                    "description": "Channel-wise marketing expenditure",
                    "row_count": 1200,
                    "column_count": 8,
                    "created_at": "2024-02-01T09:00:00Z",
                    "updated_at": "2024-06-18T11:15:00Z",
                    "status": "ready",
                },
            ]

        # Real database query
        from sqlalchemy import select
        from app.infrastructure.database.models.dataset import Dataset

        async with self.db() as session:
            result = await session.execute(
                select(Dataset).where(Dataset.organization_id == UUID(org_id))
            )
            datasets = result.scalars().all()

            return [
                {
                    "id": str(ds.id),
                    "name": ds.name,
                    "description": ds.description or "",
                    "row_count": ds.row_count or 0,
                    "column_count": len(ds.schema_info.get("columns", [])) if ds.schema_info else 0,
                    "created_at": ds.created_at.isoformat() if ds.created_at else "",
                    "updated_at": ds.updated_at.isoformat() if ds.updated_at else "",
                    "status": ds.status,
                }
                for ds in datasets
            ]

    def _generate_summary(self, dataset: Dict[str, Any]) -> str:
        """Generate human-readable summary."""
        name = dataset.get("name", "Dataset")
        rows = dataset.get("row_count", 0)
        cols = dataset.get("column_count", 0)

        return f"{name} contains {rows:,} rows across {cols} columns"


class DatasetSchemaResource(BaseResource):
    """
    Dataset schema with column types.

    URI Pattern: data://{org}/datasets/{id}/schema
    Scope: data:read
    """

    resource_type = "dataset_schema"
    uri_template = "data://{org}/datasets/{id}/schema"
    description = "Get dataset schema with column types and statistics"
    required_scope = "data:read"

    async def fetch(
        self,
        uri: str,
        claims: Optional[MCPTokenClaims],
    ) -> Dict[str, Any]:
        """Fetch dataset schema."""
        params = self._parse_uri_params(uri)
        dataset_id = params.get("id", "")

        if not dataset_id:
            raise MCPError(
                code=MCPErrorCode.INVALID_PARAMS,
                message="Dataset ID is required",
            )

        schema = await self._get_schema(dataset_id, claims.org_id if claims else "")

        if not schema:
            raise resource_not_found("Dataset", dataset_id)

        return schema

    async def _get_schema(
        self,
        dataset_id: str,
        org_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get schema from database."""
        if not self.db:
            # Mock data
            return {
                "dataset_id": dataset_id,
                "dataset_name": "Sales Data 2024",
                "columns": [
                    {
                        "name": "date",
                        "type": "datetime",
                        "nullable": False,
                        "description": "Transaction date",
                        "sample_values": ["2024-01-01", "2024-01-02"],
                    },
                    {
                        "name": "revenue",
                        "type": "float",
                        "nullable": False,
                        "description": "Daily revenue in USD",
                        "statistics": {
                            "min": 1000.0,
                            "max": 50000.0,
                            "mean": 15000.0,
                            "std": 8000.0,
                        },
                    },
                    {
                        "name": "channel",
                        "type": "string",
                        "nullable": False,
                        "description": "Marketing channel",
                        "unique_values": ["organic", "paid_search", "social", "email"],
                    },
                ],
                "primary_key": ["date"],
                "row_count": 52000,
                "recommendations": [
                    "Use 'date' as time index for forecasting",
                    "Consider normalizing 'revenue' for model training",
                ],
            }

        # Real database query
        from sqlalchemy import select
        from app.infrastructure.database.models.dataset import Dataset

        async with self.db() as session:
            result = await session.execute(
                select(Dataset).where(
                    Dataset.id == UUID(dataset_id),
                    Dataset.organization_id == UUID(org_id),
                )
            )
            dataset = result.scalar_one_or_none()

            if not dataset:
                return None

            schema_info = dataset.schema_info or {}

            return {
                "dataset_id": str(dataset.id),
                "dataset_name": dataset.name,
                "columns": schema_info.get("columns", []),
                "primary_key": schema_info.get("primary_key", []),
                "row_count": dataset.row_count or 0,
                "recommendations": self._generate_schema_recommendations(schema_info),
            }

    def _generate_schema_recommendations(
        self,
        schema_info: Dict[str, Any],
    ) -> List[str]:
        """Generate schema recommendations."""
        recommendations = []
        columns = schema_info.get("columns", [])

        # Find date columns
        date_cols = [c for c in columns if c.get("type") in ("datetime", "date")]
        if date_cols:
            recommendations.append(
                f"Use '{date_cols[0].get('name')}' as time index for forecasting"
            )

        # Find numeric columns
        numeric_cols = [c for c in columns if c.get("type") in ("float", "int", "numeric")]
        if numeric_cols:
            recommendations.append(
                f"Found {len(numeric_cols)} numeric columns suitable for analysis"
            )

        return recommendations


class DatasetQualityResource(BaseResource):
    """
    Data quality report with insights.

    URI Pattern: data://{org}/datasets/{id}/quality
    Scope: data:read
    """

    resource_type = "dataset_quality"
    uri_template = "data://{org}/datasets/{id}/quality"
    description = "Get data quality report with insights and recommendations"
    required_scope = "data:read"

    async def fetch(
        self,
        uri: str,
        claims: Optional[MCPTokenClaims],
    ) -> Dict[str, Any]:
        """Fetch quality report."""
        params = self._parse_uri_params(uri)
        dataset_id = params.get("id", "")

        if not dataset_id:
            raise MCPError(
                code=MCPErrorCode.INVALID_PARAMS,
                message="Dataset ID is required",
            )

        quality = await self._get_quality_report(
            dataset_id, claims.org_id if claims else ""
        )

        if not quality:
            raise resource_not_found("Dataset", dataset_id)

        # Format with insight formatter
        return format_data_quality(quality)

    async def _get_quality_report(
        self,
        dataset_id: str,
        org_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get quality report from database or compute."""
        if not self.db:
            # Mock data
            return {
                "completeness": 0.98,
                "validity": 0.95,
                "consistency": 0.97,
                "uniqueness": 0.99,
                "column_issues": [
                    {"column": "email", "issue": "5 invalid email formats"},
                    {"column": "date", "issue": "2 missing values"},
                ],
            }

        # Real implementation would query from quality service
        # For now, return mock data
        return {
            "completeness": 0.95,
            "validity": 0.92,
            "consistency": 0.88,
            "uniqueness": 0.99,
        }


class DatasetPreviewResource(BaseResource):
    """
    Sample rows from dataset.

    URI Pattern: data://{org}/datasets/{id}/preview
    Scope: data:read
    """

    resource_type = "dataset_preview"
    uri_template = "data://{org}/datasets/{id}/preview"
    description = "Get sample rows from dataset (max 10 rows)"
    required_scope = "data:read"

    async def fetch(
        self,
        uri: str,
        claims: Optional[MCPTokenClaims],
    ) -> Dict[str, Any]:
        """Fetch data preview."""
        params = self._parse_uri_params(uri)
        dataset_id = params.get("id", "")

        if not dataset_id:
            raise MCPError(
                code=MCPErrorCode.INVALID_PARAMS,
                message="Dataset ID is required",
            )

        preview = await self._get_preview(dataset_id, claims.org_id if claims else "")

        if not preview:
            raise resource_not_found("Dataset", dataset_id)

        return preview

    async def _get_preview(
        self,
        dataset_id: str,
        org_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get preview from database."""
        max_rows = min(10, self.settings.MCP_MAX_PREVIEW_ROWS)

        if not self.db:
            # Mock data
            return {
                "dataset_id": dataset_id,
                "columns": ["date", "revenue", "channel", "impressions"],
                "rows": [
                    ["2024-01-01", 15000.0, "organic", 50000],
                    ["2024-01-02", 18000.0, "paid_search", 75000],
                    ["2024-01-03", 12000.0, "social", 30000],
                ],
                "total_rows": 52000,
                "preview_rows": 3,
                "note": f"Showing first {max_rows} rows of 52,000 total",
            }

        # Real implementation would query actual data
        return {
            "dataset_id": dataset_id,
            "columns": [],
            "rows": [],
            "total_rows": 0,
            "preview_rows": 0,
        }
