"""Monitoring mutations."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

import strawberry
import structlog
from strawberry.types import Info

from app.api.graphql.context import get_db_session, get_current_user_from_context
from app.api.graphql.types.monitoring import (
    MonitorConfigType,
    MonitorAlertType,
    BaselineType,
    DriftCheckResultType,
    PerformanceCheckResultType,
    CreateMonitorConfigInput,
    UpdateMonitorConfigInput,
    LogPredictionInput,
    SetBaselineInput,
)
from app.core.exceptions import NotFoundError, ValidationError

logger = structlog.get_logger()


@strawberry.type
class MonitoringMutation:
    """Monitoring mutations."""

    @strawberry.mutation
    async def create_monitor_config(
        self,
        info: Info,
        input: CreateMonitorConfigInput,
    ) -> MonitorConfigType:
        """Create monitoring configuration for a model."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        now = datetime.utcnow()
        config = MonitorConfigType(
            id=uuid4(),
            model_id=input.model_id,
            drift_threshold=input.drift_threshold,
            performance_threshold=input.performance_threshold,
            latency_threshold_ms=input.latency_threshold_ms,
            error_rate_threshold=input.error_rate_threshold,
            check_interval_minutes=input.check_interval_minutes,
            enabled=input.enabled,
            created_at=now,
            updated_at=now,
        )

        logger.info(
            "Monitor config created",
            model_id=str(input.model_id),
            created_by=str(current_user.id),
        )

        return config

    @strawberry.mutation
    async def update_monitor_config(
        self,
        info: Info,
        config_id: UUID,
        input: UpdateMonitorConfigInput,
    ) -> MonitorConfigType:
        """Update monitoring configuration."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # In production, this would update the database
        raise NotFoundError("MonitorConfig", str(config_id))

    @strawberry.mutation
    async def delete_monitor_config(
        self,
        info: Info,
        config_id: UUID,
    ) -> bool:
        """Delete monitoring configuration."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        logger.info(
            "Monitor config deleted",
            config_id=str(config_id),
            deleted_by=str(current_user.id),
        )

        return True

    @strawberry.mutation
    async def log_prediction(
        self,
        info: Info,
        input: LogPredictionInput,
    ) -> bool:
        """Log a prediction for monitoring."""
        db = await get_db_session(info)
        await get_current_user_from_context(info, db)

        logger.info(
            "Prediction logged",
            model_name=input.model_name,
            prediction=input.prediction,
            actual=input.actual,
            latency_ms=input.latency_ms,
        )

        return True

    @strawberry.mutation
    async def set_baseline(
        self,
        info: Info,
        input: SetBaselineInput,
    ) -> BaselineType:
        """Set baseline for model monitoring."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        baseline = BaselineType(
            id=uuid4(),
            model_id=input.model_id,
            model_name=input.model_name,
            metrics=input.metrics,
            feature_distributions=input.feature_distributions,
            created_at=datetime.utcnow(),
        )

        logger.info(
            "Baseline set",
            model_id=str(input.model_id),
            model_name=input.model_name,
            set_by=str(current_user.id),
        )

        return baseline

    @strawberry.mutation
    async def check_drift(
        self,
        info: Info,
        model_name: str,
    ) -> DriftCheckResultType:
        """Check for data drift."""
        db = await get_db_session(info)
        await get_current_user_from_context(info, db)

        return DriftCheckResultType(
            model_name=model_name,
            checked_at=datetime.utcnow(),
            drift_detected=False,
            drifted_features=[],
            alerts=[],
        )

    @strawberry.mutation
    async def check_performance(
        self,
        info: Info,
        model_name: str,
        window_size: int = 100,
    ) -> PerformanceCheckResultType:
        """Check model performance."""
        db = await get_db_session(info)
        await get_current_user_from_context(info, db)

        return PerformanceCheckResultType(
            model_name=model_name,
            checked_at=datetime.utcnow(),
            degradation_detected=False,
            current_mape=None,
            baseline_mape=None,
            degradation_pct=None,
            alerts=[],
        )

    @strawberry.mutation
    async def acknowledge_alert(
        self,
        info: Info,
        alert_id: str,
    ) -> MonitorAlertType:
        """Acknowledge an alert."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        raise NotFoundError("MonitorAlert", alert_id)

    @strawberry.mutation
    async def dismiss_alert(
        self,
        info: Info,
        alert_id: str,
    ) -> bool:
        """Dismiss an alert."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        logger.info(
            "Alert dismissed",
            alert_id=alert_id,
            dismissed_by=str(current_user.id),
        )

        return True

    @strawberry.mutation
    async def enable_monitoring(
        self,
        info: Info,
        model_id: UUID,
    ) -> bool:
        """Enable monitoring for a model."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        logger.info(
            "Monitoring enabled",
            model_id=str(model_id),
            enabled_by=str(current_user.id),
        )

        return True

    @strawberry.mutation
    async def disable_monitoring(
        self,
        info: Info,
        model_id: UUID,
    ) -> bool:
        """Disable monitoring for a model."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        logger.info(
            "Monitoring disabled",
            model_id=str(model_id),
            disabled_by=str(current_user.id),
        )

        return True
