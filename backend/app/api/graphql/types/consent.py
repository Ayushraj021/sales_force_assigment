"""Consent Record GraphQL types for GDPR/CCPA compliance."""

from datetime import datetime
from typing import Optional
from uuid import UUID

import strawberry
from strawberry.scalars import JSON


@strawberry.type
class ConsentRecordType:
    """Consent record type for privacy compliance."""

    id: UUID
    customer_id: str

    # Consent details
    consent_type: str  # analytics, marketing, personalization
    granted: bool

    # Timing
    granted_at: Optional[datetime]
    revoked_at: Optional[datetime]
    expires_at: Optional[datetime]

    # Source
    consent_source: Optional[str]  # website, app, email
    ip_address: Optional[str]
    user_agent: Optional[str]

    # Additional data
    consent_metadata: Optional[JSON]

    # Relationships
    organization_id: Optional[UUID]

    # Timestamps
    created_at: datetime
    updated_at: datetime


@strawberry.input
class CreateConsentRecordInput:
    """Input for creating a consent record."""

    customer_id: str
    consent_type: str  # analytics, marketing, personalization
    granted: bool
    consent_source: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    expires_at: Optional[str] = None  # ISO datetime string
    consent_metadata: Optional[JSON] = None


@strawberry.input
class UpdateConsentRecordInput:
    """Input for updating a consent record (primarily for revocation)."""

    granted: Optional[bool] = None
    revoked_at: Optional[str] = None  # ISO datetime string
    expires_at: Optional[str] = None  # ISO datetime string
    consent_metadata: Optional[JSON] = None


@strawberry.input
class ConsentRecordFilterInput:
    """Input for filtering consent records."""

    customer_id: Optional[str] = None
    consent_type: Optional[str] = None
    granted: Optional[bool] = None
    consent_source: Optional[str] = None


@strawberry.type
class ConsentSummaryType:
    """Summary of consent records."""

    total_records: int
    granted_count: int
    revoked_count: int
    expired_count: int
    by_type: JSON
    by_source: JSON


@strawberry.input
class BulkConsentInput:
    """Input for bulk consent operations."""

    customer_id: str
    consent_types: list[str]
    granted: bool
    consent_source: Optional[str] = None
    ip_address: Optional[str] = None
