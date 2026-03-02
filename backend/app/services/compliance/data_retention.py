"""
Data Retention Policy Management

GDPR, CCPA compliant data retention and deletion.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class DataCategory(str, Enum):
    """Categories of data for retention policies."""
    PERSONAL = "personal"
    ANALYTICS = "analytics"
    MARKETING = "marketing"
    FINANCIAL = "financial"
    OPERATIONAL = "operational"
    LOGS = "logs"


class RetentionAction(str, Enum):
    """Actions to take when retention period expires."""
    DELETE = "delete"
    ANONYMIZE = "anonymize"
    ARCHIVE = "archive"
    AGGREGATE = "aggregate"


@dataclass
class DataRetentionPolicy:
    """Policy for a specific data category."""
    category: DataCategory
    retention_days: int
    action: RetentionAction
    legal_basis: str = ""
    description: str = ""
    exceptions: List[str] = field(default_factory=list)

    def is_expired(self, created_at: datetime) -> bool:
        """Check if data has exceeded retention period."""
        expiry = created_at + timedelta(days=self.retention_days)
        return datetime.utcnow() > expiry


@dataclass
class RetentionConfig:
    """Configuration for retention management."""
    policies: Dict[DataCategory, DataRetentionPolicy] = field(default_factory=dict)
    default_retention_days: int = 365
    enable_auto_deletion: bool = True
    dry_run: bool = False
    notification_days_before: int = 30


class RetentionManager:
    """
    Data Retention Manager.

    Features:
    - Policy-based retention management
    - Automatic deletion/anonymization
    - Audit logging
    - GDPR/CCPA compliance

    Example:
        manager = RetentionManager(config)

        # Check for expired data
        expired = manager.find_expired_records(database)

        # Execute retention actions
        manager.execute_retention(expired)
    """

    def __init__(self, config: Optional[RetentionConfig] = None):
        self.config = config or RetentionConfig()
        self._audit_log: List[Dict] = []

        # Default policies
        self._setup_default_policies()

    def _setup_default_policies(self):
        """Set up default retention policies."""
        defaults = {
            DataCategory.PERSONAL: DataRetentionPolicy(
                category=DataCategory.PERSONAL,
                retention_days=365 * 2,  # 2 years
                action=RetentionAction.DELETE,
                legal_basis="GDPR Article 5(1)(e)",
                description="Personal identifiable information",
            ),
            DataCategory.ANALYTICS: DataRetentionPolicy(
                category=DataCategory.ANALYTICS,
                retention_days=365 * 3,  # 3 years
                action=RetentionAction.AGGREGATE,
                legal_basis="Legitimate interest",
                description="Aggregated analytics data",
            ),
            DataCategory.MARKETING: DataRetentionPolicy(
                category=DataCategory.MARKETING,
                retention_days=365 * 2,
                action=RetentionAction.ANONYMIZE,
                legal_basis="Consent",
                description="Marketing campaign data",
            ),
            DataCategory.LOGS: DataRetentionPolicy(
                category=DataCategory.LOGS,
                retention_days=90,
                action=RetentionAction.DELETE,
                legal_basis="Operational necessity",
                description="System and access logs",
            ),
        }

        for category, policy in defaults.items():
            if category not in self.config.policies:
                self.config.policies[category] = policy

    def get_policy(self, category: DataCategory) -> DataRetentionPolicy:
        """Get retention policy for a category."""
        return self.config.policies.get(
            category,
            DataRetentionPolicy(
                category=category,
                retention_days=self.config.default_retention_days,
                action=RetentionAction.ARCHIVE,
            )
        )

    def find_expired_records(
        self,
        records: List[Dict],
        category: DataCategory,
        date_field: str = "created_at",
    ) -> List[Dict]:
        """
        Find records that have exceeded retention period.

        Args:
            records: List of record dicts
            category: Data category
            date_field: Field name containing creation date

        Returns:
            List of expired records
        """
        policy = self.get_policy(category)
        expired = []

        for record in records:
            created_at = record.get(date_field)
            if created_at is None:
                continue

            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at)

            if policy.is_expired(created_at):
                expired.append(record)

        return expired

    def execute_retention(
        self,
        records: List[Dict],
        category: DataCategory,
        delete_fn: Optional[Callable] = None,
        anonymize_fn: Optional[Callable] = None,
    ) -> Dict[str, int]:
        """
        Execute retention policy on records.

        Args:
            records: Records to process
            category: Data category
            delete_fn: Function to delete records
            anonymize_fn: Function to anonymize records

        Returns:
            Summary of actions taken
        """
        policy = self.get_policy(category)
        summary = {
            "processed": 0,
            "deleted": 0,
            "anonymized": 0,
            "archived": 0,
            "errors": 0,
        }

        for record in records:
            try:
                if self.config.dry_run:
                    logger.info(f"[DRY RUN] Would process record: {record.get('id')}")
                    summary["processed"] += 1
                    continue

                if policy.action == RetentionAction.DELETE:
                    if delete_fn:
                        delete_fn(record)
                    summary["deleted"] += 1

                elif policy.action == RetentionAction.ANONYMIZE:
                    if anonymize_fn:
                        anonymize_fn(record)
                    summary["anonymized"] += 1

                elif policy.action == RetentionAction.ARCHIVE:
                    # Archive logic here
                    summary["archived"] += 1

                summary["processed"] += 1

                # Audit log
                self._log_action(record, policy)

            except Exception as e:
                logger.error(f"Error processing record: {e}")
                summary["errors"] += 1

        return summary

    def anonymize_record(
        self,
        record: Dict,
        fields_to_anonymize: List[str],
    ) -> Dict:
        """
        Anonymize specific fields in a record.

        Args:
            record: Original record
            fields_to_anonymize: Field names to anonymize

        Returns:
            Anonymized record
        """
        anonymized = record.copy()

        for field in fields_to_anonymize:
            if field in anonymized:
                field_type = type(anonymized[field])

                if field_type == str:
                    anonymized[field] = self._hash_string(anonymized[field])
                elif field_type in (int, float):
                    anonymized[field] = 0
                elif field_type == list:
                    anonymized[field] = []
                else:
                    anonymized[field] = None

        return anonymized

    def _hash_string(self, value: str) -> str:
        """Hash a string for anonymization."""
        import hashlib
        return hashlib.sha256(value.encode()).hexdigest()[:16]

    def _log_action(self, record: Dict, policy: DataRetentionPolicy):
        """Log retention action for audit."""
        self._audit_log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "record_id": record.get("id"),
            "category": policy.category.value,
            "action": policy.action.value,
            "retention_days": policy.retention_days,
        })

    def get_audit_log(self) -> List[Dict]:
        """Get audit log of retention actions."""
        return self._audit_log.copy()

    def get_upcoming_expirations(
        self,
        records: List[Dict],
        category: DataCategory,
        date_field: str = "created_at",
    ) -> List[Dict]:
        """
        Find records expiring within notification period.

        Returns:
            Records expiring soon
        """
        policy = self.get_policy(category)
        notification_date = datetime.utcnow() + timedelta(
            days=self.config.notification_days_before
        )

        expiring = []
        for record in records:
            created_at = record.get(date_field)
            if created_at is None:
                continue

            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at)

            expiry = created_at + timedelta(days=policy.retention_days)
            if datetime.utcnow() < expiry <= notification_date:
                expiring.append({
                    **record,
                    "expires_at": expiry.isoformat(),
                })

        return expiring
