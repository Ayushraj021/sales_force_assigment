"""Audit Log queries."""

from datetime import datetime
from typing import Optional
from uuid import UUID

import strawberry
import structlog
from sqlalchemy import select, func
from strawberry.types import Info

from app.api.graphql.context import get_db_session, get_current_user_from_context
from app.api.graphql.types.audit import (
    AuditLogFilterInput,
    AuditLogStats,
    AuditLogType,
)
from app.core.exceptions import NotFoundError, AuthorizationError
from app.infrastructure.database.models.audit import AuditLog

logger = structlog.get_logger()


def audit_log_to_graphql(log: AuditLog) -> AuditLogType:
    """Convert audit log to GraphQL type."""
    return AuditLogType(
        id=log.id,
        timestamp=log.timestamp,
        user_id=log.user_id,
        organization_id=log.organization_id,
        action=log.action,
        resource_type=log.resource_type,
        resource_id=log.resource_id,
        description=log.description,
        details=log.details,
        ip_address=str(log.ip_address) if log.ip_address else None,
        user_agent=log.user_agent,
        request_id=log.request_id,
        status=log.status,
        error_message=log.error_message,
    )


@strawberry.type
class AuditQuery:
    """Audit log queries (read-only for compliance)."""

    @strawberry.field
    async def audit_logs(
        self,
        info: Info,
        filter: Optional[AuditLogFilterInput] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AuditLogType]:
        """Get audit logs for the organization (admin only)."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Only admins can view audit logs
        if not current_user.is_superuser and not current_user.has_role("admin"):
            raise AuthorizationError("Only admins can view audit logs")

        query = select(AuditLog).where(
            AuditLog.organization_id == current_user.organization_id
        )

        # Apply filters
        if filter:
            if filter.action:
                query = query.where(AuditLog.action == filter.action)
            if filter.resource_type:
                query = query.where(AuditLog.resource_type == filter.resource_type)
            if filter.user_id:
                query = query.where(AuditLog.user_id == filter.user_id)
            if filter.status:
                query = query.where(AuditLog.status == filter.status)
            if filter.start_date:
                start = datetime.fromisoformat(filter.start_date)
                query = query.where(AuditLog.timestamp >= start)
            if filter.end_date:
                end = datetime.fromisoformat(filter.end_date)
                query = query.where(AuditLog.timestamp <= end)

        # Order by timestamp descending and paginate
        query = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit)

        result = await db.execute(query)
        logs = result.scalars().all()

        return [audit_log_to_graphql(log) for log in logs]

    @strawberry.field
    async def audit_log(
        self,
        info: Info,
        log_id: UUID,
    ) -> AuditLogType:
        """Get a specific audit log entry by ID (admin only)."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Only admins can view audit logs
        if not current_user.is_superuser and not current_user.has_role("admin"):
            raise AuthorizationError("Only admins can view audit logs")

        result = await db.execute(
            select(AuditLog).where(
                AuditLog.id == log_id,
                AuditLog.organization_id == current_user.organization_id,
            )
        )
        log = result.scalar_one_or_none()

        if not log:
            raise NotFoundError("Audit log", str(log_id))

        return audit_log_to_graphql(log)

    @strawberry.field
    async def audit_log_stats(
        self,
        info: Info,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> AuditLogStats:
        """Get audit log statistics (admin only)."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Only admins can view audit stats
        if not current_user.is_superuser and not current_user.has_role("admin"):
            raise AuthorizationError("Only admins can view audit statistics")

        base_query = select(AuditLog).where(
            AuditLog.organization_id == current_user.organization_id
        )

        if start_date:
            start = datetime.fromisoformat(start_date)
            base_query = base_query.where(AuditLog.timestamp >= start)
        if end_date:
            end = datetime.fromisoformat(end_date)
            base_query = base_query.where(AuditLog.timestamp <= end)

        # Get total count
        count_result = await db.execute(
            select(func.count(AuditLog.id)).where(
                AuditLog.organization_id == current_user.organization_id
            )
        )
        total_count = count_result.scalar() or 0

        # Get actions breakdown
        actions_result = await db.execute(
            select(AuditLog.action, func.count(AuditLog.id))
            .where(AuditLog.organization_id == current_user.organization_id)
            .group_by(AuditLog.action)
        )
        actions_breakdown = {row[0]: row[1] for row in actions_result.all()}

        # Get resource types breakdown
        resources_result = await db.execute(
            select(AuditLog.resource_type, func.count(AuditLog.id))
            .where(AuditLog.organization_id == current_user.organization_id)
            .group_by(AuditLog.resource_type)
        )
        resource_types_breakdown = {row[0]: row[1] for row in resources_result.all()}

        # Get status breakdown
        status_result = await db.execute(
            select(AuditLog.status, func.count(AuditLog.id))
            .where(AuditLog.organization_id == current_user.organization_id)
            .group_by(AuditLog.status)
        )
        status_breakdown = {row[0]: row[1] for row in status_result.all()}

        return AuditLogStats(
            total_count=total_count,
            actions_breakdown=actions_breakdown,
            resource_types_breakdown=resource_types_breakdown,
            status_breakdown=status_breakdown,
        )

    @strawberry.field
    async def audit_actions(self) -> list[str]:
        """Get list of available audit actions."""
        return [
            "create",
            "read",
            "update",
            "delete",
            "login",
            "logout",
            "export",
            "train",
            "predict",
            "optimize",
        ]
