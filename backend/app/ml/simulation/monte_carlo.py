"""
Monte Carlo Simulation

Scenario simulation and sensitivity analysis.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable, Tuple
from enum import Enum
import numpy as np
from datetime import datetime
import logging
from concurrent.futures import ProcessPoolExecutor

logger = logging.getLogger(__name__)


class DistributionType(str, Enum):
    """Distribution types for input variables."""
    NORMAL = "normal"
    UNIFORM = "uniform"
    TRIANGULAR = "triangular"
    LOGNORMAL = "lognormal"
    BETA = "beta"
    POISSON = "poisson"


@dataclass
class Variable:
    """Input variable for simulation."""
    name: str
    distribution: DistributionType
    params: Dict[str, float]  # Distribution parameters
    base_value: Optional[float] = None

    def sample(self, n_samples: int) -> np.ndarray:
        """Generate samples from distribution."""
        if self.distribution == DistributionType.NORMAL:
            return np.random.normal(
                self.params.get("mean", 0),
                self.params.get("std", 1),
                n_samples
            )
        elif self.distribution == DistributionType.UNIFORM:
            return np.random.uniform(
                self.params.get("low", 0),
                self.params.get("high", 1),
                n_samples
            )
        elif self.distribution == DistributionType.TRIANGULAR:
            return np.random.triangular(
                self.params.get("left", 0),
                self.params.get("mode", 0.5),
                self.params.get("right", 1),
                n_samples
            )
        elif self.distribution == DistributionType.LOGNORMAL:
            return np.random.lognormal(
                self.params.get("mean", 0),
                self.params.get("sigma", 1),
                n_samples
            )
        elif self.distribution == DistributionType.BETA:
            return np.random.beta(
                self.params.get("a", 2),
                self.params.get("b", 2),
                n_samples
            )
        elif self.distribution == DistributionType.POISSON:
            return np.random.poisson(
                self.params.get("lam", 1),
                n_samples
            )
        else:
            return np.random.normal(0, 1, n_samples)


@dataclass
class SimulationResult:
    """Results of Monte Carlo simulation."""
    n_simulations: int
    outcomes: np.ndarray
    mean: float
    std: float
    median: float
    percentiles: Dict[int, float]
    var_95: float  # Value at Risk 95%
    cvar_95: float  # Conditional VaR 95%
    input_samples: Dict[str, np.ndarray]
    runtime: float

    def get_confidence_interval(self, confidence: float = 0.95) -> Tuple[float, float]:
        """Get confidence interval for outcome."""
        alpha = (1 - confidence) / 2
        lower = np.percentile(self.outcomes, alpha * 100)
        upper = np.percentile(self.outcomes, (1 - alpha) * 100)
        return float(lower), float(upper)

    def probability_above(self, threshold: float) -> float:
        """Calculate probability of exceeding threshold."""
        return float(np.mean(self.outcomes > threshold))

    def probability_below(self, threshold: float) -> float:
        """Calculate probability of falling below threshold."""
        return float(np.mean(self.outcomes < threshold))


@dataclass
class MonteCarloConfig:
    """Configuration for Monte Carlo simulation."""
    n_simulations: int = 10000
    seed: Optional[int] = 42
    parallel: bool = True
    n_jobs: int = -1
    antithetic: bool = True  # Variance reduction


class MonteCarloSimulator:
    """
    Monte Carlo Simulator for Marketing Scenarios.

    Features:
    - Flexible input distributions
    - Variance reduction techniques
    - Parallel execution
    - Risk metrics (VaR, CVaR)

    Example:
        simulator = MonteCarloSimulator(model_fn, config)

        variables = [
            Variable("tv_spend", DistributionType.NORMAL, {"mean": 50000, "std": 5000}),
            Variable("digital_spend", DistributionType.UNIFORM, {"low": 20000, "high": 40000}),
        ]

        result = simulator.simulate(variables)
        print(f"Expected outcome: {result.mean}")
        print(f"95% CI: {result.get_confidence_interval()}")
    """

    def __init__(
        self,
        model_fn: Callable[[Dict[str, float]], float],
        config: Optional[MonteCarloConfig] = None,
    ):
        self.model_fn = model_fn
        self.config = config or MonteCarloConfig()

        if self.config.seed is not None:
            np.random.seed(self.config.seed)

    def simulate(
        self,
        variables: List[Variable],
    ) -> SimulationResult:
        """
        Run Monte Carlo simulation.

        Args:
            variables: List of input variables with distributions

        Returns:
            SimulationResult with outcome statistics
        """
        start_time = datetime.now()
        n = self.config.n_simulations

        # Generate samples
        input_samples = {}
        for var in variables:
            samples = var.sample(n)

            # Antithetic variates for variance reduction
            if self.config.antithetic:
                if var.distribution == DistributionType.NORMAL:
                    antithetic = 2 * var.params.get("mean", 0) - samples
                    samples = np.concatenate([samples[:n // 2], antithetic[:n // 2]])

            input_samples[var.name] = samples

        # Run simulations
        outcomes = np.zeros(n)

        for i in range(n):
            inputs = {name: samples[i] for name, samples in input_samples.items()}
            outcomes[i] = self.model_fn(inputs)

        runtime = (datetime.now() - start_time).total_seconds()

        # Calculate statistics
        mean = float(np.mean(outcomes))
        std = float(np.std(outcomes))
        median = float(np.median(outcomes))

        percentiles = {
            5: float(np.percentile(outcomes, 5)),
            10: float(np.percentile(outcomes, 10)),
            25: float(np.percentile(outcomes, 25)),
            50: float(np.percentile(outcomes, 50)),
            75: float(np.percentile(outcomes, 75)),
            90: float(np.percentile(outcomes, 90)),
            95: float(np.percentile(outcomes, 95)),
        }

        # Value at Risk (5th percentile for losses)
        var_95 = float(np.percentile(outcomes, 5))

        # Conditional VaR (expected value below VaR)
        cvar_95 = float(np.mean(outcomes[outcomes <= var_95]))

        return SimulationResult(
            n_simulations=n,
            outcomes=outcomes,
            mean=mean,
            std=std,
            median=median,
            percentiles=percentiles,
            var_95=var_95,
            cvar_95=cvar_95,
            input_samples=input_samples,
            runtime=runtime,
        )

    def sensitivity_analysis(
        self,
        variables: List[Variable],
        n_points: int = 20,
    ) -> Dict[str, np.ndarray]:
        """
        One-at-a-time sensitivity analysis.

        Returns:
            Dict mapping variable names to (values, outcomes) arrays
        """
        results = {}

        # Get base values
        base_inputs = {
            var.name: var.base_value or var.params.get("mean", 0)
            for var in variables
        }

        for var in variables:
            # Define range
            if var.distribution == DistributionType.NORMAL:
                low = var.params.get("mean", 0) - 2 * var.params.get("std", 1)
                high = var.params.get("mean", 0) + 2 * var.params.get("std", 1)
            elif var.distribution == DistributionType.UNIFORM:
                low = var.params.get("low", 0)
                high = var.params.get("high", 1)
            else:
                low = var.params.get("mean", 0) * 0.5
                high = var.params.get("mean", 0) * 1.5

            values = np.linspace(low, high, n_points)
            outcomes = np.zeros(n_points)

            for i, val in enumerate(values):
                inputs = base_inputs.copy()
                inputs[var.name] = val
                outcomes[i] = self.model_fn(inputs)

            results[var.name] = {
                "values": values,
                "outcomes": outcomes,
                "sensitivity": float(np.std(outcomes) / (np.std(values) + 1e-10)),
            }

        return results

    def scenario_analysis(
        self,
        scenarios: List[Dict[str, float]],
        scenario_names: Optional[List[str]] = None,
    ) -> Dict[str, float]:
        """
        Evaluate specific scenarios.

        Args:
            scenarios: List of input dicts for each scenario
            scenario_names: Optional names for scenarios

        Returns:
            Dict mapping scenario names to outcomes
        """
        if scenario_names is None:
            scenario_names = [f"Scenario_{i}" for i in range(len(scenarios))]

        results = {}
        for name, inputs in zip(scenario_names, scenarios):
            results[name] = self.model_fn(inputs)

        return results


class SensitivityAnalyzer:
    """
    Sensitivity Analysis for Marketing Models.

    Provides multiple sensitivity analysis methods.
    """

    def __init__(
        self,
        model_fn: Callable,
        variable_names: List[str],
        base_values: Dict[str, float],
    ):
        self.model_fn = model_fn
        self.variable_names = variable_names
        self.base_values = base_values

    def one_at_a_time(
        self,
        perturbation: float = 0.1,
    ) -> Dict[str, float]:
        """
        One-at-a-time sensitivity analysis.

        Returns elasticity for each variable.
        """
        base_output = self.model_fn(self.base_values)
        sensitivities = {}

        for var in self.variable_names:
            base_val = self.base_values[var]

            # Perturb up
            inputs_up = self.base_values.copy()
            inputs_up[var] = base_val * (1 + perturbation)
            output_up = self.model_fn(inputs_up)

            # Calculate elasticity
            pct_change_output = (output_up - base_output) / base_output
            pct_change_input = perturbation

            elasticity = pct_change_output / pct_change_input
            sensitivities[var] = float(elasticity)

        return sensitivities

    def tornado_diagram_data(
        self,
        ranges: Dict[str, Tuple[float, float]],
    ) -> Dict[str, Dict[str, float]]:
        """
        Generate data for tornado diagram.

        Args:
            ranges: Dict mapping variable to (low, high) range

        Returns:
            Dict with low/high outputs for each variable
        """
        results = {}

        for var in self.variable_names:
            if var not in ranges:
                continue

            low_val, high_val = ranges[var]

            # Low scenario
            inputs_low = self.base_values.copy()
            inputs_low[var] = low_val
            output_low = self.model_fn(inputs_low)

            # High scenario
            inputs_high = self.base_values.copy()
            inputs_high[var] = high_val
            output_high = self.model_fn(inputs_high)

            results[var] = {
                "low_input": low_val,
                "high_input": high_val,
                "low_output": float(output_low),
                "high_output": float(output_high),
                "range": float(abs(output_high - output_low)),
            }

        # Sort by range
        results = dict(sorted(
            results.items(),
            key=lambda x: x[1]["range"],
            reverse=True
        ))

        return results

    def morris_method(
        self,
        bounds: Dict[str, Tuple[float, float]],
        n_trajectories: int = 10,
        n_levels: int = 4,
    ) -> Dict[str, Dict[str, float]]:
        """
        Morris screening method for sensitivity analysis.

        Returns mean and std of elementary effects.
        """
        k = len(self.variable_names)
        effects = {var: [] for var in self.variable_names}

        for _ in range(n_trajectories):
            # Generate random starting point
            x = np.random.randint(0, n_levels, k) / (n_levels - 1)

            # Create trajectory
            for i, var in enumerate(self.variable_names):
                # Get actual values
                low, high = bounds.get(var, (0, 1))
                x_val = low + x[i] * (high - low)

                inputs = {}
                for j, v in enumerate(self.variable_names):
                    l, h = bounds.get(v, (0, 1))
                    inputs[v] = l + x[j] * (h - l)

                y1 = self.model_fn(inputs)

                # Perturb
                delta = 1 / (n_levels - 1)
                x[i] = min(1, x[i] + delta)

                inputs[var] = low + x[i] * (high - low)
                y2 = self.model_fn(inputs)

                effect = (y2 - y1) / delta
                effects[var].append(effect)

        # Calculate statistics
        results = {}
        for var in self.variable_names:
            eff = np.array(effects[var])
            results[var] = {
                "mean": float(np.mean(np.abs(eff))),  # Mean absolute effect
                "std": float(np.std(eff)),
            }

        return results
