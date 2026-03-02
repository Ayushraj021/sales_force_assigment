"""Branding and User Preferences mutations."""

from uuid import uuid4

import strawberry
import structlog
from sqlalchemy import select
from strawberry.types import Info

from app.api.graphql.context import get_db_session, get_current_user_from_context
from app.api.graphql.types.branding import (
    CreateThemePresetInput,
    OrganizationBrandingType,
    ThemePresetType,
    UpdateOrganizationBrandingInput,
    UpdateUserPreferencesInput,
    UserPreferencesType,
)
from app.core.exceptions import AuthorizationError, NotFoundError, ValidationError
from app.infrastructure.database.models.branding import (
    OrganizationBranding,
    ThemePreset,
    UserPreferences,
)

logger = structlog.get_logger()


def branding_to_graphql(branding: OrganizationBranding) -> OrganizationBrandingType:
    """Convert organization branding to GraphQL type."""
    return OrganizationBrandingType(
        id=branding.id,
        organization_id=branding.organization_id,
        company_name=branding.company_name,
        tagline=branding.tagline,
        logo_url=branding.logo_url,
        logo_dark_url=branding.logo_dark_url,
        favicon_url=branding.favicon_url,
        logo_width=branding.logo_width,
        primary_color=branding.primary_color,
        secondary_color=branding.secondary_color,
        accent_color=branding.accent_color,
        success_color=branding.success_color,
        warning_color=branding.warning_color,
        error_color=branding.error_color,
        background_color=branding.background_color,
        background_dark_color=branding.background_dark_color,
        sidebar_color=branding.sidebar_color,
        sidebar_dark_color=branding.sidebar_dark_color,
        font_family=branding.font_family,
        heading_font_family=branding.heading_font_family,
        font_size_base=branding.font_size_base,
        border_radius=branding.border_radius,
        custom_css=branding.custom_css,
        email_logo_url=branding.email_logo_url,
        email_footer_text=branding.email_footer_text,
        email_primary_color=branding.email_primary_color,
        report_logo_url=branding.report_logo_url,
        report_header_color=branding.report_header_color,
        report_footer_text=branding.report_footer_text,
        landing_page_enabled=branding.landing_page_enabled or False,
        landing_page_config=branding.landing_page_config,
        show_powered_by=branding.show_powered_by if branding.show_powered_by is not None else True,
        custom_domain_enabled=branding.custom_domain_enabled or False,
        is_active=branding.is_active if branding.is_active is not None else True,
        created_at=branding.created_at,
        updated_at=branding.updated_at,
    )


def theme_preset_to_graphql(preset: ThemePreset) -> ThemePresetType:
    """Convert theme preset to GraphQL type."""
    return ThemePresetType(
        id=preset.id,
        name=preset.name,
        description=preset.description,
        is_dark=preset.is_dark or False,
        is_system=preset.is_system if preset.is_system is not None else True,
        colors=preset.colors,
        typography=preset.typography,
        spacing=preset.spacing,
        border_radius=preset.border_radius,
        preview_image_url=preset.preview_image_url,
        category=preset.category,
        is_active=preset.is_active if preset.is_active is not None else True,
        created_at=preset.created_at,
    )


def preferences_to_graphql(prefs: UserPreferences) -> UserPreferencesType:
    """Convert user preferences to GraphQL type."""
    return UserPreferencesType(
        id=prefs.id,
        user_id=prefs.user_id,
        theme_mode=prefs.theme_mode or "system",
        theme_preset_id=prefs.theme_preset_id,
        custom_colors=prefs.custom_colors,
        sidebar_collapsed=prefs.sidebar_collapsed or False,
        compact_mode=prefs.compact_mode or False,
        show_tooltips=prefs.show_tooltips if prefs.show_tooltips is not None else True,
        default_dashboard_id=prefs.default_dashboard_id,
        chart_animation_enabled=prefs.chart_animation_enabled if prefs.chart_animation_enabled is not None else True,
        table_rows_per_page=prefs.table_rows_per_page or "25",
        email_notifications=prefs.email_notifications if prefs.email_notifications is not None else True,
        push_notifications=prefs.push_notifications or False,
        notification_frequency=prefs.notification_frequency or "daily",
        timezone=prefs.timezone or "UTC",
        date_format=prefs.date_format or "YYYY-MM-DD",
        time_format=prefs.time_format or "24h",
        language=prefs.language or "en",
        currency=prefs.currency or "USD",
        number_format=prefs.number_format or "en-US",
        reduced_motion=prefs.reduced_motion or False,
        high_contrast=prefs.high_contrast or False,
        font_size_adjustment=prefs.font_size_adjustment or "0",
        keyboard_shortcuts_enabled=prefs.keyboard_shortcuts_enabled if prefs.keyboard_shortcuts_enabled is not None else True,
        custom_shortcuts=prefs.custom_shortcuts,
        created_at=prefs.created_at,
        updated_at=prefs.updated_at,
    )


@strawberry.type
class BrandingMutation:
    """Branding and preferences mutations."""

    @strawberry.mutation
    async def update_organization_branding(
        self,
        info: Info,
        input: UpdateOrganizationBrandingInput,
    ) -> OrganizationBrandingType:
        """Update organization branding (admin only)."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Check admin permission
        if not current_user.is_superuser and not current_user.has_role("admin"):
            raise AuthorizationError("Only admins can update organization branding")

        if not current_user.organization_id:
            raise ValidationError("User must belong to an organization")

        # Get or create branding
        result = await db.execute(
            select(OrganizationBranding).where(
                OrganizationBranding.organization_id == current_user.organization_id
            )
        )
        branding = result.scalar_one_or_none()

        if not branding:
            # Create new branding
            branding = OrganizationBranding(
                id=uuid4(),
                organization_id=current_user.organization_id,
            )
            db.add(branding)

        # Update fields
        if input.company_name is not None:
            branding.company_name = input.company_name
        if input.tagline is not None:
            branding.tagline = input.tagline
        if input.logo_url is not None:
            branding.logo_url = input.logo_url
        if input.logo_dark_url is not None:
            branding.logo_dark_url = input.logo_dark_url
        if input.favicon_url is not None:
            branding.favicon_url = input.favicon_url
        if input.logo_width is not None:
            branding.logo_width = input.logo_width
        if input.primary_color is not None:
            branding.primary_color = input.primary_color
        if input.secondary_color is not None:
            branding.secondary_color = input.secondary_color
        if input.accent_color is not None:
            branding.accent_color = input.accent_color
        if input.success_color is not None:
            branding.success_color = input.success_color
        if input.warning_color is not None:
            branding.warning_color = input.warning_color
        if input.error_color is not None:
            branding.error_color = input.error_color
        if input.background_color is not None:
            branding.background_color = input.background_color
        if input.background_dark_color is not None:
            branding.background_dark_color = input.background_dark_color
        if input.sidebar_color is not None:
            branding.sidebar_color = input.sidebar_color
        if input.sidebar_dark_color is not None:
            branding.sidebar_dark_color = input.sidebar_dark_color
        if input.font_family is not None:
            branding.font_family = input.font_family
        if input.heading_font_family is not None:
            branding.heading_font_family = input.heading_font_family
        if input.font_size_base is not None:
            branding.font_size_base = input.font_size_base
        if input.border_radius is not None:
            branding.border_radius = input.border_radius
        if input.custom_css is not None:
            branding.custom_css = input.custom_css
        if input.email_logo_url is not None:
            branding.email_logo_url = input.email_logo_url
        if input.email_footer_text is not None:
            branding.email_footer_text = input.email_footer_text
        if input.email_primary_color is not None:
            branding.email_primary_color = input.email_primary_color
        if input.report_logo_url is not None:
            branding.report_logo_url = input.report_logo_url
        if input.report_header_color is not None:
            branding.report_header_color = input.report_header_color
        if input.report_footer_text is not None:
            branding.report_footer_text = input.report_footer_text
        if input.landing_page_enabled is not None:
            branding.landing_page_enabled = input.landing_page_enabled
        if input.landing_page_config is not None:
            branding.landing_page_config = input.landing_page_config
        if input.show_powered_by is not None:
            branding.show_powered_by = input.show_powered_by
        if input.custom_domain_enabled is not None:
            branding.custom_domain_enabled = input.custom_domain_enabled

        await db.commit()
        await db.refresh(branding)

        logger.info(
            "Organization branding updated",
            organization_id=str(current_user.organization_id),
            updated_by=str(current_user.id),
        )

        return branding_to_graphql(branding)

    @strawberry.mutation
    async def reset_organization_branding(
        self,
        info: Info,
    ) -> OrganizationBrandingType:
        """Reset organization branding to defaults (admin only)."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Check admin permission
        if not current_user.is_superuser and not current_user.has_role("admin"):
            raise AuthorizationError("Only admins can reset organization branding")

        if not current_user.organization_id:
            raise ValidationError("User must belong to an organization")

        # Get branding
        result = await db.execute(
            select(OrganizationBranding).where(
                OrganizationBranding.organization_id == current_user.organization_id
            )
        )
        branding = result.scalar_one_or_none()

        if not branding:
            raise NotFoundError("Organization branding", str(current_user.organization_id))

        # Reset to defaults
        branding.company_name = None
        branding.tagline = None
        branding.logo_url = None
        branding.logo_dark_url = None
        branding.favicon_url = None
        branding.logo_width = None
        branding.primary_color = "#6366f1"
        branding.secondary_color = "#8b5cf6"
        branding.accent_color = None
        branding.success_color = "#10b981"
        branding.warning_color = "#f59e0b"
        branding.error_color = "#ef4444"
        branding.background_color = None
        branding.background_dark_color = None
        branding.sidebar_color = None
        branding.sidebar_dark_color = None
        branding.font_family = "Inter"
        branding.heading_font_family = None
        branding.font_size_base = "16px"
        branding.border_radius = "0.5rem"
        branding.custom_css = None
        branding.email_logo_url = None
        branding.email_footer_text = None
        branding.email_primary_color = None
        branding.report_logo_url = None
        branding.report_header_color = None
        branding.report_footer_text = None
        branding.landing_page_enabled = False
        branding.landing_page_config = None
        branding.show_powered_by = True
        branding.custom_domain_enabled = False

        await db.commit()
        await db.refresh(branding)

        logger.info(
            "Organization branding reset to defaults",
            organization_id=str(current_user.organization_id),
            reset_by=str(current_user.id),
        )

        return branding_to_graphql(branding)

    @strawberry.mutation
    async def update_user_preferences(
        self,
        info: Info,
        input: UpdateUserPreferencesInput,
    ) -> UserPreferencesType:
        """Update current user's preferences."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Get or create preferences
        result = await db.execute(
            select(UserPreferences).where(
                UserPreferences.user_id == current_user.id
            )
        )
        preferences = result.scalar_one_or_none()

        if not preferences:
            # Create new preferences
            preferences = UserPreferences(
                id=uuid4(),
                user_id=current_user.id,
            )
            db.add(preferences)

        # Update fields
        if input.theme_mode is not None:
            if input.theme_mode not in ["light", "dark", "system"]:
                raise ValidationError("theme_mode must be 'light', 'dark', or 'system'")
            preferences.theme_mode = input.theme_mode
        if input.theme_preset_id is not None:
            preferences.theme_preset_id = input.theme_preset_id
        if input.custom_colors is not None:
            preferences.custom_colors = input.custom_colors
        if input.sidebar_collapsed is not None:
            preferences.sidebar_collapsed = input.sidebar_collapsed
        if input.compact_mode is not None:
            preferences.compact_mode = input.compact_mode
        if input.show_tooltips is not None:
            preferences.show_tooltips = input.show_tooltips
        if input.default_dashboard_id is not None:
            preferences.default_dashboard_id = input.default_dashboard_id
        if input.chart_animation_enabled is not None:
            preferences.chart_animation_enabled = input.chart_animation_enabled
        if input.table_rows_per_page is not None:
            preferences.table_rows_per_page = input.table_rows_per_page
        if input.email_notifications is not None:
            preferences.email_notifications = input.email_notifications
        if input.push_notifications is not None:
            preferences.push_notifications = input.push_notifications
        if input.notification_frequency is not None:
            preferences.notification_frequency = input.notification_frequency
        if input.timezone is not None:
            preferences.timezone = input.timezone
        if input.date_format is not None:
            preferences.date_format = input.date_format
        if input.time_format is not None:
            preferences.time_format = input.time_format
        if input.language is not None:
            preferences.language = input.language
        if input.currency is not None:
            preferences.currency = input.currency
        if input.number_format is not None:
            preferences.number_format = input.number_format
        if input.reduced_motion is not None:
            preferences.reduced_motion = input.reduced_motion
        if input.high_contrast is not None:
            preferences.high_contrast = input.high_contrast
        if input.font_size_adjustment is not None:
            preferences.font_size_adjustment = input.font_size_adjustment
        if input.keyboard_shortcuts_enabled is not None:
            preferences.keyboard_shortcuts_enabled = input.keyboard_shortcuts_enabled
        if input.custom_shortcuts is not None:
            preferences.custom_shortcuts = input.custom_shortcuts

        await db.commit()
        await db.refresh(preferences)

        logger.info(
            "User preferences updated",
            user_id=str(current_user.id),
        )

        return preferences_to_graphql(preferences)

    @strawberry.mutation
    async def reset_user_preferences(
        self,
        info: Info,
    ) -> UserPreferencesType:
        """Reset current user's preferences to defaults."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Get preferences
        result = await db.execute(
            select(UserPreferences).where(
                UserPreferences.user_id == current_user.id
            )
        )
        preferences = result.scalar_one_or_none()

        if not preferences:
            # Create new preferences with defaults
            preferences = UserPreferences(
                id=uuid4(),
                user_id=current_user.id,
            )
            db.add(preferences)
        else:
            # Reset to defaults
            preferences.theme_mode = "system"
            preferences.theme_preset_id = None
            preferences.custom_colors = None
            preferences.sidebar_collapsed = False
            preferences.compact_mode = False
            preferences.show_tooltips = True
            preferences.default_dashboard_id = None
            preferences.chart_animation_enabled = True
            preferences.table_rows_per_page = "25"
            preferences.email_notifications = True
            preferences.push_notifications = False
            preferences.notification_frequency = "daily"
            preferences.timezone = "UTC"
            preferences.date_format = "YYYY-MM-DD"
            preferences.time_format = "24h"
            preferences.language = "en"
            preferences.currency = "USD"
            preferences.number_format = "en-US"
            preferences.reduced_motion = False
            preferences.high_contrast = False
            preferences.font_size_adjustment = "0"
            preferences.keyboard_shortcuts_enabled = True
            preferences.custom_shortcuts = None

        await db.commit()
        await db.refresh(preferences)

        logger.info(
            "User preferences reset to defaults",
            user_id=str(current_user.id),
        )

        return preferences_to_graphql(preferences)

    @strawberry.mutation
    async def create_theme_preset(
        self,
        info: Info,
        input: CreateThemePresetInput,
    ) -> ThemePresetType:
        """Create a new theme preset (superuser only)."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Only superusers can create system presets
        if not current_user.is_superuser:
            raise AuthorizationError("Only superusers can create theme presets")

        # Validate name
        if not input.name or len(input.name.strip()) == 0:
            raise ValidationError("Theme preset name is required")

        # Check for duplicate name
        result = await db.execute(
            select(ThemePreset).where(ThemePreset.name == input.name.strip())
        )
        if result.scalar_one_or_none():
            raise ValidationError(f"Theme preset '{input.name}' already exists")

        # Create preset
        preset = ThemePreset(
            id=uuid4(),
            name=input.name.strip(),
            description=input.description,
            is_dark=input.is_dark,
            is_system=True,
            colors=input.colors,
            typography=input.typography,
            spacing=input.spacing,
            border_radius=input.border_radius,
            preview_image_url=input.preview_image_url,
            category=input.category,
        )
        db.add(preset)

        await db.commit()
        await db.refresh(preset)

        logger.info(
            "Theme preset created",
            preset_id=str(preset.id),
            preset_name=preset.name,
            created_by=str(current_user.id),
        )

        return theme_preset_to_graphql(preset)

    @strawberry.mutation
    async def delete_theme_preset(
        self,
        info: Info,
        preset_id: strawberry.ID,
    ) -> bool:
        """Delete a theme preset (superuser only)."""
        from uuid import UUID

        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Only superusers can delete presets
        if not current_user.is_superuser:
            raise AuthorizationError("Only superusers can delete theme presets")

        # Get preset
        result = await db.execute(
            select(ThemePreset).where(ThemePreset.id == UUID(str(preset_id)))
        )
        preset = result.scalar_one_or_none()

        if not preset:
            raise NotFoundError("Theme preset", str(preset_id))

        await db.delete(preset)
        await db.commit()

        logger.info(
            "Theme preset deleted",
            preset_id=str(preset_id),
            deleted_by=str(current_user.id),
        )

        return True
