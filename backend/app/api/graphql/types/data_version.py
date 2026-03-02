"""DataVersion GraphQL types."""

from datetime import datetime
from typing import Optional
from uuid import UUID

import strawberry
from strawberry.scalars import JSON


@strawberry.type
class DataVersionType:
    """Dataset version type."""

    id: UUID
    version: str
    description: Optional[str]
    is_current: bool

    # DVC tracking
    dvc_hash: Optional[str]
    dvc_path: Optional[str]

    # Changes from previous version
    changes_summary: JSON

    # Statistics
    row_count: Optional[int]
    checksum: Optional[str]

    # Relationship
    dataset_id: UUID

    # Timestamps
    created_at: datetime
    updated_at: datetime


@strawberry.input
class DataVersionFilterInput:
    """Input for filtering data versions."""

    dataset_id: Optional[UUID] = None
    is_current: Optional[bool] = None


@strawberry.type
class DataVersionComparisonType:
    """Comparison between two data versions."""

    from_version: DataVersionType
    to_version: DataVersionType
    row_count_diff: int
    changes_summary: JSON
