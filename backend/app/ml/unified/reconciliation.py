"""
Signal Reconciliation Module

Advanced reconciliation methods for unifying measurement signals
when they conflict or provide different perspectives.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Literal
import numpy as np
import pandas as pd
from scipy import optimize
from enum import Enum


class ReconciliationMethod(str, Enum):
    """Available reconciliation methods."""
    WEIGHTED_AVERAGE = "weighted_average"
    BAYESIAN_UPDATE = "bayesian_update"
    HIERARCHICAL = "hierarchical"
    MINIMUM_VARIANCE = "minimum_variance"
    CONSTRAINED_OPTIMIZATION = "constrained_optimization"


@dataclass
class ReconciliationConfig:
    """Configuration for signal reconciliation."""

    method: ReconciliationMethod = ReconciliationMethod.BAYESIAN_UPDATE

    # Prior beliefs
    prior_mean: Optional[float] = None
    prior_std: Optional[float] = None

    # Constraints
    min_effect: float = 0.0
    max_effect: float = float("inf")
    total_constraint: Optional[float] = None  # Sum constraint for shares

    # Bayesian parameters
    likelihood_weight: float = 0.7
    prior_weight: float = 0.3

    # Optimization
    regularization: float = 0.01


@dataclass
class ReconciliationResult:
    """Result of signal reconciliation."""

    # Reconciled estimate
    reconciled_value: float
    reconciled_lower: float
    reconciled_upper: float

    # Quality metrics
    convergence_score: float  # How well methods agreed
    adjustment_magnitude: float  # How much reconciliation adjusted values

    # Component details
    method_used: ReconciliationMethod
    input_values: List[float]
    input_weights: List[float]

    # Diagnostics
    iterations: Optional[int] = None
    optimization_status: Optional[str] = None


class SignalReconciler:
    """
    Advanced Signal Reconciliation.

    Provides multiple methods for reconciling conflicting
    measurement signals into a unified estimate.

    Methods:
    - Weighted Average: Simple weighted combination
    - Bayesian Update: Sequential Bayesian updating
    - Hierarchical: Accounts for signal dependencies
    - Minimum Variance: Optimizes for lowest uncertainty
    - Constrained: Respects business constraints

    Example:
        config = ReconciliationConfig(method=ReconciliationMethod.BAYESIAN_UPDATE)
        reconciler = SignalReconciler(config)

        result = reconciler.reconcile(
            values=[0.5, 0.7, 0.6],
            uncertainties=[0.1, 0.15, 0.12],
            weights=[0.4, 0.3, 0.3],
        )
    """

    def __init__(self, config: Optional[ReconciliationConfig] = None):
        self.config = config or ReconciliationConfig()

    def reconcile(
        self,
        values: List[float],
        uncertainties: Optional[List[float]] = None,
        weights: Optional[List[float]] = None,
        method: Optional[ReconciliationMethod] = None,
    ) -> ReconciliationResult:
        """
        Reconcile multiple signal values.

        Args:
            values: Effect estimates from different signals
            uncertainties: Standard errors or CI widths
            weights: Quality/reliability weights
            method: Override default method

        Returns:
            ReconciliationResult with unified estimate
        """
        method = method or self.config.method
        values = np.array(values)
        n = len(values)

        # Default uncertainties if not provided
        if uncertainties is None:
            uncertainties = np.abs(values) * 0.2 + 1e-6
        else:
            uncertainties = np.array(uncertainties)

        # Default weights if not provided
        if weights is None:
            weights = np.ones(n) / n
        else:
            weights = np.array(weights)
            weights = weights / weights.sum()

        # Dispatch to method
        if method == ReconciliationMethod.WEIGHTED_AVERAGE:
            result = self._weighted_average(values, uncertainties, weights)
        elif method == ReconciliationMethod.BAYESIAN_UPDATE:
            result = self._bayesian_update(values, uncertainties, weights)
        elif method == ReconciliationMethod.HIERARCHICAL:
            result = self._hierarchical(values, uncertainties, weights)
        elif method == ReconciliationMethod.MINIMUM_VARIANCE:
            result = self._minimum_variance(values, uncertainties)
        elif method == ReconciliationMethod.CONSTRAINED_OPTIMIZATION:
            result = self._constrained_optimization(values, uncertainties, weights)
        else:
            result = self._weighted_average(values, uncertainties, weights)

        # Apply constraints
        result.reconciled_value = np.clip(
            result.reconciled_value,
            self.config.min_effect,
            self.config.max_effect,
        )

        # Compute adjustment magnitude
        result.adjustment_magnitude = np.abs(
            result.reconciled_value - np.mean(values)
        ) / (np.std(values) + 1e-6)

        result.method_used = method
        result.input_values = values.tolist()
        result.input_weights = weights.tolist()

        return result

    def _weighted_average(
        self,
        values: np.ndarray,
        uncertainties: np.ndarray,
        weights: np.ndarray,
    ) -> ReconciliationResult:
        """Simple weighted average reconciliation."""
        reconciled = np.average(values, weights=weights)

        # Weighted uncertainty propagation
        weighted_var = np.average(uncertainties**2, weights=weights**2)
        reconciled_std = np.sqrt(weighted_var)

        # Convergence based on coefficient of variation
        cv = np.std(values) / (np.abs(np.mean(values)) + 1e-6)
        convergence = 1.0 - np.clip(cv, 0, 1)

        return ReconciliationResult(
            reconciled_value=reconciled,
            reconciled_lower=reconciled - 1.96 * reconciled_std,
            reconciled_upper=reconciled + 1.96 * reconciled_std,
            convergence_score=convergence,
            adjustment_magnitude=0.0,
        )

    def _bayesian_update(
        self,
        values: np.ndarray,
        uncertainties: np.ndarray,
        weights: np.ndarray,
    ) -> ReconciliationResult:
        """
        Bayesian sequential updating.

        Treats signals as likelihood observations and updates
        a prior belief sequentially.
        """
        # Initialize prior
        if self.config.prior_mean is not None:
            prior_mean = self.config.prior_mean
            prior_var = (self.config.prior_std or 1.0) ** 2
        else:
            # Use first signal as prior
            prior_mean = values[0]
            prior_var = uncertainties[0] ** 2

        # Sequential Bayesian update
        posterior_mean = prior_mean
        posterior_var = prior_var

        for i in range(len(values)):
            # Likelihood from this signal
            obs_mean = values[i]
            obs_var = uncertainties[i] ** 2

            # Weight by signal quality
            effective_var = obs_var / weights[i]

            # Bayesian update (Gaussian conjugate)
            # Combined precision
            precision = 1.0 / posterior_var + 1.0 / effective_var
            posterior_var = 1.0 / precision

            # Updated mean
            posterior_mean = posterior_var * (
                posterior_mean / posterior_var + obs_mean / effective_var
            ) / 2

        posterior_std = np.sqrt(posterior_var)

        # Convergence score
        final_var_reduction = prior_var / (posterior_var + 1e-6)
        convergence = np.clip(1.0 - 1.0 / final_var_reduction, 0, 1)

        return ReconciliationResult(
            reconciled_value=posterior_mean,
            reconciled_lower=posterior_mean - 1.96 * posterior_std,
            reconciled_upper=posterior_mean + 1.96 * posterior_std,
            convergence_score=convergence,
            adjustment_magnitude=0.0,
            iterations=len(values),
        )

    def _hierarchical(
        self,
        values: np.ndarray,
        uncertainties: np.ndarray,
        weights: np.ndarray,
    ) -> ReconciliationResult:
        """
        Hierarchical reconciliation.

        Accounts for potential correlation between signals
        by estimating hyperparameters.
        """
        n = len(values)

        # Estimate population mean and variance (hyperparameters)
        pop_mean = np.average(values, weights=weights)
        pop_var = np.average((values - pop_mean)**2, weights=weights)

        # Shrinkage estimates - pull each estimate toward population mean
        shrunk_values = np.zeros(n)
        for i in range(n):
            # Shrinkage factor based on relative uncertainty
            obs_var = uncertainties[i] ** 2
            shrinkage = pop_var / (pop_var + obs_var)

            # Shrunk estimate
            shrunk_values[i] = shrinkage * values[i] + (1 - shrinkage) * pop_mean

        # Final reconciled value
        reconciled = np.average(shrunk_values, weights=weights)

        # Uncertainty from shrinkage
        shrunk_var = np.average((shrunk_values - reconciled)**2)
        reconciled_std = np.sqrt(shrunk_var + np.mean(uncertainties**2) / n)

        # Convergence
        cv = np.std(shrunk_values) / (np.abs(reconciled) + 1e-6)
        convergence = 1.0 - np.clip(cv, 0, 1)

        return ReconciliationResult(
            reconciled_value=reconciled,
            reconciled_lower=reconciled - 1.96 * reconciled_std,
            reconciled_upper=reconciled + 1.96 * reconciled_std,
            convergence_score=convergence,
            adjustment_magnitude=0.0,
        )

    def _minimum_variance(
        self,
        values: np.ndarray,
        uncertainties: np.ndarray,
    ) -> ReconciliationResult:
        """
        Minimum variance unbiased combination.

        Weights inversely by variance for optimal MSE.
        """
        variances = uncertainties ** 2

        # Inverse variance weights
        inv_var = 1.0 / (variances + 1e-6)
        mv_weights = inv_var / inv_var.sum()

        # Weighted combination
        reconciled = np.sum(mv_weights * values)

        # Combined variance
        combined_var = 1.0 / inv_var.sum()
        combined_std = np.sqrt(combined_var)

        # Convergence
        effective_n = (inv_var.sum()) ** 2 / (inv_var ** 2).sum()
        convergence = np.clip(effective_n / len(values), 0, 1)

        return ReconciliationResult(
            reconciled_value=reconciled,
            reconciled_lower=reconciled - 1.96 * combined_std,
            reconciled_upper=reconciled + 1.96 * combined_std,
            convergence_score=convergence,
            adjustment_magnitude=0.0,
        )

    def _constrained_optimization(
        self,
        values: np.ndarray,
        uncertainties: np.ndarray,
        weights: np.ndarray,
    ) -> ReconciliationResult:
        """
        Constrained optimization reconciliation.

        Minimizes weighted squared error subject to constraints.
        """
        def objective(x):
            # Weighted squared error from original signals
            errors = weights * (x - values) ** 2
            # Regularization
            reg = self.config.regularization * x ** 2
            return np.sum(errors) + reg

        # Bounds
        bounds = [(self.config.min_effect, self.config.max_effect)]

        # Initial guess
        x0 = np.average(values, weights=weights)

        # Optimize
        result = optimize.minimize(
            objective,
            x0,
            method='L-BFGS-B',
            bounds=bounds,
        )

        reconciled = result.x[0] if hasattr(result.x, '__len__') else result.x

        # Estimate uncertainty via Hessian
        try:
            hess_inv = result.hess_inv.todense() if hasattr(result.hess_inv, 'todense') else np.array([[1.0]])
            reconciled_std = np.sqrt(np.abs(hess_inv[0, 0]))
        except:
            reconciled_std = np.std(values)

        # Convergence based on optimization success
        convergence = 1.0 if result.success else 0.5

        return ReconciliationResult(
            reconciled_value=reconciled,
            reconciled_lower=reconciled - 1.96 * reconciled_std,
            reconciled_upper=reconciled + 1.96 * reconciled_std,
            convergence_score=convergence,
            adjustment_magnitude=0.0,
            iterations=result.nit,
            optimization_status="converged" if result.success else "not_converged",
        )

    def reconcile_all_channels(
        self,
        channel_signals: Dict[str, List[Dict]],
    ) -> Dict[str, ReconciliationResult]:
        """
        Reconcile signals for multiple channels.

        Args:
            channel_signals: Dict of channel -> list of signal dicts
                            Each dict has 'value', 'uncertainty', 'weight'

        Returns:
            Dict of channel -> ReconciliationResult
        """
        results = {}

        for channel, signals in channel_signals.items():
            values = [s['value'] for s in signals]
            uncertainties = [s.get('uncertainty', abs(s['value']) * 0.2) for s in signals]
            weights = [s.get('weight', 1.0) for s in signals]

            results[channel] = self.reconcile(values, uncertainties, weights)

        return results

    def compare_methods(
        self,
        values: List[float],
        uncertainties: Optional[List[float]] = None,
        weights: Optional[List[float]] = None,
    ) -> pd.DataFrame:
        """
        Compare results from all reconciliation methods.

        Useful for understanding sensitivity to method choice.
        """
        methods = [
            ReconciliationMethod.WEIGHTED_AVERAGE,
            ReconciliationMethod.BAYESIAN_UPDATE,
            ReconciliationMethod.HIERARCHICAL,
            ReconciliationMethod.MINIMUM_VARIANCE,
            ReconciliationMethod.CONSTRAINED_OPTIMIZATION,
        ]

        results = []
        for method in methods:
            result = self.reconcile(
                values, uncertainties, weights, method=method
            )
            results.append({
                'method': method.value,
                'reconciled_value': result.reconciled_value,
                'lower_bound': result.reconciled_lower,
                'upper_bound': result.reconciled_upper,
                'convergence': result.convergence_score,
                'adjustment': result.adjustment_magnitude,
            })

        return pd.DataFrame(results)
