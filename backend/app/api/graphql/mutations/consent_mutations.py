"""Consent Record mutations for GDPR/CCPA compliance."""

from datetime import datetime
from uuid import UUID, uuid4

import strawberry
import structlog
from sqlalchemy import select
from strawberry.types import Info

from app.api.graphql.context import get_db_session, get_current_user_from_context
from app.api.graphql.types.consent import (
    BulkConsentInput,
    ConsentRecordType,
    CreateConsentRecordInput,
    UpdateConsentRecordInput,
)
from app.core.exceptions import NotFoundError, ValidationError
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
class ConsentMutation:
    """Consent Record mutations for privacy compliance."""

    @strawberry.mutation
    async def record_consent(
        self,
        info: Info,
        input: CreateConsentRecordInput,
    ) -> ConsentRecordType:
        """Record a new consent (or update existing for same customer/type)."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Validate customer_id
        if not input.customer_id or len(input.customer_id.strip()) == 0:
            raise ValidationError("customer_id is required")

        # Validate consent_type
        valid_types = ["analytics", "marketing", "personalization", "essential", "third_party"]
        if input.consent_type not in valid_types:
            raise ValidationError(f"consent_type must be one of: {', '.join(valid_types)}")

        # Parse expires_at if provided
        expires_at = None
        if input.expires_at:
            expires_at = datetime.fromisoformat(input.expires_at)

        # Check if consent already exists for this customer/type
        result = await db.execute(
            select(ConsentRecord).where(
                ConsentRecord.customer_id == input.customer_id.strip(),
                ConsentRecord.consent_type == input.consent_type,
                ConsentRecord.organization_id == current_user.organization_id,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing consent
            existing.granted = input.granted
            existing.consent_source = input.consent_source
            existing.ip_address = input.ip_address
            existing.user_agent = input.user_agent
            existing.expires_at = expires_at
            existing.consent_metadata = input.consent_metadata

            if input.granted:
                existing.granted_at = datetime.utcnow()
                existing.revoked_at = None
            else:
                existing.revoked_at = datetime.utcnow()

            await db.commit()
            await db.refresh(existing)

            logger.info(
                "Consent updated",
                consent_id=str(existing.id),
                customer_id=input.customer_id,
                consent_type=input.consent_type,
                granted=input.granted,
            )

            return consent_to_graphql(existing)

        # Create new consent record
        consent = ConsentRecord(
            id=uuid4(),
            customer_id=input.customer_id.strip(),
            consent_type=input.consent_type,
            granted=input.granted,
            granted_at=datetime.utcnow() if input.granted else None,
            revoked_at=None if input.granted else datetime.utcnow(),
            expires_at=expires_at,
            consent_source=input.consent_source,
            ip_address=input.ip_address,
            user_agent=input.user_agent,
            consent_metadata=input.consent_metadata,
            organization_id=current_user.organization_id,
        )
        db.add(consent)

        await db.commit()
        await db.refresh(consent)

        logger.info(
            "Consent recorded",
            consent_id=str(consent.id),
            customer_id=input.customer_id,
            consent_type=input.consent_type,
            granted=input.granted,
        )

        return consent_to_graphql(consent)

    @strawberry.mutation
    async def update_consent(
        self,
        info: Info,
        consent_id: UUID,
        input: UpdateConsentRecordInput,
    ) -> ConsentRecordType:
        """Update a consent record."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Get consent
        result = await db.execute(
            select(ConsentRecord).where(
                ConsentRecord.id == consent_id,
                ConsentRecord.organization_id == current_user.organization_id,
            )
        )
        consent = result.scalar_one_or_none()

        if not consent:
            raise NotFoundError("Consent record", str(consent_id))

        # Update fields
        if input.granted is not None:
            consent.granted = input.granted
            if input.granted:
                consent.granted_at = datetime.utcnow()
                consent.revoked_at = None
            else:
                consent.revoked_at = datetime.utcnow()

        if input.revoked_at is not None:
            consent.revoked_at = datetime.fromisoformat(input.revoked_at)

        if input.expires_at is not None:
            consent.expires_at = datetime.fromisoformat(input.expires_at)

        if input.consent_metadata is not None:
            consent.consent_metadata = input.consent_metadata

        await db.commit()
        await db.refresh(consent)

        logger.info(
            "Consent updated",
            consent_id=str(consent.id),
            updated_by=str(current_user.id),
        )

        return consent_to_graphql(consent)

    @strawberry.mutation
    async def revoke_consent(
        self,
        info: Info,
        consent_id: UUID,
    ) -> ConsentRecordType:
        """Revoke a consent record."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Get consent
        result = await db.execute(
            select(ConsentRecord).where(
                ConsentRecord.id == consent_id,
                ConsentRecord.organization_id == current_user.organization_id,
            )
        )
        consent = result.scalar_one_or_none()

        if not consent:
            raise NotFoundError("Consent record", str(consent_id))

        consent.granted = False
        consent.revoked_at = datetime.utcnow()

        await db.commit()
        await db.refresh(consent)

        logger.info(
            "Consent revoked",
            consent_id=str(consent.id),
            customer_id=consent.customer_id,
            consent_type=consent.consent_type,
        )

        return consent_to_graphql(consent)

    @strawberry.mutation
    async def revoke_customer_consents(
        self,
        info: Info,
        customer_id: str,
    ) -> list[ConsentRecordType]:
        """Revoke all consents for a customer (GDPR right to be forgotten support)."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Get all consents for customer
        result = await db.execute(
            select(ConsentRecord).where(
                ConsentRecord.customer_id == customer_id,
                ConsentRecord.organization_id == current_user.organization_id,
                ConsentRecord.granted == True,
            )
        )
        consents = result.scalars().all()

        # Revoke all
        for consent in consents:
            consent.granted = False
            consent.revoked_at = datetime.utcnow()

        await db.commit()

        logger.info(
            "All customer consents revoked",
            customer_id=customer_id,
            consent_count=len(consents),
            revoked_by=str(current_user.id),
        )

        return [consent_to_graphql(c) for c in consents]

    @strawberry.mutation
    async def record_bulk_consent(
        self,
        info: Info,
        input: BulkConsentInput,
    ) -> list[ConsentRecordType]:
        """Record multiple consent types for a customer at once."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Validate customer_id
        if not input.customer_id or len(input.customer_id.strip()) == 0:
            raise ValidationError("customer_id is required")

        # Validate consent types
        valid_types = ["analytics", "marketing", "personalization", "essential", "third_party"]
        for ct in input.consent_types:
            if ct not in valid_types:
                raise ValidationError(f"Invalid consent_type: {ct}. Must be one of: {', '.join(valid_types)}")

        results = []
        for consent_type in input.consent_types:
            # Check if consent exists
            result = await db.execute(
                select(ConsentRecord).where(
                    ConsentRecord.customer_id == input.customer_id.strip(),
                    ConsentRecord.consent_type == consent_type,
                    ConsentRecord.organization_id == current_user.organization_id,
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing
                existing.granted = input.granted
                existing.consent_source = input.consent_source
                existing.ip_address = input.ip_address
                if input.granted:
                    existing.granted_at = datetime.utcnow()
                    existing.revoked_at = None
                else:
                    existing.revoked_at = datetime.utcnow()
                results.append(existing)
            else:
                # Create new
                consent = ConsentRecord(
                    id=uuid4(),
                    customer_id=input.customer_id.strip(),
                    consent_type=consent_type,
                    granted=input.granted,
                    granted_at=datetime.utcnow() if input.granted else None,
                    revoked_at=None if input.granted else datetime.utcnow(),
                    consent_source=input.consent_source,
                    ip_address=input.ip_address,
                    organization_id=current_user.organization_id,
                )
                db.add(consent)
                results.append(consent)

        await db.commit()

        # Refresh all
        for consent in results:
            await db.refresh(consent)

        logger.info(
            "Bulk consent recorded",
            customer_id=input.customer_id,
            consent_types=input.consent_types,
            granted=input.granted,
        )

        return [consent_to_graphql(c) for c in results]

    @strawberry.mutation
    async def delete_consent_record(
        self,
        info: Info,
        consent_id: UUID,
    ) -> bool:
        """Delete a consent record (for data retention compliance)."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Only admins can delete consent records
        if not current_user.is_superuser and not current_user.has_role("admin"):
            from app.core.exceptions import AuthorizationError
            raise AuthorizationError("Only admins can delete consent records")

        # Get consent
        result = await db.execute(
            select(ConsentRecord).where(
                ConsentRecord.id == consent_id,
                ConsentRecord.organization_id == current_user.organization_id,
            )
        )
        consent = result.scalar_one_or_none()

        if not consent:
            raise NotFoundError("Consent record", str(consent_id))

        await db.delete(consent)
        await db.commit()

        logger.info(
            "Consent record deleted",
            consent_id=str(consent_id),
            deleted_by=str(current_user.id),
        )

        return True
