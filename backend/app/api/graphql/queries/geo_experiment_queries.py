"""Geo Experiment queries."""

from datetime import date
from typing import Optional
from uuid import UUID

import strawberry
import structlog
from sqlalchemy import select
from strawberry.types import Info

from app.api.graphql.context import get_db_session, get_current_user_from_context
from app.api.graphql.types.geo_experiment import (
    GeoExperimentFilterInput,
    GeoExperimentStatusEnum,
    GeoExperimentType,
)
from app.core.exceptions import NotFoundError
from app.infrastructure.database.models.experiments import GeoExperiment, GeoExperimentStatus

logger = structlog.get_logger()


def geo_experiment_to_graphql(exp: GeoExperiment) -> GeoExperimentType:
    """Convert geo experiment to GraphQL type."""
    status_mapping = {
        GeoExperimentStatus.DRAFT: GeoExperimentStatusEnum.DRAFT,
        GeoExperimentStatus.DESIGNING: GeoExperimentStatusEnum.DESIGNING,
        GeoExperimentStatus.READY: GeoExperimentStatusEnum.READY,
        GeoExperimentStatus.RUNNING: GeoExperimentStatusEnum.RUNNING,
        GeoExperimentStatus.COMPLETED: GeoExperimentStatusEnum.COMPLETED,
        GeoExperimentStatus.ANALYZED: GeoExperimentStatusEnum.ANALYZED,
        GeoExperimentStatus.ARCHIVED: GeoExperimentStatusEnum.ARCHIVED,
    }

    return GeoExperimentType(
        id=exp.id,
        name=exp.name,
        description=exp.description,
        status=status_mapping.get(exp.status, GeoExperimentStatusEnum.DRAFT),
        test_regions=exp.test_regions,
        control_regions=exp.control_regions,
        holdout_regions=exp.holdout_regions,
        start_date=exp.start_date,
        end_date=exp.end_date,
        warmup_days=exp.warmup_days,
        power_analysis=exp.power_analysis,
        minimum_detectable_effect=exp.minimum_detectable_effect,
        target_power=exp.target_power,
        results=exp.results,
        absolute_lift=exp.absolute_lift,
        relative_lift=exp.relative_lift,
        p_value=exp.p_value,
        confidence_interval_lower=exp.confidence_interval_lower,
        confidence_interval_upper=exp.confidence_interval_upper,
        primary_metric=exp.primary_metric,
        secondary_metrics=exp.secondary_metrics,
        organization_id=exp.organization_id,
        created_by_id=exp.created_by_id,
        created_at=exp.created_at,
        updated_at=exp.updated_at,
        completed_at=exp.completed_at,
    )


@strawberry.type
class GeoExperimentQuery:
    """Geo Experiment queries."""

    @strawberry.field
    async def geo_experiments(
        self,
        info: Info,
        filter: Optional[GeoExperimentFilterInput] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[GeoExperimentType]:
        """Get geo experiments for the organization."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        query = select(GeoExperiment).where(
            GeoExperiment.organization_id == current_user.organization_id
        )

        # Apply filters
        if filter:
            if filter.status:
                try:
                    status_enum = GeoExperimentStatus(filter.status)
                    query = query.where(GeoExperiment.status == status_enum)
                except ValueError:
                    pass
            if filter.start_date_from:
                start_from = date.fromisoformat(filter.start_date_from)
                query = query.where(GeoExperiment.start_date >= start_from)
            if filter.start_date_to:
                start_to = date.fromisoformat(filter.start_date_to)
                query = query.where(GeoExperiment.start_date <= start_to)
            if filter.primary_metric:
                query = query.where(GeoExperiment.primary_metric == filter.primary_metric)

        # Order by creation date descending and paginate
        query = query.order_by(GeoExperiment.created_at.desc()).offset(offset).limit(limit)

        result = await db.execute(query)
        experiments = result.scalars().all()

        return [geo_experiment_to_graphql(exp) for exp in experiments]

    @strawberry.field
    async def geo_experiment(
        self,
        info: Info,
        experiment_id: UUID,
    ) -> GeoExperimentType:
        """Get a specific geo experiment by ID."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        result = await db.execute(
            select(GeoExperiment).where(
                GeoExperiment.id == experiment_id,
                GeoExperiment.organization_id == current_user.organization_id,
            )
        )
        experiment = result.scalar_one_or_none()

        if not experiment:
            raise NotFoundError("Geo experiment", str(experiment_id))

        return geo_experiment_to_graphql(experiment)

    @strawberry.field
    async def geo_experiment_statuses(self) -> list[str]:
        """Get list of available geo experiment statuses."""
        return [
            "draft",
            "designing",
            "ready",
            "running",
            "completed",
            "analyzed",
            "archived",
        ]

    @strawberry.field
    async def geo_experiments_summary(
        self,
        info: Info,
    ) -> strawberry.scalars.JSON:
        """Get summary statistics for geo experiments."""
        from sqlalchemy import func

        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Get count by status
        status_counts = await db.execute(
            select(GeoExperiment.status, func.count(GeoExperiment.id))
            .where(GeoExperiment.organization_id == current_user.organization_id)
            .group_by(GeoExperiment.status)
        )

        status_breakdown = {}
        for row in status_counts.all():
            status_breakdown[row[0].value if hasattr(row[0], 'value') else str(row[0])] = row[1]

        # Get total count
        total_result = await db.execute(
            select(func.count(GeoExperiment.id)).where(
                GeoExperiment.organization_id == current_user.organization_id
            )
        )
        total_count = total_result.scalar() or 0

        # Get significant experiments count
        significant_result = await db.execute(
            select(func.count(GeoExperiment.id)).where(
                GeoExperiment.organization_id == current_user.organization_id,
                GeoExperiment.p_value < 0.05,
            )
        )
        significant_count = significant_result.scalar() or 0

        return {
            "total_count": total_count,
            "status_breakdown": status_breakdown,
            "significant_count": significant_count,
        }
