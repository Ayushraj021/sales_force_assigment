"""Audit Log GraphQL types."""

from datetime import datetime
from typing import Optional
from uuid import UUID

import strawberry
from strawberry.scalars import JSON


@strawberry.type
class AuditLogType:
    """Audit log entry type."""

    id: UUID
    timestamp: datetime
    user_id: Optional[UUID]
    organization_id: Optional[UUID]
    action: str
    resource_type: str
    resource_id: Optional[str]
    description: Optional[str]
    details: JSON
    ip_address: Optional[str]
    user_agent: Optional[str]
    request_id: Optional[str]
    status: str
    error_message: Optional[str]


@strawberry.input
class AuditLogFilterInput:
    """Input for filtering audit logs."""

    action: Optional[str] = None
    resource_type: Optional[str] = None
    user_id: Optional[UUID] = None
    status: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


@strawberry.type
class AuditLogStats:
    """Audit log statistics."""

    total_count: int
    actions_breakdown: JSON
    resource_types_breakdown: JSON
    status_breakdown: JSON
