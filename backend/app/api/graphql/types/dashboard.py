"""Dashboard Layout GraphQL types."""

from datetime import datetime
from typing import Optional
from uuid import UUID

import strawberry
from strawberry.scalars import JSON


@strawberry.type
class DashboardLayoutType:
    """Dashboard layout type."""

    id: UUID
    name: str
    description: Optional[str]

    # Layout configuration
    layout: JSON  # react-grid-layout format
    widgets: JSON  # Widget configurations

    # Settings
    is_default: bool
    is_shared: bool

    # Ownership
    user_id: Optional[UUID]
    organization_id: Optional[UUID]

    # Timestamps
    created_at: datetime
    updated_at: datetime


@strawberry.type
class DashboardWidgetType:
    """Dashboard widget type."""

    id: str
    widget_type: str  # chart, kpi, table, etc.
    title: str
    config: JSON
    position: JSON  # {x, y, w, h}


@strawberry.input
class CreateDashboardLayoutInput:
    """Input for creating a dashboard layout."""

    name: str
    description: Optional[str] = None
    layout: JSON  # react-grid-layout items
    widgets: JSON  # Widget configurations
    is_default: bool = False
    is_shared: bool = False


@strawberry.input
class UpdateDashboardLayoutInput:
    """Input for updating a dashboard layout."""

    name: Optional[str] = None
    description: Optional[str] = None
    layout: Optional[JSON] = None
    widgets: Optional[JSON] = None
    is_default: Optional[bool] = None
    is_shared: Optional[bool] = None


@strawberry.input
class DashboardLayoutFilterInput:
    """Input for filtering dashboard layouts."""

    is_shared: Optional[bool] = None
    is_default: Optional[bool] = None
    created_by_me: Optional[bool] = None


@strawberry.input
class WidgetPositionInput:
    """Input for widget position."""

    widget_id: str
    x: int
    y: int
    w: int
    h: int


@strawberry.input
class UpdateLayoutPositionsInput:
    """Input for updating layout positions."""

    positions: list[WidgetPositionInput]


@strawberry.type
class WidgetTemplateType:
    """Widget template type."""

    id: str
    name: str
    description: str
    widget_type: str
    category: str
    default_config: JSON
    preview_image_url: Optional[str]
