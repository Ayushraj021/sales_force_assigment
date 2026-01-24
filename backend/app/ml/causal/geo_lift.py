"""
GeoLift Testing Module

Implements Meta's GeoLift methodology for measuring incrementality
of marketing campaigns using geographic experiments.

Reference: https://github.com/facebookincubator/GeoLift
"""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Optional

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.preprocessing import StandardScaler


class GeoLiftStatus(str, Enum):
    """Status of a GeoLift experiment."""

    DESIGN = "design"
    RUNNING = "running"
    COMPLETED = "completed"
    ANALYZED = "analyzed"


@dataclass
class GeoLiftResult:
    """Result from GeoLift analysis."""

    # Lift estimates
    absolute_lift: float
    relative_lift: float

    # Confidence intervals
    lift_ci_lower: float
    lift_ci_upper: float

    # Statistical measures
    p_value: float
    standard_error: float

    # Counterfactual predictions
    counterfactual: np.ndarray
    actual: np.ndarray

    # Test vs control comparison
    test_regions: list[str]
    control_regions: list[str]

    # Synthetic control weights
    synthetic_weights: dict[str, float]

    # Diagnostics
    pre_treatment_fit: float  # MAPE or R-squared
    balance_score: float

    # Metadata
    treatment_start: date
    treatment_end: date
    confidence_level: float = 0.95


@dataclass
class GeoLiftConfig:
    """Configuration for GeoLift analysis."""

    # Column names
    date_col: str = "date"
    geo_col: str = "geo"
    outcome_col: str = "outcome"

    # Analysis settings
    confidence_level: float = 0.95
    n_bootstrap: int = 1000

    # Pre-treatment validation
    min_pre_treatment_periods: int = 14
    max_pre_treatment_mape: float = 0.15

    # Synthetic control settings
    regularization: float = 0.01

    # Optional covariates
    covariate_cols: list[str] = field(default_factory=list)


class GeoLiftAnalyzer:
    """
    GeoLift Analyzer for measuring marketing incrementality.

    Uses synthetic control methodology to estimate the causal effect
    of marketing interventions in geographic regions.

    Example:
        analyzer = GeoLiftAnalyzer(config)
        result = analyzer.analyze(
            data=df,
            test_regions=["CA", "NY"],
            treatment_start=date(2024, 1, 1),
            treatment_end=date(2024, 1, 31)
        )
    """

    def __init__(self, config: Optional[GeoLiftConfig] = None):
        self.config = config or GeoLiftConfig()
        self._scaler = StandardScaler()

    def analyze(
        self,
        data: pd.DataFrame,
        test_regions: list[str],
        treatment_start: date,
        treatment_end: date,
        control_regions: Optional[list[str]] = None,
    ) -> GeoLiftResult:
        """
        Analyze the lift from a geo experiment.

        Args:
            data: Panel data with date, geo, and outcome columns
            test_regions: List of treatment region identifiers
            treatment_start: Start date of the treatment
            treatment_end: End date of the treatment
            control_regions: Optional list of control regions (inferred if not provided)

        Returns:
            GeoLiftResult with lift estimates and diagnostics
        """
        # Validate inputs
        self._validate_data(data)

        # Infer control regions if not provided
        all_geos = data[self.config.geo_col].unique()
        if control_regions is None:
            control_regions = [g for g in all_geos if g not in test_regions]

        # Split data into pre and post treatment
        data[self.config.date_col] = pd.to_datetime(data[self.config.date_col])
        treatment_start_dt = pd.to_datetime(treatment_start)
        treatment_end_dt = pd.to_datetime(treatment_end)

        pre_data = data[data[self.config.date_col] < treatment_start_dt]
        post_data = data[
            (data[self.config.date_col] >= treatment_start_dt) &
            (data[self.config.date_col] <= treatment_end_dt)
        ]

        # Pivot to wide format for synthetic control
        pre_wide = self._pivot_data(pre_data)
        post_wide = self._pivot_data(post_data)

        # Build synthetic control
        weights, pre_fit = self._build_synthetic_control(
            pre_wide, test_regions, control_regions
        )

        # Calculate counterfactual and lift
        counterfactual = self._calculate_counterfactual(
            post_wide, control_regions, weights
        )
        actual = post_wide[test_regions].sum(axis=1).values

        # Calculate lift metrics
        lift_results = self._calculate_lift(actual, counterfactual)

        # Bootstrap confidence intervals
        ci_lower, ci_upper = self._bootstrap_confidence_intervals(
            post_wide, test_regions, control_regions, weights
        )

        return GeoLiftResult(
            absolute_lift=lift_results["absolute_lift"],
            relative_lift=lift_results["relative_lift"],
            lift_ci_lower=ci_lower,
            lift_ci_upper=ci_upper,
            p_value=lift_results["p_value"],
            standard_error=lift_results["standard_error"],
            counterfactual=counterfactual,
            actual=actual,
            test_regions=test_regions,
            control_regions=control_regions,
            synthetic_weights=weights,
            pre_treatment_fit=pre_fit,
            balance_score=self._calculate_balance_score(pre_wide, test_regions, weights),
            treatment_start=treatment_start,
            treatment_end=treatment_end,
            confidence_level=self.config.confidence_level,
        )

    def design_experiment(
        self,
        data: pd.DataFrame,
        budget: float,
        min_detectable_lift: float = 0.05,
        treatment_duration_days: int = 28,
    ) -> dict[str, Any]:
        """
        Design an optimal geo experiment.

        Args:
            data: Historical panel data
            budget: Available budget for treatment
            min_detectable_lift: Minimum lift to detect (as proportion)
            treatment_duration_days: Duration of treatment period

        Returns:
            Recommended experiment design including regions and power
        """
        # Analyze historical variance by geo
        geo_stats = self._analyze_geo_variance(data)

        # Rank geos by statistical power contribution
        geos_ranked = self._rank_geos_for_experiment(
            geo_stats, budget, min_detectable_lift
        )

        # Calculate power for different test/control splits
        designs = []
        for n_test in range(1, len(geos_ranked) // 2 + 1):
            test_geos = geos_ranked[:n_test]
            control_geos = geos_ranked[n_test:]

            power = self._estimate_power(
                data, test_geos, control_geos, min_detectable_lift
            )

            designs.append({
                "test_regions": test_geos,
                "control_regions": control_geos,
                "power": power,
                "n_test": n_test,
                "n_control": len(control_geos),
            })

        # Select design with sufficient power
        recommended = max(designs, key=lambda x: x["power"])

        return {
            "recommended_design": recommended,
            "all_designs": designs,
            "geo_statistics": geo_stats,
            "minimum_detectable_lift": min_detectable_lift,
            "treatment_duration_days": treatment_duration_days,
        }

    def _validate_data(self, data: pd.DataFrame) -> None:
        """Validate input data has required columns."""
        required = [
            self.config.date_col,
            self.config.geo_col,
            self.config.outcome_col,
        ]
        missing = [c for c in required if c not in data.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

    def _pivot_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Pivot long data to wide format (dates x geos)."""
        return data.pivot_table(
            index=self.config.date_col,
            columns=self.config.geo_col,
            values=self.config.outcome_col,
            aggfunc="sum",
        ).fillna(0)

    def _build_synthetic_control(
        self,
        pre_wide: pd.DataFrame,
        test_regions: list[str],
        control_regions: list[str],
    ) -> tuple[dict[str, float], float]:
        """
        Build synthetic control weights using convex optimization.

        Finds weights w such that sum(w_i * control_i) approximates treatment.
        """
        # Aggregate test regions
        Y_test = pre_wide[test_regions].sum(axis=1).values

        # Control region matrix
        X_control = pre_wide[control_regions].values

        # Standardize
        Y_test_scaled = self._scaler.fit_transform(Y_test.reshape(-1, 1)).flatten()
        X_control_scaled = StandardScaler().fit_transform(X_control)

        # Solve for weights using constrained optimization
        # Simplified: use OLS with L2 regularization and project to simplex
        from scipy.optimize import minimize

        def objective(w):
            pred = X_control_scaled @ w
            mse = np.mean((Y_test_scaled - pred) ** 2)
            reg = self.config.regularization * np.sum(w ** 2)
            return mse + reg

        # Constraints: weights sum to 1, all non-negative
        constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1},
        ]
        bounds = [(0, 1) for _ in control_regions]

        # Initial weights: uniform
        w0 = np.ones(len(control_regions)) / len(control_regions)

        result = minimize(objective, w0, bounds=bounds, constraints=constraints)
        weights = dict(zip(control_regions, result.x))

        # Calculate pre-treatment fit
        pred_pre = X_control @ result.x
        mape = np.mean(np.abs(Y_test - pred_pre) / (Y_test + 1e-8))
        pre_fit = 1 - mape  # Convert to R2-like measure

        return weights, pre_fit

    def _calculate_counterfactual(
        self,
        post_wide: pd.DataFrame,
        control_regions: list[str],
        weights: dict[str, float],
    ) -> np.ndarray:
        """Calculate counterfactual using synthetic control weights."""
        X_control = post_wide[control_regions].values
        w = np.array([weights[g] for g in control_regions])
        return X_control @ w

    def _calculate_lift(
        self, actual: np.ndarray, counterfactual: np.ndarray
    ) -> dict[str, float]:
        """Calculate lift metrics."""
        absolute_lift = np.sum(actual - counterfactual)
        relative_lift = absolute_lift / np.sum(counterfactual)

        # T-test for significance
        diff = actual - counterfactual
        t_stat, p_value = stats.ttest_1samp(diff, 0)
        standard_error = np.std(diff) / np.sqrt(len(diff))

        return {
            "absolute_lift": absolute_lift,
            "relative_lift": relative_lift,
            "p_value": p_value,
            "standard_error": standard_error,
        }

    def _bootstrap_confidence_intervals(
        self,
        post_wide: pd.DataFrame,
        test_regions: list[str],
        control_regions: list[str],
        weights: dict[str, float],
    ) -> tuple[float, float]:
        """Calculate bootstrap confidence intervals for lift."""
        lifts = []
        n = len(post_wide)

        for _ in range(self.config.n_bootstrap):
            # Resample with replacement
            idx = np.random.choice(n, size=n, replace=True)
            actual_boot = post_wide.iloc[idx][test_regions].sum(axis=1).values

            X_control = post_wide.iloc[idx][control_regions].values
            w = np.array([weights[g] for g in control_regions])
            counterfactual_boot = X_control @ w

            lift = np.sum(actual_boot - counterfactual_boot)
            lifts.append(lift)

        alpha = 1 - self.config.confidence_level
        ci_lower = np.percentile(lifts, alpha / 2 * 100)
        ci_upper = np.percentile(lifts, (1 - alpha / 2) * 100)

        return ci_lower, ci_upper

    def _calculate_balance_score(
        self,
        pre_wide: pd.DataFrame,
        test_regions: list[str],
        weights: dict[str, float],
    ) -> float:
        """Calculate how well synthetic control balances pre-treatment."""
        Y_test = pre_wide[test_regions].sum(axis=1).values
        control_regions = list(weights.keys())
        X_control = pre_wide[control_regions].values
        w = np.array([weights[g] for g in control_regions])
        Y_synth = X_control @ w

        # Correlation as balance measure
        return float(np.corrcoef(Y_test, Y_synth)[0, 1])

    def _analyze_geo_variance(self, data: pd.DataFrame) -> pd.DataFrame:
        """Analyze variance characteristics of each geo."""
        stats_list = []
        for geo in data[self.config.geo_col].unique():
            geo_data = data[data[self.config.geo_col] == geo][self.config.outcome_col]
            stats_list.append({
                "geo": geo,
                "mean": geo_data.mean(),
                "std": geo_data.std(),
                "cv": geo_data.std() / geo_data.mean() if geo_data.mean() > 0 else float("inf"),
                "n_obs": len(geo_data),
            })
        return pd.DataFrame(stats_list)

    def _rank_geos_for_experiment(
        self,
        geo_stats: pd.DataFrame,
        budget: float,
        min_lift: float,
    ) -> list[str]:
        """Rank geos by suitability for experiment."""
        # Prefer geos with lower CV (more stable) and higher mean (more signal)
        geo_stats = geo_stats.copy()
        geo_stats["score"] = geo_stats["mean"] / (geo_stats["cv"] + 0.1)
        return geo_stats.sort_values("score", ascending=False)["geo"].tolist()

    def _estimate_power(
        self,
        data: pd.DataFrame,
        test_geos: list[str],
        control_geos: list[str],
        min_lift: float,
    ) -> float:
        """Estimate statistical power for given design."""
        # Simplified power calculation based on effect size and variance
        test_data = data[data[self.config.geo_col].isin(test_geos)][self.config.outcome_col]
        control_data = data[data[self.config.geo_col].isin(control_geos)][self.config.outcome_col]

        pooled_std = np.sqrt((test_data.var() + control_data.var()) / 2)
        effect_size = min_lift * test_data.mean() / pooled_std

        # Power from effect size (approximation)
        # Using normal approximation for two-sample t-test
        n_test = len(test_data)
        n_control = len(control_data)

        se = pooled_std * np.sqrt(1/n_test + 1/n_control)
        z_alpha = stats.norm.ppf(0.975)  # Two-tailed 5% significance
        z_beta = (min_lift * test_data.mean() - z_alpha * se) / se

        power = stats.norm.cdf(z_beta)
        return max(0, min(1, power))
