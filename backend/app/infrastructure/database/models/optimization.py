"""Budget optimization models."""

import uuid
from enum import Enum

from sqlalchemy import Boolean, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.models.base import TimestampMixin, UUIDMixin
from app.infrastructure.database.session import Base


class OptimizationObjective(str, Enum):
    """Optimization objective types."""

    MAXIMIZE_REVENUE = "maximize_revenue"
    MAXIMIZE_CONVERSIONS = "maximize_conversions"
    MAXIMIZE_ROI = "maximize_roi"
    MINIMIZE_CPA = "minimize_cpa"
    TARGET_REVENUE = "target_revenue"


class BudgetScenario(Base, UUIDMixin, TimestampMixin):
    """Budget scenario for optimization."""

    __tablename__ = "budget_scenarios"

    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Budget settings
    total_budget: Mapped[float] = mapped_column(Float)
    budget_period: Mapped[str] = mapped_column(String(20))  # weekly, monthly, quarterly
    currency: Mapped[str] = mapped_column(String(10), default="USD")

    # Objective
    objective: Mapped[str] = mapped_column(String(50))
    target_value: Mapped[float | None] = mapped_column(Float)

    # Time horizon
    start_date: Mapped[str | None] = mapped_column(String(20))
    end_date: Mapped[str | None] = mapped_column(String(20))
    periods: Mapped[int] = mapped_column(default=1)

    # Configuration
    config: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Relationships
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True
    )

    model_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("models.id")
    )

    constraints: Mapped[list["OptimizationConstraint"]] = relationship(
        back_populates="scenario"
    )
    results: Mapped[list["OptimizationResult"]] = relationship(
        back_populates="scenario"
    )


class OptimizationConstraint(Base, UUIDMixin, TimestampMixin):
    """Constraints for budget optimization."""

    __tablename__ = "optimization_constraints"

    constraint_type: Mapped[str] = mapped_column(String(50))  # min, max, fixed, ratio
    channel_name: Mapped[str | None] = mapped_column(String(255))

    # Constraint values
    min_value: Mapped[float | None] = mapped_column(Float)
    max_value: Mapped[float | None] = mapped_column(Float)
    fixed_value: Mapped[float | None] = mapped_column(Float)

    # Ratio constraints (percentage of total)
    min_ratio: Mapped[float | None] = mapped_column(Float)
    max_ratio: Mapped[float | None] = mapped_column(Float)

    # Change constraints (vs baseline)
    max_increase_pct: Mapped[float | None] = mapped_column(Float)
    max_decrease_pct: Mapped[float | None] = mapped_column(Float)

    # Relationship
    scenario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("budget_scenarios.id"), index=True
    )
    scenario: Mapped["BudgetScenario"] = relationship(back_populates="constraints")


class OptimizationResult(Base, UUIDMixin, TimestampMixin):
    """Results from budget optimization."""

    __tablename__ = "optimization_results"

    status: Mapped[str] = mapped_column(String(50))  # optimal, infeasible, timeout
    solver_status: Mapped[str | None] = mapped_column(String(50))

    # Objective value
    objective_value: Mapped[float | None] = mapped_column(Float)
    baseline_value: Mapped[float | None] = mapped_column(Float)
    improvement_pct: Mapped[float | None] = mapped_column(Float)

    # Metrics
    total_spend: Mapped[float | None] = mapped_column(Float)
    expected_revenue: Mapped[float | None] = mapped_column(Float)
    expected_roi: Mapped[float | None] = mapped_column(Float)

    # Solver info
    solver_time_seconds: Mapped[float | None] = mapped_column(Float)
    iterations: Mapped[int | None] = mapped_column()

    # Full results
    results_json: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Relationships
    scenario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("budget_scenarios.id"), index=True
    )
    scenario: Mapped["BudgetScenario"] = relationship(back_populates="results")

    allocations: Mapped[list["BudgetAllocation"]] = relationship(
        back_populates="optimization_result"
    )


class BudgetAllocation(Base, UUIDMixin, TimestampMixin):
    """Individual channel budget allocation."""

    __tablename__ = "budget_allocations"

    channel_name: Mapped[str] = mapped_column(String(255), index=True)
    period: Mapped[int] = mapped_column(default=1)

    # Allocation values
    allocated_budget: Mapped[float] = mapped_column(Float)
    baseline_budget: Mapped[float | None] = mapped_column(Float)
    change_pct: Mapped[float | None] = mapped_column(Float)

    # Expected outcomes
    expected_contribution: Mapped[float | None] = mapped_column(Float)
    expected_roi: Mapped[float | None] = mapped_column(Float)
    marginal_roi: Mapped[float | None] = mapped_column(Float)

    # Saturation info
    saturation_level: Mapped[float | None] = mapped_column(Float)

    # Relationship
    optimization_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("optimization_results.id"), index=True
    )
    optimization_result: Mapped["OptimizationResult"] = relationship(
        back_populates="allocations"
    )
