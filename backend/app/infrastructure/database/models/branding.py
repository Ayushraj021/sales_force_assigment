"""
White-labeling and branding database models.

Models for custom branding and theme configuration.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.infrastructure.database.session import Base


class OrganizationBranding(Base):
    """
    Organization-level branding configuration.

    Stores custom branding for white-label deployments.
    """

    __tablename__ = "organization_brandings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Organization reference
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id"),
        unique=True,
        nullable=False,
    )

    # Basic branding
    company_name = Column(String(255))
    tagline = Column(String(500))

    # Logos
    logo_url = Column(Text)  # Main logo URL
    logo_dark_url = Column(Text)  # Logo for dark mode
    favicon_url = Column(Text)  # Favicon URL
    logo_width = Column(String(20))  # e.g., "120px"

    # Colors (CSS color values)
    primary_color = Column(String(50), default="#6366f1")  # Indigo
    secondary_color = Column(String(50), default="#8b5cf6")  # Violet
    accent_color = Column(String(50))
    success_color = Column(String(50), default="#10b981")
    warning_color = Column(String(50), default="#f59e0b")
    error_color = Column(String(50), default="#ef4444")

    # Background colors
    background_color = Column(String(50))
    background_dark_color = Column(String(50))
    sidebar_color = Column(String(50))
    sidebar_dark_color = Column(String(50))

    # Typography
    font_family = Column(String(255), default="Inter")
    heading_font_family = Column(String(255))
    font_size_base = Column(String(20), default="16px")

    # Border radius
    border_radius = Column(String(20), default="0.5rem")

    # Custom CSS (advanced)
    custom_css = Column(Text)

    # Email branding
    email_logo_url = Column(Text)
    email_footer_text = Column(Text)
    email_primary_color = Column(String(50))

    # Report branding
    report_logo_url = Column(Text)
    report_header_color = Column(String(50))
    report_footer_text = Column(Text)

    # Landing page
    landing_page_enabled = Column(Boolean, default=False)
    landing_page_config = Column(JSONB)

    # Feature flags
    show_powered_by = Column(Boolean, default=True)  # "Powered by Analytics"
    custom_domain_enabled = Column(Boolean, default=False)

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ThemePreset(Base):
    """
    Predefined theme presets.

    System-level theme configurations that can be applied.
    """

    __tablename__ = "theme_presets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)

    # Theme type
    is_dark = Column(Boolean, default=False)
    is_system = Column(Boolean, default=True)  # System preset vs user-created

    # Colors
    colors = Column(JSONB, nullable=False)  # Full color palette

    # Typography
    typography = Column(JSONB)

    # Spacing and sizing
    spacing = Column(JSONB)
    border_radius = Column(JSONB)

    # Preview
    preview_image_url = Column(Text)

    # Metadata
    category = Column(String(50))  # e.g., "professional", "modern", "minimal"
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)


class UserPreferences(Base):
    """
    User-level preferences and settings.

    Stores individual user preferences including theme.
    """

    __tablename__ = "user_preferences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # User reference
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        unique=True,
        nullable=False,
    )

    # Theme preferences
    theme_mode = Column(String(20), default="system")  # "light", "dark", "system"
    theme_preset_id = Column(UUID(as_uuid=True), ForeignKey("theme_presets.id"))
    custom_colors = Column(JSONB)  # Override colors

    # Display preferences
    sidebar_collapsed = Column(Boolean, default=False)
    compact_mode = Column(Boolean, default=False)
    show_tooltips = Column(Boolean, default=True)

    # Dashboard preferences
    default_dashboard_id = Column(UUID(as_uuid=True), ForeignKey("dashboard_layouts.id"))
    chart_animation_enabled = Column(Boolean, default=True)
    table_rows_per_page = Column(String(10), default="25")

    # Notification preferences
    email_notifications = Column(Boolean, default=True)
    push_notifications = Column(Boolean, default=False)
    notification_frequency = Column(String(20), default="daily")

    # Date/time preferences
    timezone = Column(String(100), default="UTC")
    date_format = Column(String(50), default="YYYY-MM-DD")
    time_format = Column(String(20), default="24h")

    # Locale
    language = Column(String(10), default="en")
    currency = Column(String(10), default="USD")
    number_format = Column(String(20), default="en-US")

    # Accessibility
    reduced_motion = Column(Boolean, default=False)
    high_contrast = Column(Boolean, default=False)
    font_size_adjustment = Column(String(10), default="0")  # e.g., "+2", "-1"

    # Keyboard shortcuts
    keyboard_shortcuts_enabled = Column(Boolean, default=True)
    custom_shortcuts = Column(JSONB)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
