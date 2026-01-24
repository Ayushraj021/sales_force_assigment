"""
Consent Management

GDPR/CCPA compliant consent tracking and management.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum
import logging
import hashlib

logger = logging.getLogger(__name__)


class ConsentType(str, Enum):
    """Types of consent."""
    ESSENTIAL = "essential"  # Always required
    ANALYTICS = "analytics"
    MARKETING = "marketing"
    PERSONALIZATION = "personalization"
    THIRD_PARTY = "third_party"
    DATA_SHARING = "data_sharing"


class ConsentStatus(str, Enum):
    """Consent status."""
    GRANTED = "granted"
    DENIED = "denied"
    WITHDRAWN = "withdrawn"
    PENDING = "pending"
    EXPIRED = "expired"


@dataclass
class ConsentRecord:
    """Individual consent record."""
    consent_id: str
    user_id: str
    consent_type: ConsentType
    status: ConsentStatus
    granted_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    withdrawn_at: Optional[datetime] = None
    source: str = "web"  # web, app, api, import
    ip_address: Optional[str] = None
    version: str = "1.0"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_valid(self) -> bool:
        """Check if consent is currently valid."""
        if self.status != ConsentStatus.GRANTED:
            return False

        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False

        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "consent_id": self.consent_id,
            "user_id": self.user_id,
            "consent_type": self.consent_type.value,
            "status": self.status.value,
            "granted_at": self.granted_at.isoformat() if self.granted_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "withdrawn_at": self.withdrawn_at.isoformat() if self.withdrawn_at else None,
            "source": self.source,
            "version": self.version,
        }


class ConsentManager:
    """
    Consent Management System.

    Features:
    - Track consent by type and user
    - Consent versioning
    - Expiration handling
    - Audit trail

    Example:
        manager = ConsentManager()

        # Record consent
        manager.record_consent(
            user_id="user_123",
            consent_type=ConsentType.MARKETING,
            granted=True,
        )

        # Check consent
        if manager.has_consent("user_123", ConsentType.MARKETING):
            send_marketing_email()
    """

    def __init__(self, default_expiry_days: int = 365):
        self.default_expiry_days = default_expiry_days
        self._consents: Dict[str, List[ConsentRecord]] = {}
        self._audit_log: List[Dict] = []

    def record_consent(
        self,
        user_id: str,
        consent_type: ConsentType,
        granted: bool,
        source: str = "web",
        ip_address: Optional[str] = None,
        expires_in_days: Optional[int] = None,
        version: str = "1.0",
        metadata: Optional[Dict] = None,
    ) -> ConsentRecord:
        """
        Record a consent decision.

        Args:
            user_id: User identifier
            consent_type: Type of consent
            granted: Whether consent was granted
            source: Source of consent (web, app, etc.)
            ip_address: IP address (optional, for audit)
            expires_in_days: Expiry in days (optional)
            version: Consent policy version
            metadata: Additional metadata

        Returns:
            ConsentRecord
        """
        now = datetime.utcnow()

        # Generate consent ID
        consent_id = self._generate_consent_id(user_id, consent_type, now)

        # Calculate expiry
        expires_at = None
        if granted:
            days = expires_in_days or self.default_expiry_days
            expires_at = now + datetime.timedelta(days=days) if days > 0 else None

        record = ConsentRecord(
            consent_id=consent_id,
            user_id=user_id,
            consent_type=consent_type,
            status=ConsentStatus.GRANTED if granted else ConsentStatus.DENIED,
            granted_at=now if granted else None,
            expires_at=expires_at,
            source=source,
            ip_address=self._hash_ip(ip_address) if ip_address else None,
            version=version,
            metadata=metadata or {},
        )

        # Store consent
        if user_id not in self._consents:
            self._consents[user_id] = []
        self._consents[user_id].append(record)

        # Audit log
        self._log_consent_event("record", record)

        return record

    def withdraw_consent(
        self,
        user_id: str,
        consent_type: ConsentType,
        reason: Optional[str] = None,
    ) -> bool:
        """
        Withdraw previously granted consent.

        Args:
            user_id: User identifier
            consent_type: Type of consent to withdraw
            reason: Optional reason for withdrawal

        Returns:
            True if consent was withdrawn
        """
        if user_id not in self._consents:
            return False

        withdrawn = False
        for record in self._consents[user_id]:
            if (record.consent_type == consent_type and
                record.status == ConsentStatus.GRANTED):
                record.status = ConsentStatus.WITHDRAWN
                record.withdrawn_at = datetime.utcnow()
                record.metadata["withdrawal_reason"] = reason
                withdrawn = True

                self._log_consent_event("withdraw", record)

        return withdrawn

    def has_consent(
        self,
        user_id: str,
        consent_type: ConsentType,
    ) -> bool:
        """
        Check if user has valid consent for a type.

        Args:
            user_id: User identifier
            consent_type: Type of consent to check

        Returns:
            True if valid consent exists
        """
        # Essential consent is always required
        if consent_type == ConsentType.ESSENTIAL:
            return True

        if user_id not in self._consents:
            return False

        for record in self._consents[user_id]:
            if record.consent_type == consent_type and record.is_valid():
                return True

        return False

    def get_user_consents(
        self,
        user_id: str,
        include_expired: bool = False,
    ) -> List[ConsentRecord]:
        """Get all consent records for a user."""
        if user_id not in self._consents:
            return []

        consents = self._consents[user_id]

        if not include_expired:
            consents = [c for c in consents if c.is_valid() or c.status == ConsentStatus.DENIED]

        return consents

    def get_consent_summary(self, user_id: str) -> Dict[str, str]:
        """Get summary of consent status by type."""
        summary = {}

        for consent_type in ConsentType:
            if self.has_consent(user_id, consent_type):
                summary[consent_type.value] = "granted"
            else:
                # Check if explicitly denied
                denied = False
                for record in self._consents.get(user_id, []):
                    if (record.consent_type == consent_type and
                        record.status in [ConsentStatus.DENIED, ConsentStatus.WITHDRAWN]):
                        denied = True
                        break

                summary[consent_type.value] = "denied" if denied else "pending"

        return summary

    def refresh_expired_consents(self) -> List[str]:
        """
        Find and mark expired consents.

        Returns:
            List of user IDs with expired consents
        """
        expired_users = []

        for user_id, consents in self._consents.items():
            for record in consents:
                if (record.status == ConsentStatus.GRANTED and
                    record.expires_at and
                    datetime.utcnow() > record.expires_at):
                    record.status = ConsentStatus.EXPIRED
                    expired_users.append(user_id)
                    self._log_consent_event("expire", record)

        return list(set(expired_users))

    def export_user_consents(self, user_id: str) -> Dict[str, Any]:
        """
        Export all consent data for a user (GDPR data portability).

        Returns:
            Complete consent history
        """
        consents = self._consents.get(user_id, [])

        return {
            "user_id": user_id,
            "export_date": datetime.utcnow().isoformat(),
            "consents": [c.to_dict() for c in consents],
            "current_status": self.get_consent_summary(user_id),
        }

    def delete_user_data(self, user_id: str) -> bool:
        """
        Delete all consent records for a user (GDPR right to erasure).

        Returns:
            True if data was deleted
        """
        if user_id not in self._consents:
            return False

        # Log before deletion
        for record in self._consents[user_id]:
            self._log_consent_event("delete", record)

        del self._consents[user_id]
        return True

    def _generate_consent_id(
        self,
        user_id: str,
        consent_type: ConsentType,
        timestamp: datetime,
    ) -> str:
        """Generate unique consent ID."""
        data = f"{user_id}:{consent_type.value}:{timestamp.isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:24]

    def _hash_ip(self, ip: str) -> str:
        """Hash IP address for privacy."""
        return hashlib.sha256(ip.encode()).hexdigest()[:12]

    def _log_consent_event(self, event_type: str, record: ConsentRecord):
        """Log consent event for audit."""
        self._audit_log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "consent_id": record.consent_id,
            "user_id": record.user_id,
            "consent_type": record.consent_type.value,
            "status": record.status.value,
        })

    def get_audit_log(
        self,
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
    ) -> List[Dict]:
        """Get audit log, optionally filtered."""
        log = self._audit_log

        if user_id:
            log = [e for e in log if e.get("user_id") == user_id]

        if start_date:
            log = [
                e for e in log
                if datetime.fromisoformat(e["timestamp"]) >= start_date
            ]

        return log
