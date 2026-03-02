"""Branding and User Preferences queries."""

from typing import Optional
from uuid import UUID

import strawberry
import structlog
from sqlalchemy import select
from strawberry.types import Info

from app.api.graphql.context import get_db_session, get_current_user_from_context
from app.api.graphql.types.branding import (
    OrganizationBrandingType,
    ThemePresetType,
    UserPreferencesType,
)
from app.core.exceptions import NotFoundError
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
class BrandingQuery:
    """Branding and preferences queries."""

    @strawberry.field
    async def organization_branding(
        self,
        info: Info,
        organization_id: Optional[UUID] = None,
    ) -> Optional[OrganizationBrandingType]:
        """Get organization branding. If no ID provided, returns current user's organization branding."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Determine which organization to fetch
        org_id = organization_id or current_user.organization_id

        if not org_id:
            return None

        # Non-superusers can only view their own org's branding
        if not current_user.is_superuser and org_id != current_user.organization_id:
            return None

        result = await db.execute(
            select(OrganizationBranding).where(
                OrganizationBranding.organization_id == org_id,
                OrganizationBranding.is_active == True,
            )
        )
        branding = result.scalar_one_or_none()

        if not branding:
            return None

        return branding_to_graphql(branding)

    @strawberry.field
    async def theme_presets(
        self,
        info: Info,
        category: Optional[str] = None,
        is_dark: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ThemePresetType]:
        """Get available theme presets."""
        db = await get_db_session(info)
        await get_current_user_from_context(info, db)

        query = select(ThemePreset).where(ThemePreset.is_active == True)

        if category is not None:
            query = query.where(ThemePreset.category == category)

        if is_dark is not None:
            query = query.where(ThemePreset.is_dark == is_dark)

        query = query.order_by(ThemePreset.name).offset(offset).limit(limit)

        result = await db.execute(query)
        presets = result.scalars().all()

        return [theme_preset_to_graphql(p) for p in presets]

    @strawberry.field
    async def theme_preset(
        self,
        info: Info,
        preset_id: UUID,
    ) -> ThemePresetType:
        """Get a specific theme preset by ID."""
        db = await get_db_session(info)
        await get_current_user_from_context(info, db)

        result = await db.execute(
            select(ThemePreset).where(
                ThemePreset.id == preset_id,
                ThemePreset.is_active == True,
            )
        )
        preset = result.scalar_one_or_none()

        if not preset:
            raise NotFoundError("Theme preset", str(preset_id))

        return theme_preset_to_graphql(preset)

    @strawberry.field
    async def user_preferences(
        self,
        info: Info,
    ) -> Optional[UserPreferencesType]:
        """Get current user's preferences."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        result = await db.execute(
            select(UserPreferences).where(
                UserPreferences.user_id == current_user.id
            )
        )
        preferences = result.scalar_one_or_none()

        if not preferences:
            return None

        return preferences_to_graphql(preferences)

    @strawberry.field
    async def theme_categories(self) -> list[str]:
        """Get list of available theme categories."""
        return [
            "professional",
            "modern",
            "minimal",
            "colorful",
            "dark",
            "light",
            "custom",
        ]

    @strawberry.field
    async def supported_languages(self) -> list[str]:
        """Get list of supported languages."""
        return [
            "en",
            "es",
            "fr",
            "de",
            "pt",
            "it",
            "nl",
            "ja",
            "zh",
            "ko",
        ]

    @strawberry.field
    async def supported_currencies(self) -> list[str]:
        """Get list of supported currencies."""
        return [
            "USD",
            "EUR",
            "GBP",
            "JPY",
            "CNY",
            "INR",
            "CAD",
            "AUD",
            "CHF",
            "BRL",
        ]

    @strawberry.field
    async def supported_timezones(self) -> list[str]:
        """Get list of commonly used timezones."""
        return [
            "UTC",
            "America/New_York",
            "America/Chicago",
            "America/Denver",
            "America/Los_Angeles",
            "Europe/London",
            "Europe/Paris",
            "Europe/Berlin",
            "Asia/Tokyo",
            "Asia/Shanghai",
            "Asia/Kolkata",
            "Australia/Sydney",
            "Pacific/Auckland",
        ]
