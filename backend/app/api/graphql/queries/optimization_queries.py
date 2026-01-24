"""Budget optimization queries."""

from typing import Optional
from uuid import UUID

import strawberry
import structlog
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from strawberry.types import Info

from app.api.graphql.context import get_db_session, get_current_user_from_context
from app.api.graphql.types.optimization import (
    BudgetAllocationtype,
    BudgetScenarioType,
    OptimizationConstraintType,
    OptimizationResultType,
)
from app.core.exceptions import NotFoundError
from app.infrastructure.database.models.optimization import (
    BudgetAllocation,
    BudgetScenario,
    OptimizationConstraint,
    OptimizationResult,
)

logger = structlog.get_logger()


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


@strawberry.type
class OptimizationQuery:
    """Budget optimization queries."""

    @strawberry.field
    async def budget_scenarios(
        self,
        info: Info,
        is_active: Optional[bool] = None,
        model_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[BudgetScenarioType]:
        """Get all budget scenarios for the organization."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        query = (
            select(BudgetScenario)
            .options(
                selectinload(BudgetScenario.constraints),
                selectinload(BudgetScenario.results).selectinload(OptimizationResult.allocations),
            )
            .where(BudgetScenario.organization_id == current_user.organization_id)
        )

        if is_active is not None:
            query = query.where(BudgetScenario.is_active == is_active)

        if model_id is not None:
            query = query.where(BudgetScenario.model_id == model_id)

        query = query.order_by(BudgetScenario.created_at.desc()).offset(offset).limit(limit)

        result = await db.execute(query)
        scenarios = result.scalars().all()

        return [scenario_to_graphql(s) for s in scenarios]

    @strawberry.field
    async def budget_scenario(
        self,
        info: Info,
        scenario_id: UUID,
    ) -> BudgetScenarioType:
        """Get a specific budget scenario by ID."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

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

        return scenario_to_graphql(scenario)

    @strawberry.field
    async def optimization_result(
        self,
        info: Info,
        result_id: UUID,
    ) -> OptimizationResultType:
        """Get a specific optimization result by ID."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        # Join through scenario to check organization
        result = await db.execute(
            select(OptimizationResult)
            .options(selectinload(OptimizationResult.allocations))
            .join(BudgetScenario)
            .where(
                OptimizationResult.id == result_id,
                BudgetScenario.organization_id == current_user.organization_id,
            )
        )
        opt_result = result.scalar_one_or_none()

        if not opt_result:
            raise NotFoundError("Optimization result", str(result_id))

        return result_to_graphql(opt_result)

    @strawberry.field
    async def optimization_objectives(self) -> list[str]:
        """Get list of available optimization objectives."""
        return [
            "maximize_revenue",
            "maximize_conversions",
            "maximize_roi",
            "minimize_cpa",
            "target_revenue",
        ]
