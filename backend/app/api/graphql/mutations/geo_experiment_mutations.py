"""Geo Experiment mutations."""

from datetime import date, datetime
from uuid import UUID, uuid4

import strawberry
import structlog
from sqlalchemy import select
from strawberry.types import Info

from app.api.graphql.context import get_db_session, get_current_user_from_context
from app.api.graphql.types.geo_experiment import (
    CreateGeoExperimentInput,
    GeoExperimentResultType,
    GeoExperimentStatusEnum,
    GeoExperimentType,
    PowerAnalysisResult,
    RunPowerAnalysisInput,
    UpdateGeoExperimentInput,
)
from app.core.exceptions import NotFoundError, ValidationError, AuthorizationError
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
class GeoExperimentMutation:
    """Geo Experiment mutations."""

    @strawberry.mutation
    async def create_geo_experiment(
        self,
        info: Info,
        input: CreateGeoExperimentInput,
    ) -> GeoExperimentType:
        """Create a new geo experiment."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Validate name
        if not input.name or len(input.name.strip()) == 0:
            raise ValidationError("Experiment name is required")

        # Validate regions
        if not input.test_regions or len(input.test_regions) == 0:
            raise ValidationError("At least one test region is required")
        if not input.control_regions or len(input.control_regions) == 0:
            raise ValidationError("At least one control region is required")

        # Parse dates if provided
        start_dt = None
        end_dt = None
        if input.start_date:
            start_dt = date.fromisoformat(input.start_date)
        if input.end_date:
            end_dt = date.fromisoformat(input.end_date)

        # Create experiment
        experiment = GeoExperiment(
            id=uuid4(),
            name=input.name.strip(),
            description=input.description,
            status=GeoExperimentStatus.DRAFT,
            test_regions=input.test_regions,
            control_regions=input.control_regions,
            holdout_regions=input.holdout_regions,
            start_date=start_dt,
            end_date=end_dt,
            warmup_days=input.warmup_days,
            minimum_detectable_effect=input.minimum_detectable_effect,
            target_power=input.target_power,
            primary_metric=input.primary_metric,
            secondary_metrics=input.secondary_metrics,
            organization_id=current_user.organization_id,
            created_by_id=current_user.id,
        )
        db.add(experiment)

        await db.commit()
        await db.refresh(experiment)

        logger.info(
            "Geo experiment created",
            experiment_id=str(experiment.id),
            experiment_name=experiment.name,
            created_by=str(current_user.id),
        )

        return geo_experiment_to_graphql(experiment)

    @strawberry.mutation
    async def update_geo_experiment(
        self,
        info: Info,
        experiment_id: UUID,
        input: UpdateGeoExperimentInput,
    ) -> GeoExperimentType:
        """Update a geo experiment."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Get experiment
        result = await db.execute(
            select(GeoExperiment).where(
                GeoExperiment.id == experiment_id,
                GeoExperiment.organization_id == current_user.organization_id,
            )
        )
        experiment = result.scalar_one_or_none()

        if not experiment:
            raise NotFoundError("Geo experiment", str(experiment_id))

        # Can only update draft or designing experiments
        if experiment.status not in [GeoExperimentStatus.DRAFT, GeoExperimentStatus.DESIGNING]:
            raise ValidationError("Can only update experiments in draft or designing status")

        # Update fields
        if input.name is not None:
            if len(input.name.strip()) == 0:
                raise ValidationError("Experiment name cannot be empty")
            experiment.name = input.name.strip()
        if input.description is not None:
            experiment.description = input.description
        if input.test_regions is not None:
            if len(input.test_regions) == 0:
                raise ValidationError("At least one test region is required")
            experiment.test_regions = input.test_regions
        if input.control_regions is not None:
            if len(input.control_regions) == 0:
                raise ValidationError("At least one control region is required")
            experiment.control_regions = input.control_regions
        if input.holdout_regions is not None:
            experiment.holdout_regions = input.holdout_regions
        if input.start_date is not None:
            experiment.start_date = date.fromisoformat(input.start_date)
        if input.end_date is not None:
            experiment.end_date = date.fromisoformat(input.end_date)
        if input.warmup_days is not None:
            experiment.warmup_days = input.warmup_days
        if input.minimum_detectable_effect is not None:
            experiment.minimum_detectable_effect = input.minimum_detectable_effect
        if input.target_power is not None:
            experiment.target_power = input.target_power
        if input.primary_metric is not None:
            experiment.primary_metric = input.primary_metric
        if input.secondary_metrics is not None:
            experiment.secondary_metrics = input.secondary_metrics

        await db.commit()
        await db.refresh(experiment)

        logger.info(
            "Geo experiment updated",
            experiment_id=str(experiment.id),
            updated_by=str(current_user.id),
        )

        return geo_experiment_to_graphql(experiment)

    @strawberry.mutation
    async def delete_geo_experiment(
        self,
        info: Info,
        experiment_id: UUID,
    ) -> bool:
        """Delete a geo experiment."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Get experiment
        result = await db.execute(
            select(GeoExperiment).where(
                GeoExperiment.id == experiment_id,
                GeoExperiment.organization_id == current_user.organization_id,
            )
        )
        experiment = result.scalar_one_or_none()

        if not experiment:
            raise NotFoundError("Geo experiment", str(experiment_id))

        # Can only delete draft experiments, others should be archived
        if experiment.status not in [GeoExperimentStatus.DRAFT, GeoExperimentStatus.ARCHIVED]:
            raise ValidationError("Only draft or archived experiments can be deleted")

        await db.delete(experiment)
        await db.commit()

        logger.info(
            "Geo experiment deleted",
            experiment_id=str(experiment_id),
            deleted_by=str(current_user.id),
        )

        return True

    @strawberry.mutation
    async def start_geo_experiment(
        self,
        info: Info,
        experiment_id: UUID,
    ) -> GeoExperimentType:
        """Start a geo experiment (move to running status)."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Get experiment
        result = await db.execute(
            select(GeoExperiment).where(
                GeoExperiment.id == experiment_id,
                GeoExperiment.organization_id == current_user.organization_id,
            )
        )
        experiment = result.scalar_one_or_none()

        if not experiment:
            raise NotFoundError("Geo experiment", str(experiment_id))

        # Can only start ready experiments
        if experiment.status != GeoExperimentStatus.READY:
            raise ValidationError("Can only start experiments in ready status")

        # Validate start/end dates
        if not experiment.start_date or not experiment.end_date:
            raise ValidationError("Experiment must have start and end dates defined")

        experiment.status = GeoExperimentStatus.RUNNING

        await db.commit()
        await db.refresh(experiment)

        logger.info(
            "Geo experiment started",
            experiment_id=str(experiment.id),
            started_by=str(current_user.id),
        )

        return geo_experiment_to_graphql(experiment)

    @strawberry.mutation
    async def complete_geo_experiment(
        self,
        info: Info,
        experiment_id: UUID,
    ) -> GeoExperimentType:
        """Mark a geo experiment as completed."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Get experiment
        result = await db.execute(
            select(GeoExperiment).where(
                GeoExperiment.id == experiment_id,
                GeoExperiment.organization_id == current_user.organization_id,
            )
        )
        experiment = result.scalar_one_or_none()

        if not experiment:
            raise NotFoundError("Geo experiment", str(experiment_id))

        # Can only complete running experiments
        if experiment.status != GeoExperimentStatus.RUNNING:
            raise ValidationError("Can only complete experiments in running status")

        experiment.status = GeoExperimentStatus.COMPLETED
        experiment.completed_at = datetime.utcnow()

        await db.commit()
        await db.refresh(experiment)

        logger.info(
            "Geo experiment completed",
            experiment_id=str(experiment.id),
            completed_by=str(current_user.id),
        )

        return geo_experiment_to_graphql(experiment)

    @strawberry.mutation
    async def archive_geo_experiment(
        self,
        info: Info,
        experiment_id: UUID,
    ) -> GeoExperimentType:
        """Archive a geo experiment."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Get experiment
        result = await db.execute(
            select(GeoExperiment).where(
                GeoExperiment.id == experiment_id,
                GeoExperiment.organization_id == current_user.organization_id,
            )
        )
        experiment = result.scalar_one_or_none()

        if not experiment:
            raise NotFoundError("Geo experiment", str(experiment_id))

        experiment.status = GeoExperimentStatus.ARCHIVED

        await db.commit()
        await db.refresh(experiment)

        logger.info(
            "Geo experiment archived",
            experiment_id=str(experiment.id),
            archived_by=str(current_user.id),
        )

        return geo_experiment_to_graphql(experiment)

    @strawberry.mutation
    async def run_power_analysis(
        self,
        info: Info,
        input: RunPowerAnalysisInput,
    ) -> PowerAnalysisResult:
        """Run power analysis for a geo experiment."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Get experiment
        result = await db.execute(
            select(GeoExperiment).where(
                GeoExperiment.id == input.experiment_id,
                GeoExperiment.organization_id == current_user.organization_id,
            )
        )
        experiment = result.scalar_one_or_none()

        if not experiment:
            raise NotFoundError("Geo experiment", str(input.experiment_id))

        # Calculate power analysis (simplified simulation)
        test_count = len(experiment.test_regions) if experiment.test_regions else 0
        control_count = len(experiment.control_regions) if experiment.control_regions else 0
        total_regions = test_count + control_count

        # Simplified power calculation
        effect_size = input.expected_effect_size or experiment.minimum_detectable_effect or 0.1
        estimated_power = min(0.95, 0.8 + (total_regions - 10) * 0.01)
        required_sample_size = max(10, int(100 / (effect_size ** 2)))

        recommendations = []
        if estimated_power < 0.8:
            recommendations.append("Consider increasing the number of regions")
        if effect_size < 0.05:
            recommendations.append("Expected effect size is small - experiment may need longer duration")
        if test_count < 3:
            recommendations.append("Consider adding more test regions for better precision")

        # Store power analysis result
        power_analysis_data = {
            "required_sample_size": required_sample_size,
            "estimated_power": estimated_power,
            "minimum_detectable_effect": effect_size,
            "confidence_level": 1 - input.significance_level,
            "test_regions_count": test_count,
            "control_regions_count": control_count,
        }
        experiment.power_analysis = power_analysis_data

        # Move to designing status if in draft
        if experiment.status == GeoExperimentStatus.DRAFT:
            experiment.status = GeoExperimentStatus.DESIGNING

        await db.commit()

        logger.info(
            "Power analysis completed",
            experiment_id=str(experiment.id),
            estimated_power=estimated_power,
        )

        return PowerAnalysisResult(
            required_sample_size=required_sample_size,
            estimated_power=estimated_power,
            minimum_detectable_effect=effect_size,
            confidence_level=1 - input.significance_level,
            test_regions_count=test_count,
            control_regions_count=control_count,
            recommendations=recommendations,
        )

    @strawberry.mutation
    async def analyze_geo_experiment(
        self,
        info: Info,
        experiment_id: UUID,
    ) -> GeoExperimentResultType:
        """Analyze a completed geo experiment and compute results."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Get experiment
        result = await db.execute(
            select(GeoExperiment).where(
                GeoExperiment.id == experiment_id,
                GeoExperiment.organization_id == current_user.organization_id,
            )
        )
        experiment = result.scalar_one_or_none()

        if not experiment:
            raise NotFoundError("Geo experiment", str(experiment_id))

        # Can only analyze completed experiments
        if experiment.status != GeoExperimentStatus.COMPLETED:
            raise ValidationError("Can only analyze experiments in completed status")

        # Simulated analysis results (in production, this would call actual analysis service)
        test_metric_value = 1250.0
        control_metric_value = 1000.0
        absolute_lift = test_metric_value - control_metric_value
        relative_lift = (absolute_lift / control_metric_value) * 100

        # Simulated statistical significance
        p_value = 0.023
        ci_lower = 150.0
        ci_upper = 350.0
        is_significant = p_value < 0.05

        # Store results
        experiment.absolute_lift = absolute_lift
        experiment.relative_lift = relative_lift
        experiment.p_value = p_value
        experiment.confidence_interval_lower = ci_lower
        experiment.confidence_interval_upper = ci_upper
        experiment.results = {
            "test_metric_value": test_metric_value,
            "control_metric_value": control_metric_value,
            "is_significant": is_significant,
        }
        experiment.status = GeoExperimentStatus.ANALYZED

        await db.commit()
        await db.refresh(experiment)

        logger.info(
            "Geo experiment analyzed",
            experiment_id=str(experiment.id),
            relative_lift=relative_lift,
            is_significant=is_significant,
        )

        return GeoExperimentResultType(
            experiment_id=experiment.id,
            absolute_lift=absolute_lift,
            relative_lift=relative_lift,
            p_value=p_value,
            confidence_interval_lower=ci_lower,
            confidence_interval_upper=ci_upper,
            is_significant=is_significant,
            test_metric_value=test_metric_value,
            control_metric_value=control_metric_value,
            region_level_results={},
            time_series_comparison={},
            diagnostics=None,
        )

    @strawberry.mutation
    async def mark_experiment_ready(
        self,
        info: Info,
        experiment_id: UUID,
    ) -> GeoExperimentType:
        """Mark a geo experiment as ready to run."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Get experiment
        result = await db.execute(
            select(GeoExperiment).where(
                GeoExperiment.id == experiment_id,
                GeoExperiment.organization_id == current_user.organization_id,
            )
        )
        experiment = result.scalar_one_or_none()

        if not experiment:
            raise NotFoundError("Geo experiment", str(experiment_id))

        # Can only mark designing experiments as ready
        if experiment.status not in [GeoExperimentStatus.DRAFT, GeoExperimentStatus.DESIGNING]:
            raise ValidationError("Can only mark draft or designing experiments as ready")

        # Validate experiment is properly configured
        if not experiment.test_regions or len(experiment.test_regions) == 0:
            raise ValidationError("Experiment must have test regions defined")
        if not experiment.control_regions or len(experiment.control_regions) == 0:
            raise ValidationError("Experiment must have control regions defined")
        if not experiment.start_date or not experiment.end_date:
            raise ValidationError("Experiment must have start and end dates defined")

        experiment.status = GeoExperimentStatus.READY

        await db.commit()
        await db.refresh(experiment)

        logger.info(
            "Geo experiment marked ready",
            experiment_id=str(experiment.id),
            marked_by=str(current_user.id),
        )

        return geo_experiment_to_graphql(experiment)
