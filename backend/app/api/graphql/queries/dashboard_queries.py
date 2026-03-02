"""Dashboard Layout queries."""

from typing import Optional
from uuid import UUID

import strawberry
import structlog
from sqlalchemy import select, or_
from strawberry.types import Info

from app.api.graphql.context import get_db_session, get_current_user_from_context
from app.api.graphql.types.dashboard import (
    DashboardLayoutFilterInput,
    DashboardLayoutType,
    WidgetTemplateType,
)
from app.core.exceptions import NotFoundError
from app.infrastructure.database.models.experiments import DashboardLayout

logger = structlog.get_logger()


def dashboard_to_graphql(dashboard: DashboardLayout) -> DashboardLayoutType:
    """Convert dashboard layout to GraphQL type."""
    return DashboardLayoutType(
        id=dashboard.id,
        name=dashboard.name,
        description=dashboard.description,
        layout=dashboard.layout,
        widgets=dashboard.widgets,
        is_default=dashboard.is_default or False,
        is_shared=dashboard.is_shared or False,
        user_id=dashboard.user_id,
        organization_id=dashboard.organization_id,
        created_at=dashboard.created_at,
        updated_at=dashboard.updated_at,
    )


@strawberry.type
class DashboardQuery:
    """Dashboard Layout queries."""

    @strawberry.field
    async def dashboard_layouts(
        self,
        info: Info,
        filter: Optional[DashboardLayoutFilterInput] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DashboardLayoutType]:
        """Get dashboard layouts visible to the current user."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Base query: user's own layouts OR shared layouts in their org
        query = select(DashboardLayout).where(
            or_(
                DashboardLayout.user_id == current_user.id,
                (
                    DashboardLayout.is_shared == True,
                    DashboardLayout.organization_id == current_user.organization_id,
                ),
            )
        )

        # Apply filters
        if filter:
            if filter.is_shared is not None:
                query = query.where(DashboardLayout.is_shared == filter.is_shared)
            if filter.is_default is not None:
                query = query.where(DashboardLayout.is_default == filter.is_default)
            if filter.created_by_me is not None:
                if filter.created_by_me:
                    query = query.where(DashboardLayout.user_id == current_user.id)
                else:
                    query = query.where(DashboardLayout.user_id != current_user.id)

        # Order by name and paginate
        query = query.order_by(DashboardLayout.name).offset(offset).limit(limit)

        result = await db.execute(query)
        layouts = result.scalars().all()

        return [dashboard_to_graphql(l) for l in layouts]

    @strawberry.field
    async def dashboard_layout(
        self,
        info: Info,
        dashboard_id: UUID,
    ) -> DashboardLayoutType:
        """Get a specific dashboard layout by ID."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        result = await db.execute(
            select(DashboardLayout).where(DashboardLayout.id == dashboard_id)
        )
        layout = result.scalar_one_or_none()

        if not layout:
            raise NotFoundError("Dashboard layout", str(dashboard_id))

        # Check access
        if layout.user_id != current_user.id:
            if not layout.is_shared:
                raise NotFoundError("Dashboard layout", str(dashboard_id))
            if layout.organization_id != current_user.organization_id:
                raise NotFoundError("Dashboard layout", str(dashboard_id))

        return dashboard_to_graphql(layout)

    @strawberry.field
    async def my_default_dashboard(
        self,
        info: Info,
    ) -> Optional[DashboardLayoutType]:
        """Get the current user's default dashboard layout."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        result = await db.execute(
            select(DashboardLayout).where(
                DashboardLayout.user_id == current_user.id,
                DashboardLayout.is_default == True,
            )
        )
        layout = result.scalar_one_or_none()

        if not layout:
            return None

        return dashboard_to_graphql(layout)

    @strawberry.field
    async def shared_dashboard_layouts(
        self,
        info: Info,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DashboardLayoutType]:
        """Get shared dashboard layouts in the organization."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        query = select(DashboardLayout).where(
            DashboardLayout.is_shared == True,
            DashboardLayout.organization_id == current_user.organization_id,
        ).order_by(DashboardLayout.name).offset(offset).limit(limit)

        result = await db.execute(query)
        layouts = result.scalars().all()

        return [dashboard_to_graphql(l) for l in layouts]

    @strawberry.field
    async def widget_templates(self) -> list[WidgetTemplateType]:
        """Get available widget templates."""
        # Predefined widget templates
        return [
            WidgetTemplateType(
                id="kpi_card",
                name="KPI Card",
                description="Display a single key performance indicator",
                widget_type="kpi",
                category="metrics",
                default_config={"metric": "", "format": "number", "comparison": "previous_period"},
                preview_image_url=None,
            ),
            WidgetTemplateType(
                id="line_chart",
                name="Line Chart",
                description="Time series data visualization",
                widget_type="chart",
                category="charts",
                default_config={"chart_type": "line", "x_axis": "date", "y_axis": []},
                preview_image_url=None,
            ),
            WidgetTemplateType(
                id="bar_chart",
                name="Bar Chart",
                description="Categorical data comparison",
                widget_type="chart",
                category="charts",
                default_config={"chart_type": "bar", "orientation": "vertical"},
                preview_image_url=None,
            ),
            WidgetTemplateType(
                id="pie_chart",
                name="Pie Chart",
                description="Part-to-whole data visualization",
                widget_type="chart",
                category="charts",
                default_config={"chart_type": "pie", "show_legend": True},
                preview_image_url=None,
            ),
            WidgetTemplateType(
                id="data_table",
                name="Data Table",
                description="Tabular data display with sorting and filtering",
                widget_type="table",
                category="tables",
                default_config={"columns": [], "page_size": 10, "sortable": True},
                preview_image_url=None,
            ),
            WidgetTemplateType(
                id="attribution_chart",
                name="Attribution Chart",
                description="Channel attribution breakdown",
                widget_type="attribution",
                category="analytics",
                default_config={"model_id": "", "chart_type": "bar"},
                preview_image_url=None,
            ),
            WidgetTemplateType(
                id="forecast_chart",
                name="Forecast Chart",
                description="Time series forecast with confidence intervals",
                widget_type="forecast",
                category="analytics",
                default_config={"forecast_id": "", "show_confidence": True},
                preview_image_url=None,
            ),
            WidgetTemplateType(
                id="geo_map",
                name="Geographic Map",
                description="Geographic data visualization",
                widget_type="map",
                category="charts",
                default_config={"map_type": "choropleth", "region": "us"},
                preview_image_url=None,
            ),
            WidgetTemplateType(
                id="text_block",
                name="Text Block",
                description="Rich text content block",
                widget_type="text",
                category="content",
                default_config={"content": "", "format": "markdown"},
                preview_image_url=None,
            ),
            WidgetTemplateType(
                id="heatmap",
                name="Heatmap",
                description="Two-dimensional data heatmap",
                widget_type="chart",
                category="charts",
                default_config={"chart_type": "heatmap", "color_scale": "viridis"},
                preview_image_url=None,
            ),
        ]

    @strawberry.field
    async def widget_categories(self) -> list[str]:
        """Get list of widget categories."""
        return [
            "metrics",
            "charts",
            "tables",
            "analytics",
            "content",
        ]
