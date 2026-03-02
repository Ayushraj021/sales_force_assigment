"""Optimization GraphQL types."""

from datetime import datetime
from typing import Optional
from uuid import UUID

import strawberry
from strawberry.scalars import JSON


@strawberry.type
class OptimizationConstraintType:
    """Optimization constraint type."""

    id: UUID
    constraint_type: str
    channel_name: Optional[str]
    min_value: Optional[float]
    max_value: Optional[float]
    fixed_value: Optional[float]
    min_ratio: Optional[float]
    max_ratio: Optional[float]
    max_increase_pct: Optional[float]
    max_decrease_pct: Optional[float]


@strawberry.type
class BudgetAllocationtype:
    """Budget allocation for a channel."""

    id: UUID
    channel_name: str
    period: int
    allocated_budget: float
    baseline_budget: Optional[float]
    change_pct: Optional[float]
    expected_contribution: Optional[float]
    expected_roi: Optional[float]
    marginal_roi: Optional[float]
    saturation_level: Optional[float]


@strawberry.type
class OptimizationResultType:
    """Optimization result type."""

    id: UUID
    status: str
    solver_status: Optional[str]
    objective_value: Optional[float]
    baseline_value: Optional[float]
    improvement_pct: Optional[float]
    total_spend: Optional[float]
    expected_revenue: Optional[float]
    expected_roi: Optional[float]
    solver_time_seconds: Optional[float]
    allocations: list[BudgetAllocationtype]
    created_at: datetime


@strawberry.type
class BudgetScenarioType:
    """Budget scenario type."""

    id: UUID
    name: str
    description: Optional[str]
    is_active: bool
    total_budget: float
    budget_period: str
    currency: str
    objective: str
    target_value: Optional[float]
    start_date: Optional[str]
    end_date: Optional[str]
    periods: int
    constraints: list[OptimizationConstraintType]
    results: list[OptimizationResultType]
    created_at: datetime
    updated_at: datetime


@strawberry.input
class ConstraintInput:
    """Input for optimization constraint."""

    constraint_type: str  # min, max, fixed, ratio
    channel_name: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    fixed_value: Optional[float] = None
    min_ratio: Optional[float] = None
    max_ratio: Optional[float] = None
    max_increase_pct: Optional[float] = None
    max_decrease_pct: Optional[float] = None


@strawberry.input
class CreateBudgetScenarioInput:
    """Input for creating a budget scenario."""

    name: str
    description: Optional[str] = None
    total_budget: float
    budget_period: str = "monthly"  # weekly, monthly, quarterly
    currency: str = "USD"
    objective: str  # maximize_revenue, maximize_conversions, maximize_roi, minimize_cpa
    target_value: Optional[float] = None
    model_id: UUID
    constraints: Optional[list[ConstraintInput]] = None


@strawberry.input
class RunOptimizationInput:
    """Input for running optimization."""

    scenario_id: UUID
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    periods: int = 1


@strawberry.type
class WhatIfResult:
    """What-if analysis result."""

    channel_name: str
    current_spend: float
    proposed_spend: float
    current_contribution: float
    expected_contribution: float
    change_pct: float
    marginal_roi: float


@strawberry.type
class WhatIfAnalysisType:
    """What-if analysis results."""

    total_current_spend: float
    total_proposed_spend: float
    total_current_contribution: float
    total_expected_contribution: float
    overall_change_pct: float
    channel_results: list[WhatIfResult]


@strawberry.input
class WhatIfInput:
    """Input for what-if analysis."""

    model_id: UUID
    channel_spends: JSON  # {"channel_name": spend_amount}
