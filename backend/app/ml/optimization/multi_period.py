"""
Multi-Period Budget Optimization

Optimize marketing budgets across multiple time periods.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
import numpy as np
import logging

logger = logging.getLogger(__name__)


class OptimizationObjective(str, Enum):
    """Optimization objectives."""
    MAXIMIZE_REVENUE = "maximize_revenue"
    MAXIMIZE_ROI = "maximize_roi"
    MAXIMIZE_REACH = "maximize_reach"
    MINIMIZE_CPA = "minimize_cpa"


@dataclass
class PeriodConstraints:
    """Constraints for a single period."""
    period_id: int
    min_budget: float = 0.0
    max_budget: float = float('inf')
    channel_min: Dict[str, float] = field(default_factory=dict)
    channel_max: Dict[str, float] = field(default_factory=dict)
    target_revenue: Optional[float] = None


@dataclass
class MultiPeriodConfig:
    """Configuration for multi-period optimization."""
    n_periods: int = 12
    total_budget: float = 1_000_000
    objective: OptimizationObjective = OptimizationObjective.MAXIMIZE_REVENUE
    channels: List[str] = field(default_factory=lambda: ["tv", "digital", "social"])

    # Constraints
    min_channel_budget: float = 0.0
    max_channel_concentration: float = 0.5  # Max share per channel

    # Temporal settings
    carryover_enabled: bool = True
    carryover_rate: float = 0.3  # Adstock carryover

    # Solver settings
    solver: str = "scipy"  # scipy, cvxpy
    max_iterations: int = 1000


@dataclass
class AllocationResult:
    """Result of budget allocation."""
    allocations: np.ndarray  # (n_periods, n_channels)
    period_budgets: np.ndarray  # (n_periods,)
    predicted_outcomes: np.ndarray  # (n_periods,)
    total_outcome: float
    roi: float
    channel_shares: Dict[str, float]
    optimization_status: str


class MultiPeriodOptimizer:
    """
    Multi-Period Budget Optimization.

    Features:
    - Optimize budget allocation across time periods
    - Handle carryover effects (adstock)
    - Support multiple objectives (revenue, ROI, reach)
    - Period-specific and global constraints

    Example:
        optimizer = MultiPeriodOptimizer(response_model, config)
        result = optimizer.optimize(
            period_constraints=constraints,
            initial_allocation=current_budget,
        )

        print(f"Optimal allocation: {result.allocations}")
        print(f"Expected revenue: {result.total_outcome}")
    """

    def __init__(
        self,
        response_model: Any,
        config: Optional[MultiPeriodConfig] = None,
    ):
        self.response_model = response_model
        self.config = config or MultiPeriodConfig()
        self.n_channels = len(self.config.channels)

    def optimize(
        self,
        period_constraints: Optional[List[PeriodConstraints]] = None,
        initial_allocation: Optional[np.ndarray] = None,
    ) -> AllocationResult:
        """
        Optimize budget allocation across periods.

        Args:
            period_constraints: Optional constraints per period
            initial_allocation: Optional starting allocation

        Returns:
            AllocationResult with optimal allocation
        """
        n_periods = self.config.n_periods
        n_channels = self.n_channels

        # Initialize
        if initial_allocation is None:
            # Uniform allocation
            per_period = self.config.total_budget / n_periods
            per_channel = per_period / n_channels
            initial_allocation = np.full((n_periods, n_channels), per_channel)

        # Set up period constraints
        if period_constraints is None:
            period_constraints = [
                PeriodConstraints(period_id=i)
                for i in range(n_periods)
            ]

        # Optimize based on solver
        if self.config.solver == "cvxpy":
            result = self._optimize_cvxpy(initial_allocation, period_constraints)
        else:
            result = self._optimize_scipy(initial_allocation, period_constraints)

        return result

    def _optimize_scipy(
        self,
        initial: np.ndarray,
        constraints: List[PeriodConstraints],
    ) -> AllocationResult:
        """Optimize using scipy."""
        from scipy.optimize import minimize

        n_periods = self.config.n_periods
        n_channels = self.n_channels

        # Flatten for optimizer
        x0 = initial.flatten()

        # Define objective
        def objective(x):
            allocations = x.reshape(n_periods, n_channels)
            outcomes = self._predict_outcomes(allocations)

            if self.config.objective == OptimizationObjective.MAXIMIZE_REVENUE:
                return -np.sum(outcomes)
            elif self.config.objective == OptimizationObjective.MAXIMIZE_ROI:
                total_spend = np.sum(allocations)
                total_revenue = np.sum(outcomes)
                return -(total_revenue - total_spend) / (total_spend + 1e-6)
            else:
                return -np.sum(outcomes)

        # Define constraints
        scipy_constraints = []

        # Total budget constraint
        scipy_constraints.append({
            'type': 'eq',
            'fun': lambda x: np.sum(x) - self.config.total_budget
        })

        # Per-period constraints
        for i, pc in enumerate(constraints):
            # Period budget bounds
            if pc.max_budget < float('inf'):
                scipy_constraints.append({
                    'type': 'ineq',
                    'fun': lambda x, i=i, max_b=pc.max_budget: max_b - np.sum(
                        x[i * n_channels:(i + 1) * n_channels]
                    )
                })

        # Bounds
        bounds = []
        for i in range(n_periods):
            for j, channel in enumerate(self.config.channels):
                min_val = self.config.min_channel_budget
                max_val = self.config.total_budget * self.config.max_channel_concentration

                # Check period-specific constraints
                if i < len(constraints):
                    if channel in constraints[i].channel_min:
                        min_val = max(min_val, constraints[i].channel_min[channel])
                    if channel in constraints[i].channel_max:
                        max_val = min(max_val, constraints[i].channel_max[channel])

                bounds.append((min_val, max_val))

        # Optimize
        result = minimize(
            objective,
            x0,
            method='SLSQP',
            bounds=bounds,
            constraints=scipy_constraints,
            options={'maxiter': self.config.max_iterations}
        )

        allocations = result.x.reshape(n_periods, n_channels)
        outcomes = self._predict_outcomes(allocations)

        # Calculate metrics
        total_outcome = float(np.sum(outcomes))
        total_spend = float(np.sum(allocations))
        roi = (total_outcome - total_spend) / total_spend if total_spend > 0 else 0

        channel_totals = np.sum(allocations, axis=0)
        channel_shares = {
            channel: float(channel_totals[i] / total_spend)
            for i, channel in enumerate(self.config.channels)
        }

        return AllocationResult(
            allocations=allocations,
            period_budgets=np.sum(allocations, axis=1),
            predicted_outcomes=outcomes,
            total_outcome=total_outcome,
            roi=roi,
            channel_shares=channel_shares,
            optimization_status="success" if result.success else "failed",
        )

    def _optimize_cvxpy(
        self,
        initial: np.ndarray,
        constraints: List[PeriodConstraints],
    ) -> AllocationResult:
        """Optimize using cvxpy."""
        try:
            import cvxpy as cp
        except ImportError:
            logger.warning("cvxpy not available, using scipy")
            return self._optimize_scipy(initial, constraints)

        n_periods = self.config.n_periods
        n_channels = self.n_channels

        # Decision variables
        X = cp.Variable((n_periods, n_channels), nonneg=True)

        # Build objective (using linear approximation for convexity)
        # Get response coefficients from model
        coeffs = self._get_response_coefficients()
        total_revenue = cp.sum(cp.multiply(coeffs, X))

        if self.config.objective == OptimizationObjective.MAXIMIZE_REVENUE:
            objective = cp.Maximize(total_revenue)
        else:
            objective = cp.Maximize(total_revenue)

        # Constraints
        cvxpy_constraints = [
            cp.sum(X) == self.config.total_budget,  # Total budget
        ]

        # Channel concentration
        for j in range(n_channels):
            cvxpy_constraints.append(
                cp.sum(X[:, j]) <= self.config.total_budget * self.config.max_channel_concentration
            )

        # Period-specific constraints
        for i, pc in enumerate(constraints):
            cvxpy_constraints.append(cp.sum(X[i, :]) >= pc.min_budget)
            if pc.max_budget < float('inf'):
                cvxpy_constraints.append(cp.sum(X[i, :]) <= pc.max_budget)

        # Solve
        problem = cp.Problem(objective, cvxpy_constraints)
        problem.solve(solver=cp.ECOS)

        if problem.status not in ["optimal", "optimal_inaccurate"]:
            logger.warning(f"CVXPY status: {problem.status}")
            return self._optimize_scipy(initial, constraints)

        allocations = X.value
        outcomes = self._predict_outcomes(allocations)

        total_outcome = float(np.sum(outcomes))
        total_spend = float(np.sum(allocations))
        roi = (total_outcome - total_spend) / total_spend if total_spend > 0 else 0

        channel_totals = np.sum(allocations, axis=0)
        channel_shares = {
            channel: float(channel_totals[i] / total_spend)
            for i, channel in enumerate(self.config.channels)
        }

        return AllocationResult(
            allocations=allocations,
            period_budgets=np.sum(allocations, axis=1),
            predicted_outcomes=outcomes,
            total_outcome=total_outcome,
            roi=roi,
            channel_shares=channel_shares,
            optimization_status=problem.status,
        )

    def _predict_outcomes(self, allocations: np.ndarray) -> np.ndarray:
        """Predict outcomes for given allocations."""
        n_periods = allocations.shape[0]
        outcomes = np.zeros(n_periods)

        # Apply carryover if enabled
        if self.config.carryover_enabled:
            effective_spend = self._apply_carryover(allocations)
        else:
            effective_spend = allocations

        for t in range(n_periods):
            try:
                if hasattr(self.response_model, 'predict'):
                    outcomes[t] = self.response_model.predict(
                        effective_spend[t].reshape(1, -1)
                    )[0]
                else:
                    # Simple response function
                    outcomes[t] = self._default_response(effective_spend[t])
            except Exception:
                outcomes[t] = self._default_response(effective_spend[t])

        return outcomes

    def _apply_carryover(self, allocations: np.ndarray) -> np.ndarray:
        """Apply adstock carryover effect."""
        n_periods, n_channels = allocations.shape
        effective = np.zeros_like(allocations)

        for j in range(n_channels):
            for t in range(n_periods):
                if t == 0:
                    effective[t, j] = allocations[t, j]
                else:
                    effective[t, j] = (
                        allocations[t, j] +
                        self.config.carryover_rate * effective[t - 1, j]
                    )

        return effective

    def _get_response_coefficients(self) -> np.ndarray:
        """Extract response coefficients from model."""
        if hasattr(self.response_model, 'coef_'):
            return np.abs(self.response_model.coef_)
        elif hasattr(self.response_model, 'feature_importances_'):
            return self.response_model.feature_importances_

        # Default coefficients
        return np.ones(self.n_channels)

    def _default_response(self, spend: np.ndarray) -> float:
        """Default response function (Hill curve)."""
        response = 0.0
        for i, s in enumerate(spend):
            # Hill function: s^a / (k^a + s^a)
            k = 10000  # Half-saturation
            a = 0.7  # Hill exponent
            response += (s ** a) / (k ** a + s ** a) * 100000

        return response


class PortfolioOptimizer:
    """
    Portfolio Optimization for Marketing Channels.

    Uses Markowitz-style optimization to balance return and risk.
    """

    def __init__(
        self,
        channels: List[str],
        risk_aversion: float = 1.0,
    ):
        self.channels = channels
        self.risk_aversion = risk_aversion
        self._returns: Optional[np.ndarray] = None
        self._covariance: Optional[np.ndarray] = None

    def fit(
        self,
        returns: np.ndarray,  # (n_periods, n_channels)
    ) -> "PortfolioOptimizer":
        """Fit optimizer with historical returns."""
        self._returns = returns
        self._covariance = np.cov(returns.T)
        return self

    def optimize(
        self,
        total_budget: float,
        min_weight: float = 0.0,
        max_weight: float = 1.0,
    ) -> Dict[str, float]:
        """Optimize portfolio allocation."""
        if self._returns is None:
            raise ValueError("Optimizer not fitted")

        n_channels = len(self.channels)
        mean_returns = np.mean(self._returns, axis=0)

        try:
            import cvxpy as cp

            weights = cp.Variable(n_channels, nonneg=True)

            # Portfolio return
            portfolio_return = mean_returns @ weights

            # Portfolio variance
            portfolio_variance = cp.quad_form(weights, self._covariance)

            # Objective: maximize return - risk_aversion * variance
            objective = cp.Maximize(portfolio_return - self.risk_aversion * portfolio_variance)

            constraints = [
                cp.sum(weights) == 1.0,
                weights >= min_weight,
                weights <= max_weight,
            ]

            problem = cp.Problem(objective, constraints)
            problem.solve()

            optimal_weights = weights.value

        except ImportError:
            # Fallback to equal weights
            optimal_weights = np.ones(n_channels) / n_channels

        # Convert to allocations
        allocations = {
            channel: float(optimal_weights[i] * total_budget)
            for i, channel in enumerate(self.channels)
        }

        return allocations

    def get_efficient_frontier(
        self,
        n_points: int = 20,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Calculate efficient frontier."""
        if self._returns is None:
            raise ValueError("Optimizer not fitted")

        mean_returns = np.mean(self._returns, axis=0)

        returns_range = np.linspace(
            mean_returns.min(),
            mean_returns.max(),
            n_points
        )

        frontier_returns = []
        frontier_volatility = []

        for target_return in returns_range:
            try:
                import cvxpy as cp

                n = len(self.channels)
                weights = cp.Variable(n, nonneg=True)

                variance = cp.quad_form(weights, self._covariance)
                objective = cp.Minimize(variance)

                constraints = [
                    cp.sum(weights) == 1.0,
                    mean_returns @ weights >= target_return,
                ]

                problem = cp.Problem(objective, constraints)
                problem.solve()

                if problem.status == "optimal":
                    frontier_returns.append(target_return)
                    frontier_volatility.append(np.sqrt(variance.value))

            except Exception:
                continue

        return np.array(frontier_returns), np.array(frontier_volatility)
