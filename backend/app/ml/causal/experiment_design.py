"""
Experiment Design Module

Tools for designing and analyzing marketing experiments including:
- Power analysis
- Sample size calculations
- Optimal treatment/control splits
- Multi-arm experiment design
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats


class ExperimentType(str, Enum):
    """Types of experiments supported."""

    AB_TEST = "ab_test"
    GEO_EXPERIMENT = "geo_experiment"
    HOLDOUT = "holdout"
    SWITCHBACK = "switchback"
    MULTI_ARM = "multi_arm"


@dataclass
class PowerAnalysisResult:
    """Result from power analysis."""

    # Core metrics
    power: float
    sample_size_per_arm: int
    total_sample_size: int

    # Effect size
    minimum_detectable_effect: float
    effect_type: str  # "absolute" or "relative"

    # Test parameters
    alpha: float
    n_arms: int

    # Variance estimates
    baseline_mean: float
    baseline_std: float

    # Duration (for time-based experiments)
    recommended_duration_days: Optional[int] = None


@dataclass
class ExperimentDesign:
    """Complete experiment design specification."""

    experiment_type: ExperimentType

    # Assignment
    treatment_units: list[str]
    control_units: list[str]

    # Timing
    start_date: str
    end_date: str
    warmup_days: int

    # Power
    power_analysis: PowerAnalysisResult

    # Monitoring
    interim_analysis_dates: list[str]
    stopping_rules: dict

    # Metrics
    primary_metric: str
    secondary_metrics: list[str]
    guardrail_metrics: list[str]


class ExperimentDesigner:
    """
    Experiment design and power analysis tool.

    Helps design experiments with proper statistical power
    and valid inference.

    Example:
        designer = ExperimentDesigner()
        power = designer.calculate_power(
            baseline_mean=100,
            baseline_std=20,
            mde=0.05,
            sample_size=1000
        )
    """

    def __init__(self, seed: Optional[int] = None):
        self.seed = seed
        self._rng = np.random.default_rng(seed)

    def calculate_power(
        self,
        baseline_mean: float,
        baseline_std: float,
        mde: float,
        sample_size_per_arm: int,
        alpha: float = 0.05,
        n_arms: int = 2,
        one_sided: bool = False,
    ) -> PowerAnalysisResult:
        """
        Calculate statistical power for an experiment.

        Args:
            baseline_mean: Expected mean of control group
            baseline_std: Expected standard deviation
            mde: Minimum detectable effect (as proportion of baseline)
            sample_size_per_arm: Sample size in each arm
            alpha: Significance level
            n_arms: Number of experiment arms
            one_sided: Whether to use one-sided test

        Returns:
            PowerAnalysisResult with power and recommendations
        """
        # Calculate effect size
        absolute_effect = mde * baseline_mean
        pooled_std = baseline_std

        # Standard error
        se = pooled_std * np.sqrt(2 / sample_size_per_arm)

        # Critical value
        if one_sided:
            z_alpha = stats.norm.ppf(1 - alpha)
        else:
            z_alpha = stats.norm.ppf(1 - alpha / 2)

        # Power
        z_power = (absolute_effect - z_alpha * se) / se
        power = stats.norm.cdf(z_power)

        # Adjust for multiple comparisons if multi-arm
        if n_arms > 2:
            # Bonferroni correction
            adjusted_alpha = alpha / (n_arms - 1)
            z_alpha_adj = stats.norm.ppf(1 - adjusted_alpha / 2)
            z_power_adj = (absolute_effect - z_alpha_adj * se) / se
            power = stats.norm.cdf(z_power_adj)

        return PowerAnalysisResult(
            power=max(0, min(1, power)),
            sample_size_per_arm=sample_size_per_arm,
            total_sample_size=sample_size_per_arm * n_arms,
            minimum_detectable_effect=mde,
            effect_type="relative",
            alpha=alpha,
            n_arms=n_arms,
            baseline_mean=baseline_mean,
            baseline_std=baseline_std,
        )

    def calculate_sample_size(
        self,
        baseline_mean: float,
        baseline_std: float,
        mde: float,
        power: float = 0.8,
        alpha: float = 0.05,
        n_arms: int = 2,
        one_sided: bool = False,
    ) -> PowerAnalysisResult:
        """
        Calculate required sample size for desired power.

        Args:
            baseline_mean: Expected mean of control group
            baseline_std: Expected standard deviation
            mde: Minimum detectable effect (as proportion)
            power: Desired statistical power
            alpha: Significance level
            n_arms: Number of experiment arms
            one_sided: Whether to use one-sided test

        Returns:
            PowerAnalysisResult with required sample sizes
        """
        # Effect size in standard deviation units
        absolute_effect = mde * baseline_mean
        effect_size = absolute_effect / baseline_std

        # Critical values
        if one_sided:
            z_alpha = stats.norm.ppf(1 - alpha)
        else:
            z_alpha = stats.norm.ppf(1 - alpha / 2)
        z_power = stats.norm.ppf(power)

        # Sample size per arm
        n_per_arm = 2 * ((z_alpha + z_power) / effect_size) ** 2

        # Adjust for multiple comparisons
        if n_arms > 2:
            adjusted_alpha = alpha / (n_arms - 1)
            z_alpha_adj = stats.norm.ppf(1 - adjusted_alpha / 2)
            n_per_arm = 2 * ((z_alpha_adj + z_power) / effect_size) ** 2

        n_per_arm = int(np.ceil(n_per_arm))

        return PowerAnalysisResult(
            power=power,
            sample_size_per_arm=n_per_arm,
            total_sample_size=n_per_arm * n_arms,
            minimum_detectable_effect=mde,
            effect_type="relative",
            alpha=alpha,
            n_arms=n_arms,
            baseline_mean=baseline_mean,
            baseline_std=baseline_std,
        )

    def calculate_mde(
        self,
        baseline_mean: float,
        baseline_std: float,
        sample_size_per_arm: int,
        power: float = 0.8,
        alpha: float = 0.05,
        n_arms: int = 2,
    ) -> PowerAnalysisResult:
        """
        Calculate minimum detectable effect for given sample size and power.

        Args:
            baseline_mean: Expected mean of control group
            baseline_std: Expected standard deviation
            sample_size_per_arm: Available sample size per arm
            power: Desired statistical power
            alpha: Significance level
            n_arms: Number of experiment arms

        Returns:
            PowerAnalysisResult with MDE
        """
        # Critical values
        z_alpha = stats.norm.ppf(1 - alpha / 2)
        z_power = stats.norm.ppf(power)

        # Adjust for multiple comparisons
        if n_arms > 2:
            adjusted_alpha = alpha / (n_arms - 1)
            z_alpha = stats.norm.ppf(1 - adjusted_alpha / 2)

        # Effect size
        effect_size = (z_alpha + z_power) * np.sqrt(2 / sample_size_per_arm)
        absolute_effect = effect_size * baseline_std
        mde = absolute_effect / baseline_mean

        return PowerAnalysisResult(
            power=power,
            sample_size_per_arm=sample_size_per_arm,
            total_sample_size=sample_size_per_arm * n_arms,
            minimum_detectable_effect=mde,
            effect_type="relative",
            alpha=alpha,
            n_arms=n_arms,
            baseline_mean=baseline_mean,
            baseline_std=baseline_std,
        )

    def design_geo_experiment(
        self,
        data: pd.DataFrame,
        geo_col: str,
        outcome_col: str,
        date_col: str,
        mde: float = 0.05,
        power: float = 0.8,
        treatment_duration_days: int = 28,
    ) -> ExperimentDesign:
        """
        Design a geo experiment with optimal assignment.

        Args:
            data: Historical panel data
            geo_col: Column with geo identifiers
            outcome_col: Outcome metric column
            date_col: Date column
            mde: Minimum detectable effect
            power: Desired power
            treatment_duration_days: Duration of treatment

        Returns:
            ExperimentDesign with recommended configuration
        """
        # Analyze geo-level variance
        geo_stats = data.groupby(geo_col)[outcome_col].agg(["mean", "std", "count"]).reset_index()
        geo_stats.columns = ["geo", "mean", "std", "count"]

        # Calculate baseline metrics
        baseline_mean = geo_stats["mean"].mean()
        baseline_std = geo_stats["mean"].std()  # Variance between geos

        # Power analysis
        n_geos = len(geo_stats)
        power_result = self.calculate_power(
            baseline_mean=baseline_mean,
            baseline_std=baseline_std,
            mde=mde,
            sample_size_per_arm=n_geos // 2,
            power=power,
        )

        # Optimal geo assignment using stratification
        geo_stats_sorted = geo_stats.sort_values("mean")
        geos_list = geo_stats_sorted["geo"].tolist()

        # Stratified random assignment
        treatment_geos = []
        control_geos = []
        for i in range(0, len(geos_list), 2):
            pair = geos_list[i:i+2]
            if len(pair) == 2:
                if self._rng.random() < 0.5:
                    treatment_geos.append(pair[0])
                    control_geos.append(pair[1])
                else:
                    treatment_geos.append(pair[1])
                    control_geos.append(pair[0])
            else:
                control_geos.append(pair[0])

        # Calculate recommended duration
        daily_obs_per_geo = data.groupby([geo_col, date_col]).size().groupby(geo_col).mean().mean()

        return ExperimentDesign(
            experiment_type=ExperimentType.GEO_EXPERIMENT,
            treatment_units=treatment_geos,
            control_units=control_geos,
            start_date="",  # To be set
            end_date="",
            warmup_days=7,
            power_analysis=power_result,
            interim_analysis_dates=[],
            stopping_rules={
                "early_stop_for_harm": True,
                "harm_threshold": -0.1,
            },
            primary_metric=outcome_col,
            secondary_metrics=[],
            guardrail_metrics=[],
        )

    def simulate_experiment(
        self,
        baseline_mean: float,
        baseline_std: float,
        true_effect: float,
        sample_size_per_arm: int,
        n_simulations: int = 1000,
        alpha: float = 0.05,
    ) -> dict:
        """
        Simulate experiment outcomes to verify power.

        Args:
            baseline_mean: True baseline mean
            baseline_std: True baseline std
            true_effect: True treatment effect (relative)
            sample_size_per_arm: Sample size per arm
            n_simulations: Number of simulations
            alpha: Significance level

        Returns:
            Simulation results with empirical power
        """
        significant = 0
        effect_estimates = []

        for _ in range(n_simulations):
            # Generate data
            control = self._rng.normal(
                baseline_mean, baseline_std, sample_size_per_arm
            )
            treatment = self._rng.normal(
                baseline_mean * (1 + true_effect), baseline_std, sample_size_per_arm
            )

            # Run t-test
            t_stat, p_value = stats.ttest_ind(treatment, control)

            if p_value < alpha and np.mean(treatment) > np.mean(control):
                significant += 1

            effect_estimates.append(
                (np.mean(treatment) - np.mean(control)) / np.mean(control)
            )

        return {
            "empirical_power": significant / n_simulations,
            "effect_estimates": np.array(effect_estimates),
            "mean_estimated_effect": np.mean(effect_estimates),
            "std_estimated_effect": np.std(effect_estimates),
            "true_effect": true_effect,
            "n_simulations": n_simulations,
        }
