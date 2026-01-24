"""Budget optimization mutations."""

from typing import Optional
from uuid import UUID, uuid4

import strawberry
import structlog
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from strawberry.types import Info

from app.api.graphql.context import get_db_session, get_current_user_from_context
from app.api.graphql.types.optimization import (
    BudgetAllocationtype,
    BudgetScenarioType,
    ConstraintInput,
    CreateBudgetScenarioInput,
    OptimizationConstraintType,
    OptimizationResultType,
    RunOptimizationInput,
    WhatIfAnalysisType,
    WhatIfInput,
    WhatIfResult,
)
from app.core.exceptions import NotFoundError, ValidationError
from app.infrastructure.database.models.model import Model
from app.infrastructure.database.models.optimization import (
    BudgetAllocation,
    BudgetScenario,
    OptimizationConstraint,
    OptimizationResult,
)

logger = structlog.get_logger()

# Valid optimization objectives
VALID_OBJECTIVES = {
    "maximize_revenue",
    "maximize_conversions",
    "maximize_roi",
    "minimize_cpa",
    "target_revenue",
}


def constraint_to_graphql(constraint: OptimizationConstraint) -> OptimizationConstraintType:
    """Convert constraint to GraphQL type."""
    return OptimizationConstraintType(
        id=constraint.id,
        constraint_type=constraint.constraint_type,
        channel_name=constraint.channel_name,
        min_value=constraint.min_value,
        max_value=constraint.max_value,
        fixed_value=constraint.fixed_value,
        min_ratio=constraint.min_ratio,
        max_ratio=constraint.max_ratio,
        max_increase_pct=constraint.max_increase_pct,
        max_decrease_pct=constraint.max_decrease_pct,
    )


def allocation_to_graphql(allocation: BudgetAllocation) -> BudgetAllocationtype:
    """Convert allocation to GraphQL type."""
    return BudgetAllocationtype(
        id=allocation.id,
        channel_name=allocation.channel_name,
        period=allocation.period,
        allocated_budget=allocation.allocated_budget,
        baseline_budget=allocation.baseline_budget,
        change_pct=allocation.change_pct,
        expected_contribution=allocation.expected_contribution,
        expected_roi=allocation.expected_roi,
        marginal_roi=allocation.marginal_roi,
        saturation_level=allocation.saturation_level,
    )


def result_to_graphql(result: OptimizationResult) -> OptimizationResultType:
    """Convert optimization result to GraphQL type."""
    return OptimizationResultType(
        id=result.id,
        status=result.status,
        solver_status=result.solver_status,
        objective_value=result.objective_value,
        baseline_value=result.baseline_value,
        improvement_pct=result.improvement_pct,
        total_spend=result.total_spend,
        expected_revenue=result.expected_revenue,
        expected_roi=result.expected_roi,
        solver_time_seconds=result.solver_time_seconds,
        allocations=[allocation_to_graphql(a) for a in result.allocations],
        created_at=result.created_at,
    )


def scenario_to_graphql(scenario: BudgetScenario) -> BudgetScenarioType:
    """Convert budget scenario to GraphQL type."""
    return BudgetScenarioType(
        id=scenario.id,
        name=scenario.name,
        description=scenario.description,
        is_active=scenario.is_active,
        total_budget=scenario.total_budget,
        budget_period=scenario.budget_period,
        currency=scenario.currency,
        objective=scenario.objective,
        target_value=scenario.target_value,
        start_date=scenario.start_date,
        end_date=scenario.end_date,
        periods=scenario.periods,
        constraints=[constraint_to_graphql(c) for c in scenario.constraints],
        results=[result_to_graphql(r) for r in scenario.results],
        created_at=scenario.created_at,
        updated_at=scenario.updated_at,
    )


@strawberry.input
class UpdateBudgetScenarioInput:
    """Input for updating a budget scenario."""

    name: Optional[str] = None
    description: Optional[str] = None
    total_budget: Optional[float] = None
    budget_period: Optional[str] = None
    objective: Optional[str] = None
    target_value: Optional[float] = None
    is_active: Optional[bool] = None


@strawberry.type
class OptimizationMutation:
    """Budget optimization mutations."""

    @strawberry.mutation
    async def create_budget_scenario(
        self,
        info: Info,
        input: CreateBudgetScenarioInput,
    ) -> BudgetScenarioType:
        """Create a new budget optimization scenario."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Validate name
        if not input.name or len(input.name.strip()) == 0:
            raise ValidationError("Scenario name is required")

        # Validate objective
        if input.objective not in VALID_OBJECTIVES:
            raise ValidationError(
                f"Invalid objective '{input.objective}'. "
                f"Valid objectives: {', '.join(sorted(VALID_OBJECTIVES))}"
            )

        # Validate budget
        if input.total_budget <= 0:
            raise ValidationError("Total budget must be positive")

        # Verify model exists and belongs to organization
        result = await db.execute(
            select(Model).where(
                Model.id == input.model_id,
                Model.organization_id == current_user.organization_id,
            )
        )
        model = result.scalar_one_or_none()

        if not model:
            raise NotFoundError("Model", str(input.model_id))

        # Create scenario
        scenario = BudgetScenario(
            id=uuid4(),
            name=input.name.strip(),
            description=input.description,
            total_budget=input.total_budget,
            budget_period=input.budget_period,
            currency=input.currency,
            objective=input.objective,
            target_value=input.target_value,
            model_id=input.model_id,
            organization_id=current_user.organization_id,
            is_active=True,
        )
        db.add(scenario)

        # Add constraints if provided
        if input.constraints:
            for c in input.constraints:
                constraint = OptimizationConstraint(
                    id=uuid4(),
                    scenario_id=scenario.id,
                    constraint_type=c.constraint_type,
                    channel_name=c.channel_name,
                    min_value=c.min_value,
                    max_value=c.max_value,
                    fixed_value=c.fixed_value,
                    min_ratio=c.min_ratio,
                    max_ratio=c.max_ratio,
                    max_increase_pct=c.max_increase_pct,
                    max_decrease_pct=c.max_decrease_pct,
                )
                db.add(constraint)

        await db.commit()

        # Reload with relationships
        result = await db.execute(
            select(BudgetScenario)
            .options(
                selectinload(BudgetScenario.constraints),
                selectinload(BudgetScenario.results).selectinload(OptimizationResult.allocations),
            )
            .where(BudgetScenario.id == scenario.id)
        )
        scenario = result.scalar_one()

        logger.info(
            "Budget scenario created",
            scenario_id=str(scenario.id),
            created_by=str(current_user.id),
        )

        return scenario_to_graphql(scenario)

    @strawberry.mutation
    async def update_budget_scenario(
        self,
        info: Info,
        scenario_id: UUID,
        input: UpdateBudgetScenarioInput,
    ) -> BudgetScenarioType:
        """Update a budget scenario."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Get scenario
        result = await db.execute(
            select(BudgetScenario)
            .options(
                selectinload(BudgetScenario.constraints),
                selectinload(BudgetScenario.results).selectinload(OptimizationResult.allocations),
            )
            .where(
                BudgetScenario.id == scenario_id,
                BudgetScenario.organization_id == current_user.organization_id,
            )
        )
        scenario = result.scalar_one_or_none()

        if not scenario:
            raise NotFoundError("Budget scenario", str(scenario_id))

        # Update fields
        if input.name is not None:
            if len(input.name.strip()) == 0:
                raise ValidationError("Scenario name cannot be empty")
            scenario.name = input.name.strip()

        if input.description is not None:
            scenario.description = input.description

        if input.total_budget is not None:
            if input.total_budget <= 0:
                raise ValidationError("Total budget must be positive")
            scenario.total_budget = input.total_budget

        if input.budget_period is not None:
            scenario.budget_period = input.budget_period

        if input.objective is not None:
            if input.objective not in VALID_OBJECTIVES:
                raise ValidationError(f"Invalid objective '{input.objective}'")
            scenario.objective = input.objective

        if input.target_value is not None:
            scenario.target_value = input.target_value

        if input.is_active is not None:
            scenario.is_active = input.is_active

        await db.commit()
        await db.refresh(scenario)

        logger.info(
            "Budget scenario updated",
            scenario_id=str(scenario.id),
            updated_by=str(current_user.id),
        )

        return scenario_to_graphql(scenario)

    @strawberry.mutation
    async def delete_budget_scenario(
        self,
        info: Info,
        scenario_id: UUID,
    ) -> bool:
        """Delete a budget scenario (soft delete)."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Get scenario
        result = await db.execute(
            select(BudgetScenario).where(
                BudgetScenario.id == scenario_id,
                BudgetScenario.organization_id == current_user.organization_id,
            )
        )
        scenario = result.scalar_one_or_none()

        if not scenario:
            raise NotFoundError("Budget scenario", str(scenario_id))

        # Soft delete
        scenario.is_active = False

        await db.commit()

        logger.info(
            "Budget scenario deleted",
            scenario_id=str(scenario.id),
            deleted_by=str(current_user.id),
        )

        return True

    @strawberry.mutation
    async def run_optimization(
        self,
        info: Info,
        input: RunOptimizationInput,
    ) -> OptimizationResultType:
        """Run budget optimization for a scenario."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Get scenario
        result = await db.execute(
            select(BudgetScenario)
            .options(selectinload(BudgetScenario.constraints))
            .where(
                BudgetScenario.id == input.scenario_id,
                BudgetScenario.organization_id == current_user.organization_id,
            )
        )
        scenario = result.scalar_one_or_none()

        if not scenario:
            raise NotFoundError("Budget scenario", str(input.scenario_id))

        if not scenario.is_active:
            raise ValidationError("Cannot run optimization on inactive scenario")

        # Update scenario date range if provided
        if input.start_date:
            scenario.start_date = input.start_date
        if input.end_date:
            scenario.end_date = input.end_date
        if input.periods:
            scenario.periods = input.periods

        # Create optimization result (pending)
        opt_result = OptimizationResult(
            id=uuid4(),
            scenario_id=scenario.id,
            status="pending",
        )
        db.add(opt_result)
        await db.commit()

        # TODO: Queue optimization task
        # from app.infrastructure.celery.tasks import run_budget_optimization
        # run_budget_optimization.delay(str(opt_result.id))

        # For now, create mock results
        mock_channels = ["google_ads", "meta_ads", "display", "email", "affiliate"]
        total_budget = scenario.total_budget
        baseline_revenue = total_budget * 2.5  # Mock ROAS of 2.5

        for i, channel in enumerate(mock_channels):
            allocation = BudgetAllocation(
                id=uuid4(),
                optimization_result_id=opt_result.id,
                channel_name=channel,
                period=1,
                allocated_budget=total_budget * (0.3 - i * 0.05),
                baseline_budget=total_budget * 0.2,
                change_pct=50 - i * 25,
                expected_contribution=baseline_revenue * (0.25 - i * 0.03),
                expected_roi=2.5 - i * 0.3,
                marginal_roi=1.8 - i * 0.2,
                saturation_level=0.6 + i * 0.05,
            )
            db.add(allocation)

        opt_result.status = "optimal"
        opt_result.objective_value = baseline_revenue * 1.15
        opt_result.baseline_value = baseline_revenue
        opt_result.improvement_pct = 15.0
        opt_result.total_spend = total_budget
        opt_result.expected_revenue = baseline_revenue * 1.15
        opt_result.expected_roi = 2.875
        opt_result.solver_time_seconds = 1.5

        await db.commit()

        # Reload with allocations
        result = await db.execute(
            select(OptimizationResult)
            .options(selectinload(OptimizationResult.allocations))
            .where(OptimizationResult.id == opt_result.id)
        )
        opt_result = result.scalar_one()

        logger.info(
            "Optimization completed",
            result_id=str(opt_result.id),
            scenario_id=str(scenario.id),
            run_by=str(current_user.id),
        )

        return result_to_graphql(opt_result)

    @strawberry.mutation
    async def what_if_analysis(
        self,
        info: Info,
        input: WhatIfInput,
    ) -> WhatIfAnalysisType:
        """Run what-if analysis with custom channel spends."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Verify model exists
        result = await db.execute(
            select(Model).where(
                Model.id == input.model_id,
                Model.organization_id == current_user.organization_id,
            )
        )
        model = result.scalar_one_or_none()

        if not model:
            raise NotFoundError("Model", str(input.model_id))

        # Parse channel spends
        channel_spends = input.channel_spends
        if not channel_spends or not isinstance(channel_spends, dict):
            raise ValidationError("channel_spends must be a non-empty object")

        # Calculate what-if results (mock implementation)
        channel_results = []
        total_current_spend = 0.0
        total_proposed_spend = 0.0
        total_current_contribution = 0.0
        total_expected_contribution = 0.0

        for channel_name, proposed_spend in channel_spends.items():
            # Mock current values
            current_spend = proposed_spend * 0.8  # Assume 20% increase
            current_contribution = current_spend * 2.5  # Mock ROAS

            # Calculate expected contribution with diminishing returns
            spend_ratio = proposed_spend / current_spend if current_spend > 0 else 1
            # Apply diminishing returns
            efficiency_factor = 1 - (0.1 * (spend_ratio - 1)) if spend_ratio > 1 else 1
            expected_contribution = proposed_spend * 2.5 * efficiency_factor

            change_pct = ((expected_contribution - current_contribution) / current_contribution * 100) if current_contribution > 0 else 0
            marginal_roi = (expected_contribution - current_contribution) / (proposed_spend - current_spend) if proposed_spend != current_spend else 2.5

            channel_results.append(
                WhatIfResult(
                    channel_name=channel_name,
                    current_spend=current_spend,
                    proposed_spend=proposed_spend,
                    current_contribution=current_contribution,
                    expected_contribution=expected_contribution,
                    change_pct=change_pct,
                    marginal_roi=marginal_roi,
                )
            )

            total_current_spend += current_spend
            total_proposed_spend += proposed_spend
            total_current_contribution += current_contribution
            total_expected_contribution += expected_contribution

        overall_change_pct = ((total_expected_contribution - total_current_contribution) / total_current_contribution * 100) if total_current_contribution > 0 else 0

        logger.info(
            "What-if analysis completed",
            model_id=str(model.id),
            channels=len(channel_spends),
            run_by=str(current_user.id),
        )

        return WhatIfAnalysisType(
            total_current_spend=total_current_spend,
            total_proposed_spend=total_proposed_spend,
            total_current_contribution=total_current_contribution,
            total_expected_contribution=total_expected_contribution,
            overall_change_pct=overall_change_pct,
            channel_results=channel_results,
        )
