"""Organization management mutations."""

from typing import Optional
from uuid import UUID

import strawberry
import structlog
from sqlalchemy import select
from strawberry.scalars import JSON
from strawberry.types import Info

from app.api.graphql.context import get_db_session, get_current_user_from_context
from app.api.graphql.types.auth import OrganizationType
from app.core.exceptions import NotFoundError, ValidationError, AuthorizationError
from app.infrastructure.database.models.organization import Organization

logger = structlog.get_logger()


def organization_to_graphql(org: Organization) -> OrganizationType:
    """Convert database organization to GraphQL type."""
    return OrganizationType(
        id=org.id,
        name=org.name,
        slug=org.slug,
        description=org.description,
        is_active=org.is_active,
        subscription_tier=org.subscription_tier,
        max_users=org.max_users,
        max_models=org.max_models,
        max_datasets=org.max_datasets,
        created_at=org.created_at,
        updated_at=org.updated_at,
    )


@strawberry.input
class UpdateOrganizationInput:
    """Input for updating organization settings."""

    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    settings: Optional[JSON] = None


@strawberry.type
class OrganizationMutation:
    """Organization management mutations."""

    @strawberry.mutation
    async def update_organization(
        self,
        info: Info,
        input: UpdateOrganizationInput,
        organization_id: Optional[UUID] = None,
    ) -> OrganizationType:
        """Update organization settings (admin only)."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Check if user has admin permissions
        if not current_user.is_superuser and not current_user.has_role("admin"):
            raise AuthorizationError("Only admins can update organization settings")

        # Determine which organization to update
        target_org_id = organization_id
        if not target_org_id:
            target_org_id = current_user.organization_id

        if not target_org_id:
            raise ValidationError("No organization specified")

        # Non-superusers can only update their own organization
        if not current_user.is_superuser and target_org_id != current_user.organization_id:
            raise AuthorizationError("You can only update your own organization")

        # Get organization
        result = await db.execute(
            select(Organization).where(Organization.id == target_org_id)
        )
        organization = result.scalar_one_or_none()

        if not organization:
            raise NotFoundError("Organization", str(target_org_id))

        # Update fields
        if input.name is not None:
            if len(input.name.strip()) == 0:
                raise ValidationError("Organization name cannot be empty")
            organization.name = input.name.strip()

        if input.slug is not None:
            # Validate slug format
            slug = input.slug.strip().lower()
            if not slug or not slug.replace("-", "").replace("_", "").isalnum():
                raise ValidationError("Invalid slug format. Use only letters, numbers, hyphens, and underscores.")

            # Check if slug is already taken by another org
            result = await db.execute(
                select(Organization).where(
                    Organization.slug == slug,
                    Organization.id != target_org_id,
                )
            )
            if result.scalar_one_or_none():
                raise ValidationError("This slug is already taken")

            organization.slug = slug

        if input.description is not None:
            organization.description = input.description

        if input.settings is not None:
            # Merge new settings with existing
            existing_settings = organization.settings or {}
            organization.settings = {**existing_settings, **input.settings}

        await db.commit()
        await db.refresh(organization)

        logger.info(
            "Organization updated",
            organization_id=str(organization.id),
            updated_by=str(current_user.id),
        )

        return organization_to_graphql(organization)
