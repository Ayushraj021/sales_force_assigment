"""
MCP Resources Module.

Provides read-only access to datasets, models, forecasts, and optimization data.
"""

from app.mcp.resources.base import BaseResource, ResourceCache
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
    ModelParametersResource,
)

__all__ = [
    "BaseResource",
    "ResourceCache",
    "DatasetsResource",
    "DatasetSchemaResource",
    "DatasetQualityResource",
    "DatasetPreviewResource",
    "ModelRegistryResource",
    "ModelDetailResource",
    "ModelPerformanceResource",
    "ModelParametersResource",
]
