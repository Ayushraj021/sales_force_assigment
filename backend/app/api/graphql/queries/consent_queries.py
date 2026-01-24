"""Consent Record queries for GDPR/CCPA compliance."""

from datetime import datetime
from typing import Optional
from uuid import UUID

import strawberry
import structlog
from sqlalchemy import select, func
from strawberry.types import Info

from app.api.graphql.context import get_db_session, get_current_user_from_context
from app.api.graphql.types.consent import (
    ConsentRecordFilterInput,
    ConsentRecordType,
    ConsentSummaryType,
)
from app.core.exceptions import NotFoundError
from app.infrastructure.database.models.experiments import ConsentRecord

logger = structlog.get_logger()


def consent_to_graphql(consent: ConsentRecord) -> ConsentRecordType:
    """Convert consent record to GraphQL type."""
    return ConsentRecordType(
        id=consent.id,
        customer_id=consent.customer_id,
        consent_type=consent.consent_type,
        granted=consent.granted,
        granted_at=consent.granted_at,
        revoked_at=consent.revoked_at,
        expires_at=consent.expires_at,
        consent_source=consent.consent_source,
        ip_address=consent.ip_address,
        user_agent=consent.user_agent,
        consent_metadata=consent.consent_metadata,
        organization_id=consent.organization_id,
        created_at=consent.created_at,
        updated_at=consent.updated_at,
    )


@strawberry.type
class ConsentQuery:
    """Consent Record queries for privacy compliance."""

    @strawberry.field
    async def consent_records(
        self,
        info: Info,
        filter: Optional[ConsentRecordFilterInput] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ConsentRecordType]:
        """Get consent records for the organization."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        query = select(ConsentRecord).where(
            ConsentRecord.organization_id == current_user.organization_id
        )

        # Apply filters
        if filter:
            if filter.customer_id:
                query = query.where(ConsentRecord.customer_id == filter.customer_id)
            if filter.consent_type:
                query = query.where(ConsentRecord.consent_type == filter.consent_type)
            if filter.granted is not None:
                query = query.where(ConsentRecord.granted == filter.granted)
            if filter.consent_source:
                query = query.where(ConsentRecord.consent_source == filter.consent_source)

        # Order by creation date descending and paginate
        query = query.order_by(ConsentRecord.created_at.desc()).offset(offset).limit(limit)

        result = await db.execute(query)
        consents = result.scalars().all()

        return [consent_to_graphql(c) for c in consents]

    @strawberry.field
    async def consent_record(
        self,
        info: Info,
        consent_id: UUID,
    ) -> ConsentRecordType:
        """Get a specific consent record by ID."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        result = await db.execute(
            select(ConsentRecord).where(
                ConsentRecord.id == consent_id,
                ConsentRecord.organization_id == current_user.organization_id,
            )
        )
        consent = result.scalar_one_or_none()

        if not consent:
            raise NotFoundError("Consent record", str(consent_id))

        return consent_to_graphql(consent)

    @strawberry.field
    async def customer_consents(
        self,
        info: Info,
        customer_id: str,
    ) -> list[ConsentRecordType]:
        """Get all consent records for a specific customer."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        result = await db.execute(
            select(ConsentRecord).where(
                ConsentRecord.customer_id == customer_id,
                ConsentRecord.organization_id == current_user.organization_id,
            ).order_by(ConsentRecord.consent_type)
        )
        consents = result.scalars().all()

        return [consent_to_graphql(c) for c in consents]

    @strawberry.field
    async def customer_consent_status(
        self,
        info: Info,
        customer_id: str,
    ) -> strawberry.scalars.JSON:
        """Get consent status summary for a customer."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        result = await db.execute(
            select(ConsentRecord).where(
                ConsentRecord.customer_id == customer_id,
                ConsentRecord.organization_id == current_user.organization_id,
            )
        )
        consents = result.scalars().all()

        now = datetime.utcnow()
        status = {}
        for consent in consents:
            is_expired = consent.expires_at and consent.expires_at < now
            status[consent.consent_type] = {
                "granted": consent.granted and not is_expired,
                "granted_at": consent.granted_at.isoformat() if consent.granted_at else None,
                "revoked_at": consent.revoked_at.isoformat() if consent.revoked_at else None,
                "expires_at": consent.expires_at.isoformat() if consent.expires_at else None,
                "is_expired": is_expired,
            }

        return {
            "customer_id": customer_id,
            "consents": status,
            "has_analytics": status.get("analytics", {}).get("granted", False),
            "has_marketing": status.get("marketing", {}).get("granted", False),
            "has_personalization": status.get("personalization", {}).get("granted", False),
        }

    @strawberry.field
    async def consent_summary(
        self,
        info: Info,
    ) -> ConsentSummaryType:
        """Get summary of all consent records for the organization."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)
        now = datetime.utcnow()

        # Total count
        total_result = await db.execute(
            select(func.count(ConsentRecord.id)).where(
                ConsentRecord.organization_id == current_user.organization_id
            )
        )
        total_records = total_result.scalar() or 0

        # Granted count
        granted_result = await db.execute(
            select(func.count(ConsentRecord.id)).where(
                ConsentRecord.organization_id == current_user.organization_id,
                ConsentRecord.granted == True,
            )
        )
        granted_count = granted_result.scalar() or 0

        # Revoked count
        revoked_result = await db.execute(
            select(func.count(ConsentRecord.id)).where(
                ConsentRecord.organization_id == current_user.organization_id,
                ConsentRecord.granted == False,
            )
        )
        revoked_count = revoked_result.scalar() or 0

        # Expired count (granted but past expiry)
        expired_result = await db.execute(
            select(func.count(ConsentRecord.id)).where(
                ConsentRecord.organization_id == current_user.organization_id,
                ConsentRecord.granted == True,
                ConsentRecord.expires_at < now,
            )
        )
        expired_count = expired_result.scalar() or 0

        # By type breakdown
        by_type_result = await db.execute(
            select(ConsentRecord.consent_type, func.count(ConsentRecord.id))
            .where(ConsentRecord.organization_id == current_user.organization_id)
            .group_by(ConsentRecord.consent_type)
        )
        by_type = {row[0]: row[1] for row in by_type_result.all()}

        # By source breakdown
        by_source_result = await db.execute(
            select(ConsentRecord.consent_source, func.count(ConsentRecord.id))
            .where(ConsentRecord.organization_id == current_user.organization_id)
            .group_by(ConsentRecord.consent_source)
        )
        by_source = {row[0] or "unknown": row[1] for row in by_source_result.all()}

        return ConsentSummaryType(
            total_records=total_records,
            granted_count=granted_count,
            revoked_count=revoked_count,
            expired_count=expired_count,
            by_type=by_type,
            by_source=by_source,
        )

    @strawberry.field
    async def consent_types(self) -> list[str]:
        """Get list of available consent types."""
        return [
            "analytics",
            "marketing",
            "personalization",
            "essential",
            "third_party",
        ]

    @strawberry.field
    async def consent_sources(self) -> list[str]:
        """Get list of common consent sources."""
        return [
            "website",
            "app",
            "email",
            "api",
            "manual",
        ]

    @strawberry.field
    async def expiring_consents(
        self,
        info: Info,
        days_until_expiry: int = 30,
        limit: int = 50,
    ) -> list[ConsentRecordType]:
        """Get consents expiring within the specified number of days."""
        from datetime import timedelta

        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        now = datetime.utcnow()
        expiry_threshold = now + timedelta(days=days_until_expiry)

        result = await db.execute(
            select(ConsentRecord).where(
                ConsentRecord.organization_id == current_user.organization_id,
                ConsentRecord.granted == True,
                ConsentRecord.expires_at != None,
                ConsentRecord.expires_at > now,
                ConsentRecord.expires_at <= expiry_threshold,
            ).order_by(ConsentRecord.expires_at).limit(limit)
        )
        consents = result.scalars().all()

        return [consent_to_graphql(c) for c in consents]
