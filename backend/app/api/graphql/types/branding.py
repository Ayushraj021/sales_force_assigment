"""Branding and User Preferences GraphQL types."""

from datetime import datetime
from typing import Optional
from uuid import UUID

import strawberry
from strawberry.scalars import JSON


@strawberry.type
class OrganizationBrandingType:
    """Organization branding configuration type."""

    id: UUID
    organization_id: UUID

    # Basic branding
    company_name: Optional[str]
    tagline: Optional[str]

    # Logos
    logo_url: Optional[str]
    logo_dark_url: Optional[str]
    favicon_url: Optional[str]
    logo_width: Optional[str]

    # Colors
    primary_color: Optional[str]
    secondary_color: Optional[str]
    accent_color: Optional[str]
    success_color: Optional[str]
    warning_color: Optional[str]
    error_color: Optional[str]

    # Background colors
    background_color: Optional[str]
    background_dark_color: Optional[str]
    sidebar_color: Optional[str]
    sidebar_dark_color: Optional[str]

    # Typography
    font_family: Optional[str]
    heading_font_family: Optional[str]
    font_size_base: Optional[str]

    # Border radius
    border_radius: Optional[str]

    # Custom CSS
    custom_css: Optional[str]

    # Email branding
    email_logo_url: Optional[str]
    email_footer_text: Optional[str]
    email_primary_color: Optional[str]

    # Report branding
    report_logo_url: Optional[str]
    report_header_color: Optional[str]
    report_footer_text: Optional[str]

    # Landing page
    landing_page_enabled: bool
    landing_page_config: Optional[JSON]

    # Feature flags
    show_powered_by: bool
    custom_domain_enabled: bool

    # Status
    is_active: bool

    # Timestamps
    created_at: datetime
    updated_at: datetime


@strawberry.type
class ThemePresetType:
    """Theme preset type."""

    id: UUID
    name: str
    description: Optional[str]

    # Theme type
    is_dark: bool
    is_system: bool

    # Theme configuration
    colors: JSON
    typography: Optional[JSON]
    spacing: Optional[JSON]
    border_radius: Optional[JSON]

    # Preview
    preview_image_url: Optional[str]

    # Metadata
    category: Optional[str]
    is_active: bool

    # Timestamps
    created_at: datetime


@strawberry.type
class UserPreferencesType:
    """User preferences type."""

    id: UUID
    user_id: UUID

    # Theme preferences
    theme_mode: str
    theme_preset_id: Optional[UUID]
    custom_colors: Optional[JSON]

    # Display preferences
    sidebar_collapsed: bool
    compact_mode: bool
    show_tooltips: bool

    # Dashboard preferences
    default_dashboard_id: Optional[UUID]
    chart_animation_enabled: bool
    table_rows_per_page: str

    # Notification preferences
    email_notifications: bool
    push_notifications: bool
    notification_frequency: str

    # Date/time preferences
    timezone: str
    date_format: str
    time_format: str

    # Locale
    language: str
    currency: str
    number_format: str

    # Accessibility
    reduced_motion: bool
    high_contrast: bool
    font_size_adjustment: str

    # Keyboard shortcuts
    keyboard_shortcuts_enabled: bool
    custom_shortcuts: Optional[JSON]

    # Timestamps
    created_at: datetime
    updated_at: datetime


@strawberry.input
class UpdateOrganizationBrandingInput:
    """Input for updating organization branding."""

    # Basic branding
    company_name: Optional[str] = None
    tagline: Optional[str] = None

    # Logos
    logo_url: Optional[str] = None
    logo_dark_url: Optional[str] = None
    favicon_url: Optional[str] = None
    logo_width: Optional[str] = None

    # Colors
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    accent_color: Optional[str] = None
    success_color: Optional[str] = None
    warning_color: Optional[str] = None
    error_color: Optional[str] = None

    # Background colors
    background_color: Optional[str] = None
    background_dark_color: Optional[str] = None
    sidebar_color: Optional[str] = None
    sidebar_dark_color: Optional[str] = None

    # Typography
    font_family: Optional[str] = None
    heading_font_family: Optional[str] = None
    font_size_base: Optional[str] = None

    # Border radius
    border_radius: Optional[str] = None

    # Custom CSS
    custom_css: Optional[str] = None

    # Email branding
    email_logo_url: Optional[str] = None
    email_footer_text: Optional[str] = None
    email_primary_color: Optional[str] = None

    # Report branding
    report_logo_url: Optional[str] = None
    report_header_color: Optional[str] = None
    report_footer_text: Optional[str] = None

    # Landing page
    landing_page_enabled: Optional[bool] = None
    landing_page_config: Optional[JSON] = None

    # Feature flags
    show_powered_by: Optional[bool] = None
    custom_domain_enabled: Optional[bool] = None


@strawberry.input
class UpdateUserPreferencesInput:
    """Input for updating user preferences."""

    # Theme preferences
    theme_mode: Optional[str] = None
    theme_preset_id: Optional[UUID] = None
    custom_colors: Optional[JSON] = None

    # Display preferences
    sidebar_collapsed: Optional[bool] = None
    compact_mode: Optional[bool] = None
    show_tooltips: Optional[bool] = None

    # Dashboard preferences
    default_dashboard_id: Optional[UUID] = None
    chart_animation_enabled: Optional[bool] = None
    table_rows_per_page: Optional[str] = None

    # Notification preferences
    email_notifications: Optional[bool] = None
    push_notifications: Optional[bool] = None
    notification_frequency: Optional[str] = None

    # Date/time preferences
    timezone: Optional[str] = None
    date_format: Optional[str] = None
    time_format: Optional[str] = None

    # Locale
    language: Optional[str] = None
    currency: Optional[str] = None
    number_format: Optional[str] = None

    # Accessibility
    reduced_motion: Optional[bool] = None
    high_contrast: Optional[bool] = None
    font_size_adjustment: Optional[str] = None

    # Keyboard shortcuts
    keyboard_shortcuts_enabled: Optional[bool] = None
    custom_shortcuts: Optional[JSON] = None


@strawberry.input
class CreateThemePresetInput:
    """Input for creating a theme preset."""

    name: str
    description: Optional[str] = None
    is_dark: bool = False
    colors: JSON
    typography: Optional[JSON] = None
    spacing: Optional[JSON] = None
    border_radius: Optional[JSON] = None
    preview_image_url: Optional[str] = None
    category: Optional[str] = None
