"""Dashboard Layout mutations."""

from typing import Optional
from uuid import UUID, uuid4

import strawberry
import structlog
from sqlalchemy import select
from strawberry.types import Info

from app.api.graphql.context import get_db_session, get_current_user_from_context
from app.api.graphql.types.dashboard import (
    CreateDashboardLayoutInput,
    DashboardLayoutType,
    UpdateDashboardLayoutInput,
    UpdateLayoutPositionsInput,
)
from app.core.exceptions import NotFoundError, ValidationError, AuthorizationError
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
class DashboardMutation:
    """Dashboard Layout mutations."""

    @strawberry.mutation
    async def create_dashboard_layout(
        self,
        info: Info,
        input: CreateDashboardLayoutInput,
    ) -> DashboardLayoutType:
        """Create a new dashboard layout."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Validate name
        if not input.name or len(input.name.strip()) == 0:
            raise ValidationError("Dashboard name is required")

        # Validate layout and widgets
        if not input.layout:
            raise ValidationError("Layout configuration is required")
        if not input.widgets:
            raise ValidationError("Widget configurations are required")

        # If setting as default, unset other defaults for this user
        if input.is_default:
            result = await db.execute(
                select(DashboardLayout).where(
                    DashboardLayout.user_id == current_user.id,
                    DashboardLayout.is_default == True,
                )
            )
            for other in result.scalars().all():
                other.is_default = False

        # Create layout
        layout = DashboardLayout(
            id=uuid4(),
            name=input.name.strip(),
            description=input.description,
            layout=input.layout,
            widgets=input.widgets,
            is_default=input.is_default,
            is_shared=input.is_shared,
            user_id=current_user.id,
            organization_id=current_user.organization_id,
        )
        db.add(layout)

        await db.commit()
        await db.refresh(layout)

        logger.info(
            "Dashboard layout created",
            dashboard_id=str(layout.id),
            dashboard_name=layout.name,
            created_by=str(current_user.id),
        )

        return dashboard_to_graphql(layout)

    @strawberry.mutation
    async def update_dashboard_layout(
        self,
        info: Info,
        dashboard_id: UUID,
        input: UpdateDashboardLayoutInput,
    ) -> DashboardLayoutType:
        """Update a dashboard layout."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Get layout
        result = await db.execute(
            select(DashboardLayout).where(DashboardLayout.id == dashboard_id)
        )
        layout = result.scalar_one_or_none()

        if not layout:
            raise NotFoundError("Dashboard layout", str(dashboard_id))

        # Check ownership (only owner can update, unless shared)
        if layout.user_id != current_user.id and not current_user.is_superuser:
            if not layout.is_shared:
                raise AuthorizationError("You can only update your own dashboard layouts")
            # For shared layouts, must be in same organization
            if layout.organization_id != current_user.organization_id:
                raise AuthorizationError("Dashboard layout belongs to a different organization")

        # Update fields
        if input.name is not None:
            if len(input.name.strip()) == 0:
                raise ValidationError("Dashboard name cannot be empty")
            layout.name = input.name.strip()
        if input.description is not None:
            layout.description = input.description
        if input.layout is not None:
            layout.layout = input.layout
        if input.widgets is not None:
            layout.widgets = input.widgets
        if input.is_default is not None:
            # If setting as default, unset other defaults for this user
            if input.is_default:
                other_result = await db.execute(
                    select(DashboardLayout).where(
                        DashboardLayout.user_id == current_user.id,
                        DashboardLayout.is_default == True,
                        DashboardLayout.id != dashboard_id,
                    )
                )
                for other in other_result.scalars().all():
                    other.is_default = False
            layout.is_default = input.is_default
        if input.is_shared is not None:
            layout.is_shared = input.is_shared

        await db.commit()
        await db.refresh(layout)

        logger.info(
            "Dashboard layout updated",
            dashboard_id=str(layout.id),
            updated_by=str(current_user.id),
        )

        return dashboard_to_graphql(layout)

    @strawberry.mutation
    async def delete_dashboard_layout(
        self,
        info: Info,
        dashboard_id: UUID,
    ) -> bool:
        """Delete a dashboard layout."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Get layout
        result = await db.execute(
            select(DashboardLayout).where(DashboardLayout.id == dashboard_id)
        )
        layout = result.scalar_one_or_none()

        if not layout:
            raise NotFoundError("Dashboard layout", str(dashboard_id))

        # Check ownership
        if layout.user_id != current_user.id and not current_user.is_superuser:
            raise AuthorizationError("You can only delete your own dashboard layouts")

        await db.delete(layout)
        await db.commit()

        logger.info(
            "Dashboard layout deleted",
            dashboard_id=str(dashboard_id),
            deleted_by=str(current_user.id),
        )

        return True

    @strawberry.mutation
    async def duplicate_dashboard_layout(
        self,
        info: Info,
        dashboard_id: UUID,
        new_name: Optional[str] = None,
    ) -> DashboardLayoutType:
        """Duplicate a dashboard layout."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Get original layout
        result = await db.execute(
            select(DashboardLayout).where(DashboardLayout.id == dashboard_id)
        )
        original = result.scalar_one_or_none()

        if not original:
            raise NotFoundError("Dashboard layout", str(dashboard_id))

        # Check access (must be owner or shared)
        if original.user_id != current_user.id:
            if not original.is_shared:
                raise AuthorizationError("Cannot duplicate private dashboard layouts")
            if original.organization_id != current_user.organization_id:
                raise AuthorizationError("Dashboard layout belongs to a different organization")

        # Create copy
        name = new_name.strip() if new_name else f"{original.name} (Copy)"

        copy = DashboardLayout(
            id=uuid4(),
            name=name,
            description=original.description,
            layout=original.layout,
            widgets=original.widgets,
            is_default=False,
            is_shared=False,
            user_id=current_user.id,
            organization_id=current_user.organization_id,
        )
        db.add(copy)

        await db.commit()
        await db.refresh(copy)

        logger.info(
            "Dashboard layout duplicated",
            original_id=str(dashboard_id),
            new_id=str(copy.id),
            duplicated_by=str(current_user.id),
        )

        return dashboard_to_graphql(copy)

    @strawberry.mutation
    async def update_layout_positions(
        self,
        info: Info,
        dashboard_id: UUID,
        input: UpdateLayoutPositionsInput,
    ) -> DashboardLayoutType:
        """Update widget positions in a dashboard layout."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Get layout
        result = await db.execute(
            select(DashboardLayout).where(DashboardLayout.id == dashboard_id)
        )
        layout = result.scalar_one_or_none()

        if not layout:
            raise NotFoundError("Dashboard layout", str(dashboard_id))

        # Check ownership
        if layout.user_id != current_user.id and not current_user.is_superuser:
            if not layout.is_shared:
                raise AuthorizationError("You can only update your own dashboard layouts")
            if layout.organization_id != current_user.organization_id:
                raise AuthorizationError("Dashboard layout belongs to a different organization")

        # Update layout positions
        new_layout = []
        for pos in input.positions:
            new_layout.append({
                "i": pos.widget_id,
                "x": pos.x,
                "y": pos.y,
                "w": pos.w,
                "h": pos.h,
            })

        layout.layout = new_layout

        await db.commit()
        await db.refresh(layout)

        logger.info(
            "Dashboard layout positions updated",
            dashboard_id=str(layout.id),
            updated_by=str(current_user.id),
        )

        return dashboard_to_graphql(layout)

    @strawberry.mutation
    async def set_default_dashboard(
        self,
        info: Info,
        dashboard_id: UUID,
    ) -> DashboardLayoutType:
        """Set a dashboard as the default for the current user."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Get layout
        result = await db.execute(
            select(DashboardLayout).where(DashboardLayout.id == dashboard_id)
        )
        layout = result.scalar_one_or_none()

        if not layout:
            raise NotFoundError("Dashboard layout", str(dashboard_id))

        # Check access
        if layout.user_id != current_user.id:
            if not layout.is_shared:
                raise AuthorizationError("Cannot set private dashboard as default")
            if layout.organization_id != current_user.organization_id:
                raise AuthorizationError("Dashboard layout belongs to a different organization")

        # Unset other defaults
        other_result = await db.execute(
            select(DashboardLayout).where(
                DashboardLayout.user_id == current_user.id,
                DashboardLayout.is_default == True,
            )
        )
        for other in other_result.scalars().all():
            other.is_default = False

        # Set this one as default
        layout.is_default = True

        await db.commit()
        await db.refresh(layout)

        logger.info(
            "Default dashboard set",
            dashboard_id=str(layout.id),
            user_id=str(current_user.id),
        )

        return dashboard_to_graphql(layout)
