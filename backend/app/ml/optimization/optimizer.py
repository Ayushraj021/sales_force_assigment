"""Budget optimization engine using convex optimization."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

import numpy as np
import pandas as pd
import structlog
from numpy.typing import NDArray

logger = structlog.get_logger()


@dataclass
class ChannelConstraint:
    """Constraint for a single channel."""

    channel_name: str
    min_spend: Optional[float] = None
    max_spend: Optional[float] = None
    min_ratio: Optional[float] = None  # Min % of total budget
    max_ratio: Optional[float] = None  # Max % of total budget
    fixed_spend: Optional[float] = None  # Fixed allocation
    max_increase_pct: Optional[float] = None  # Max increase from baseline
    max_decrease_pct: Optional[float] = None  # Max decrease from baseline


@dataclass
class OptimizationConfig:
    """Configuration for budget optimization."""

    # Objective
    objective: Literal[
        "maximize_revenue",
        "maximize_conversions",
        "maximize_roi",
        "minimize_cpa",
    ] = "maximize_revenue"

    # Budget
    total_budget: float = 100000.0
    periods: int = 1

    # Constraints
    channel_constraints: List[ChannelConstraint] = field(default_factory=list)

    # Solver settings
    solver: str = "ECOS"
    max_iterations: int = 1000
    tolerance: float = 1e-6

    # Response function parameters (from MMM)
    response_params: Dict[str, Dict[str, float]] = field(default_factory=dict)


class BudgetOptimizer:
    """Budget optimization using convex optimization.

    Uses CVXPY to solve the constrained optimization problem
    of allocating marketing budget across channels to maximize
    expected revenue/conversions.
    """

    def __init__(
        self,
        config: OptimizationConfig,
        response_function: Optional[Any] = None,
    ) -> None:
        """Initialize budget optimizer.

        Args:
            config: Optimization configuration.
            response_function: Optional function that maps spend to response.
                             If not provided, uses Hill saturation curves.
        """
        self.config = config
        self.response_function = response_function
        self._solution: Optional[Dict[str, float]] = None
        self._status: str = "not_solved"

    def _create_response_function(
        self,
        channel: str,
    ) -> callable:
        """Create response function for a channel using Hill curve."""
        from app.ml.transformers.saturation import HillSaturation

        params = self.config.response_params.get(channel, {})
        alpha = params.get("alpha", 2.0)
        gamma = params.get("gamma", 1.0)
        coefficient = params.get("coefficient", 1.0)

        saturation = HillSaturation()

        def response(x: float) -> float:
            return coefficient * saturation.transform(np.array([x]), alpha=alpha, gamma=gamma)[0]

        return response

    def _build_constraints(
        self,
        x: "cp.Variable",
        channels: List[str],
    ) -> List["cp.Constraint"]:
        """Build CVXPY constraints."""
        import cvxpy as cp

        constraints = []
        n_channels = len(channels)

        # Budget constraint
        constraints.append(cp.sum(x) <= self.config.total_budget)

        # Non-negativity
        constraints.append(x >= 0)

        # Channel-specific constraints
        for i, channel in enumerate(channels):
            channel_constraint = next(
                (c for c in self.config.channel_constraints if c.channel_name == channel),
                None,
            )

            if channel_constraint is None:
                continue

            # Fixed spend
            if channel_constraint.fixed_spend is not None:
                constraints.append(x[i] == channel_constraint.fixed_spend)
                continue

            # Min/max spend
            if channel_constraint.min_spend is not None:
                constraints.append(x[i] >= channel_constraint.min_spend)
            if channel_constraint.max_spend is not None:
                constraints.append(x[i] <= channel_constraint.max_spend)

            # Min/max ratio
            if channel_constraint.min_ratio is not None:
                constraints.append(x[i] >= channel_constraint.min_ratio * self.config.total_budget)
            if channel_constraint.max_ratio is not None:
                constraints.append(x[i] <= channel_constraint.max_ratio * self.config.total_budget)

        return constraints

    def optimize(
        self,
        channels: List[str],
        baseline_spend: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """Run budget optimization.

        Args:
            channels: List of channel names to optimize.
            baseline_spend: Optional baseline spend per channel.

        Returns:
            Dictionary with optimization results.
        """
        try:
            import cvxpy as cp
        except ImportError:
            raise ImportError("cvxpy required. Install with: pip install cvxpy")

        logger.info(
            "Starting budget optimization",
            objective=self.config.objective,
            total_budget=self.config.total_budget,
            n_channels=len(channels),
        )

        n_channels = len(channels)

        # Decision variables
        x = cp.Variable(n_channels, nonneg=True)

        # Build response functions for each channel
        response_funcs = {ch: self._create_response_function(ch) for ch in channels}

        # Calculate expected response (using approximation for convexity)
        # For Hill curves, we use a concave approximation
        total_response = 0
        for i, channel in enumerate(channels):
            params = self.config.response_params.get(channel, {})
            coefficient = params.get("coefficient", 1.0)
            gamma = params.get("gamma", 1.0)
            alpha = params.get("alpha", 2.0)

            # Use power function approximation for concavity
            # This is a simplification - actual implementation would use
            # disciplined convex programming or successive linear approximation
            if alpha >= 1:
                total_response += coefficient * cp.power(x[i] / gamma, 1 / alpha)
            else:
                total_response += coefficient * cp.power(x[i] / gamma, alpha)

        # Objective
        if self.config.objective in ["maximize_revenue", "maximize_conversions"]:
            objective = cp.Maximize(total_response)
        elif self.config.objective == "maximize_roi":
            # ROI = response / spend
            objective = cp.Maximize(total_response / cp.sum(x))
        elif self.config.objective == "minimize_cpa":
            # CPA = spend / conversions
            objective = cp.Minimize(cp.sum(x) / total_response)
        else:
            objective = cp.Maximize(total_response)

        # Constraints
        constraints = self._build_constraints(x, channels)

        # Add baseline change constraints
        if baseline_spend:
            for i, channel in enumerate(channels):
                channel_constraint = next(
                    (c for c in self.config.channel_constraints if c.channel_name == channel),
                    None,
                )
                if channel_constraint and channel in baseline_spend:
                    baseline = baseline_spend[channel]
                    if channel_constraint.max_increase_pct is not None:
                        max_val = baseline * (1 + channel_constraint.max_increase_pct / 100)
                        constraints.append(x[i] <= max_val)
                    if channel_constraint.max_decrease_pct is not None:
                        min_val = baseline * (1 - channel_constraint.max_decrease_pct / 100)
                        constraints.append(x[i] >= min_val)

        # Solve
        problem = cp.Problem(objective, constraints)

        try:
            problem.solve(solver=self.config.solver, verbose=False)
        except Exception as e:
            logger.error(f"Solver error: {e}")
            # Try alternative solver
            problem.solve(verbose=False)

        self._status = problem.status

        if problem.status not in ["optimal", "optimal_inaccurate"]:
            logger.warning(f"Optimization status: {problem.status}")
            return {
                "status": problem.status,
                "allocations": {},
                "objective_value": None,
            }

        # Extract solution
        allocations = {}
        for i, channel in enumerate(channels):
            allocations[channel] = {
                "allocated_budget": float(x.value[i]),
                "expected_response": float(response_funcs[channel](x.value[i])),
                "roi": float(response_funcs[channel](x.value[i]) / x.value[i]) if x.value[i] > 0 else 0,
            }

            if baseline_spend and channel in baseline_spend:
                baseline = baseline_spend[channel]
                change = x.value[i] - baseline
                allocations[channel]["baseline_budget"] = baseline
                allocations[channel]["change"] = change
                allocations[channel]["change_pct"] = (change / baseline * 100) if baseline > 0 else 0

        self._solution = allocations

        total_response_value = sum(a["expected_response"] for a in allocations.values())
        total_spend = sum(a["allocated_budget"] for a in allocations.values())

        logger.info(
            "Optimization completed",
            status=problem.status,
            total_spend=total_spend,
            expected_response=total_response_value,
        )

        return {
            "status": problem.status,
            "objective_value": float(problem.value) if problem.value else None,
            "total_spend": total_spend,
            "total_expected_response": total_response_value,
            "overall_roi": total_response_value / total_spend if total_spend > 0 else 0,
            "allocations": allocations,
        }

    def get_solution(self) -> Optional[Dict[str, float]]:
        """Get the optimization solution."""
        return self._solution

    def what_if_analysis(
        self,
        channels: List[str],
        spend_scenarios: List[Dict[str, float]],
    ) -> pd.DataFrame:
        """Run what-if analysis for different spend scenarios.

        Args:
            channels: List of channel names.
            spend_scenarios: List of dictionaries mapping channels to spend.

        Returns:
            DataFrame with scenario results.
        """
        results = []

        for i, scenario in enumerate(spend_scenarios):
            total_spend = sum(scenario.values())
            total_response = 0
            channel_responses = {}

            for channel, spend in scenario.items():
                if channel in channels:
                    response_func = self._create_response_function(channel)
                    response = response_func(spend)
                    total_response += response
                    channel_responses[channel] = response

            results.append(
                {
                    "scenario": i + 1,
                    "total_spend": total_spend,
                    "total_response": total_response,
                    "roi": total_response / total_spend if total_spend > 0 else 0,
                    **{f"{ch}_spend": scenario.get(ch, 0) for ch in channels},
                    **{f"{ch}_response": channel_responses.get(ch, 0) for ch in channels},
                }
            )

        return pd.DataFrame(results)
