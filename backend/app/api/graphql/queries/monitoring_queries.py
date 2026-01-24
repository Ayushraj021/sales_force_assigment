"""Monitoring queries."""

from datetime import datetime
from typing import Optional
from uuid import UUID

import strawberry
import structlog
from sqlalchemy import select
from strawberry.types import Info

from app.api.graphql.context import get_db_session, get_current_user_from_context
from app.api.graphql.types.monitoring import (
    MonitorAlertType,
    MonitorConfigType,
    MonitorMetricType,
    MonitorSummaryType,
    BaselineType,
    AlertFilterInput,
)
from app.core.exceptions import NotFoundError

logger = structlog.get_logger()


@strawberry.type
class MonitoringQuery:
    """Monitoring queries."""

    @strawberry.field
    async def monitor_alerts(
        self,
        info: Info,
        filter: Optional[AlertFilterInput] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MonitorAlertType]:
        """Get monitoring alerts."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # In production, this would query from a database table
        # For now, return empty list as service is in-memory
        logger.info(
            "Fetching monitor alerts",
            user_id=str(current_user.id),
            org_id=str(current_user.organization_id),
        )

        return []

    @strawberry.field
    async def monitor_alert(
        self,
        info: Info,
        alert_id: str,
    ) -> MonitorAlertType:
        """Get a specific alert by ID."""
        db = await get_db_session(info)
        await get_current_user_from_context(info, db)

        raise NotFoundError("MonitorAlert", alert_id)

    @strawberry.field
    async def monitor_config(
        self,
        info: Info,
        model_id: UUID,
    ) -> Optional[MonitorConfigType]:
        """Get monitoring configuration for a model."""
        db = await get_db_session(info)
        await get_current_user_from_context(info, db)

        # Would query from database
        return None

    @strawberry.field
    async def monitor_configs(
        self,
        info: Info,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MonitorConfigType]:
        """Get all monitoring configurations."""
        db = await get_db_session(info)
        await get_current_user_from_context(info, db)

        return []

    @strawberry.field
    async def monitor_metrics(
        self,
        info: Info,
        model_name: str,
        since: Optional[datetime] = None,
        limit: int = 1000,
    ) -> list[MonitorMetricType]:
        """Get logged metrics for a model."""
        db = await get_db_session(info)
        await get_current_user_from_context(info, db)

        logger.info("Fetching monitor metrics", model_name=model_name)
        return []

    @strawberry.field
    async def monitor_summary(
        self,
        info: Info,
        model_name: str,
    ) -> MonitorSummaryType:
        """Get monitoring summary for a model."""
        db = await get_db_session(info)
        await get_current_user_from_context(info, db)

        return MonitorSummaryType(
            model_name=model_name,
            total_predictions=0,
            recent_predictions=0,
            avg_latency_ms=0.0,
            alert_count=0,
            critical_alerts=0,
            current_mae=None,
            current_mape=None,
            status="no_data",
        )

    @strawberry.field
    async def monitor_baseline(
        self,
        info: Info,
        model_id: UUID,
    ) -> Optional[BaselineType]:
        """Get baseline for a model."""
        db = await get_db_session(info)
        await get_current_user_from_context(info, db)

        return None

    @strawberry.field
    async def alert_severities(self) -> list[str]:
        """Get available alert severity levels."""
        return ["info", "warning", "critical"]

    @strawberry.field
    async def alert_types(self) -> list[str]:
        """Get available alert types."""
        return ["drift", "performance", "latency", "error_rate", "threshold"]
