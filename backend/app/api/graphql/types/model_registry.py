"""Model Registry GraphQL types."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

import strawberry
from strawberry.scalars import JSON


@strawberry.enum
class ModelStageEnum(Enum):
    """Model deployment stages."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    ARCHIVED = "archived"


@strawberry.type
class RegistryModelVersionType:
    """A specific version of a model."""
    id: UUID
    model_name: str
    version: str
    model_type: str
    framework: str
    stage: str
    metrics: JSON
    parameters: JSON
    tags: JSON
    description: Optional[str]
    checksum: Optional[str]
    file_size_bytes: Optional[int]
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID]


@strawberry.type
class ModelRegistryEntryType:
    """A model in the registry with all versions."""
    name: str
    latest_version: str
    version_count: int
    production_version: Optional[str]
    staging_version: Optional[str]
    versions: list[RegistryModelVersionType]
    created_at: datetime
    updated_at: datetime


@strawberry.type
class ModelComparisonType:
    """Comparison of model versions."""
    version: str
    stage: str
    metrics: JSON


@strawberry.type
class ModelPromotionResultType:
    """Result of model promotion."""
    success: bool
    model_name: str
    version: str
    from_stage: str
    to_stage: str
    promoted_at: datetime
    message: Optional[str]


@strawberry.input
class RegisterModelInput:
    """Input for registering a model."""
    name: str
    version: Optional[str] = None
    model_type: str = "unknown"
    framework: str = "unknown"
    metrics: Optional[JSON] = None
    parameters: Optional[JSON] = None
    tags: Optional[JSON] = None
    description: Optional[str] = None


@strawberry.input
class UpdateModelVersionInput:
    """Input for updating a model version."""
    description: Optional[str] = None
    tags: Optional[JSON] = None
    metrics: Optional[JSON] = None


@strawberry.input
class PromoteModelInput:
    """Input for promoting a model."""
    model_name: str
    version: str
    stage: str


@strawberry.input
class ModelFilterInput:
    """Input for filtering models in registry."""
    name_contains: Optional[str] = None
    framework: Optional[str] = None
    stage: Optional[str] = None
    model_type: Optional[str] = None
    has_tag: Optional[str] = None


@strawberry.input
class CompareModelsInput:
    """Input for comparing model versions."""
    model_name: str
    versions: list[str]
