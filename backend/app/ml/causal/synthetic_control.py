"""
Synthetic Control Methods

Implements synthetic control method (SCM) for causal inference
in observational studies with aggregate data.

References:
- Abadie, Diamond, Hainmueller (2010): Synthetic Control Methods
- Abadie, Diamond, Hainmueller (2015): Comparative Politics and SCM
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import minimize
from sklearn.preprocessing import StandardScaler


@dataclass
class SyntheticControlResult:
    """Result from synthetic control analysis."""

    # Treatment effect estimates
    att: float  # Average Treatment effect on the Treated
    cumulative_effect: float

    # Time series
    treated_actual: np.ndarray
    synthetic_control: np.ndarray
    treatment_effect: np.ndarray
    time_index: np.ndarray

    # Weights and fit
    unit_weights: dict[str, float]
    covariate_weights: dict[str, float]

    # Pre-treatment diagnostics
    pre_treatment_rmspe: float
    pre_treatment_r2: float

    # Inference
    p_value: float
    placebo_effects: Optional[np.ndarray] = None

    # Metadata
    treated_unit: str
    treatment_period: int


class SyntheticControlAnalyzer:
    """
    Synthetic Control Method analyzer.

    Constructs a synthetic control unit as a weighted combination
    of untreated units that best approximates the treated unit
    in the pre-treatment period.

    Example:
        analyzer = SyntheticControlAnalyzer()
        result = analyzer.fit(
            data=df,
            treated_unit="California",
            treatment_period=2000,
            outcome_col="gdp",
            unit_col="state",
            time_col="year"
        )
    """

    def __init__(
        self,
        regularization: float = 0.01,
        n_placebo: int = 100,
        seed: Optional[int] = None,
    ):
        self.regularization = regularization
        self.n_placebo = n_placebo
        self.seed = seed
        self._rng = np.random.default_rng(seed)

    def fit(
        self,
        data: pd.DataFrame,
        treated_unit: str,
        treatment_period: int,
        outcome_col: str,
        unit_col: str,
        time_col: str,
        covariate_cols: Optional[list[str]] = None,
        donor_units: Optional[list[str]] = None,
    ) -> SyntheticControlResult:
        """
        Fit synthetic control model.

        Args:
            data: Panel data with units, time, and outcomes
            treated_unit: Identifier of the treated unit
            treatment_period: Time period when treatment starts
            outcome_col: Name of outcome variable column
            unit_col: Name of unit identifier column
            time_col: Name of time period column
            covariate_cols: Optional list of covariate columns
            donor_units: Optional list of donor pool units

        Returns:
            SyntheticControlResult with estimated effects
        """
        # Validate and prepare data
        self._validate_data(data, outcome_col, unit_col, time_col)

        # Get donor pool
        all_units = data[unit_col].unique()
        if donor_units is None:
            donor_units = [u for u in all_units if u != treated_unit]

        # Split by treatment period
        pre_data = data[data[time_col] < treatment_period]
        post_data = data[data[time_col] >= treatment_period]

        # Pivot to wide format
        pre_wide = data.pivot_table(
            index=time_col,
            columns=unit_col,
            values=outcome_col,
        ).fillna(0)

        # Get treated and donor series
        Y_treated_pre = pre_wide[treated_unit].values
        X_donors_pre = pre_wide[donor_units].values

        # Find optimal weights
        weights = self._find_weights(Y_treated_pre, X_donors_pre, donor_units)

        # Calculate synthetic control for full period
        full_wide = data.pivot_table(
            index=time_col,
            columns=unit_col,
            values=outcome_col,
        ).fillna(0)

        time_index = full_wide.index.values
        treated_actual = full_wide[treated_unit].values
        synthetic_control = full_wide[donor_units].values @ np.array(
            [weights[u] for u in donor_units]
        )
        treatment_effect = treated_actual - synthetic_control

        # Pre-treatment fit diagnostics
        pre_mask = time_index < treatment_period
        pre_rmspe = np.sqrt(np.mean((treated_actual[pre_mask] - synthetic_control[pre_mask]) ** 2))
        pre_r2 = 1 - np.sum((treated_actual[pre_mask] - synthetic_control[pre_mask]) ** 2) / \
                 np.sum((treated_actual[pre_mask] - np.mean(treated_actual[pre_mask])) ** 2)

        # Post-treatment effects
        post_mask = time_index >= treatment_period
        att = np.mean(treatment_effect[post_mask])
        cumulative_effect = np.sum(treatment_effect[post_mask])

        # Placebo inference
        p_value, placebo_effects = self._placebo_inference(
            full_wide, donor_units, treatment_period, weights, att
        )

        return SyntheticControlResult(
            att=att,
            cumulative_effect=cumulative_effect,
            treated_actual=treated_actual,
            synthetic_control=synthetic_control,
            treatment_effect=treatment_effect,
            time_index=time_index,
            unit_weights=weights,
            covariate_weights={},  # Simplified - no covariate matching
            pre_treatment_rmspe=pre_rmspe,
            pre_treatment_r2=pre_r2,
            p_value=p_value,
            placebo_effects=placebo_effects,
            treated_unit=treated_unit,
            treatment_period=treatment_period,
        )

    def _validate_data(
        self,
        data: pd.DataFrame,
        outcome_col: str,
        unit_col: str,
        time_col: str,
    ) -> None:
        """Validate input data."""
        required = [outcome_col, unit_col, time_col]
        missing = [c for c in required if c not in data.columns]
        if missing:
            raise ValueError(f"Missing columns: {missing}")

    def _find_weights(
        self,
        Y_treated: np.ndarray,
        X_donors: np.ndarray,
        donor_units: list[str],
    ) -> dict[str, float]:
        """
        Find optimal weights for synthetic control.

        Solves: min_w ||Y_treated - X_donors @ w||^2 + lambda * ||w||^2
        s.t. sum(w) = 1, w >= 0
        """
        n_donors = len(donor_units)

        # Standardize for optimization
        scaler = StandardScaler()
        Y_scaled = scaler.fit_transform(Y_treated.reshape(-1, 1)).flatten()
        X_scaled = StandardScaler().fit_transform(X_donors)

        def objective(w):
            pred = X_scaled @ w
            mse = np.mean((Y_scaled - pred) ** 2)
            reg = self.regularization * np.sum(w ** 2)
            return mse + reg

        # Constraints
        constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
        bounds = [(0, 1) for _ in range(n_donors)]

        # Initial weights
        w0 = np.ones(n_donors) / n_donors

        result = minimize(objective, w0, bounds=bounds, constraints=constraints)

        return dict(zip(donor_units, result.x))

    def _placebo_inference(
        self,
        full_wide: pd.DataFrame,
        donor_units: list[str],
        treatment_period: int,
        actual_weights: dict[str, float],
        actual_att: float,
    ) -> tuple[float, np.ndarray]:
        """
        Placebo-based inference.

        Runs synthetic control on each donor unit as if it were treated,
        calculates distribution of placebo effects.
        """
        time_index = full_wide.index.values
        placebo_effects = []

        for placebo_unit in donor_units:
            # Other donors as control
            control_units = [u for u in donor_units if u != placebo_unit]
            if len(control_units) < 2:
                continue

            # Pre-treatment period
            pre_mask = time_index < treatment_period
            Y_placebo_pre = full_wide.loc[pre_mask, placebo_unit].values
            X_control_pre = full_wide.loc[pre_mask, control_units].values

            # Find placebo weights
            try:
                placebo_weights = self._find_weights(
                    Y_placebo_pre, X_control_pre, control_units
                )
            except Exception:
                continue

            # Calculate placebo effect
            post_mask = time_index >= treatment_period
            Y_placebo_post = full_wide.loc[post_mask, placebo_unit].values
            Y_synth_post = full_wide.loc[post_mask, control_units].values @ \
                          np.array([placebo_weights[u] for u in control_units])

            placebo_att = np.mean(Y_placebo_post - Y_synth_post)
            placebo_effects.append(placebo_att)

        placebo_effects = np.array(placebo_effects)

        # Calculate p-value
        if len(placebo_effects) > 0:
            p_value = np.mean(np.abs(placebo_effects) >= np.abs(actual_att))
        else:
            p_value = 1.0

        return p_value, placebo_effects

    def plot_results(self, result: SyntheticControlResult) -> dict:
        """
        Generate plot data for visualization.

        Returns dict with data for:
        - Time series of treated vs synthetic
        - Treatment effect over time
        - Gap plot
        """
        treatment_idx = np.searchsorted(result.time_index, result.treatment_period)

        return {
            "time_series": {
                "time": result.time_index.tolist(),
                "treated": result.treated_actual.tolist(),
                "synthetic": result.synthetic_control.tolist(),
                "treatment_period": result.treatment_period,
            },
            "treatment_effect": {
                "time": result.time_index.tolist(),
                "effect": result.treatment_effect.tolist(),
                "treatment_period": result.treatment_period,
            },
            "weights": result.unit_weights,
            "diagnostics": {
                "pre_rmspe": result.pre_treatment_rmspe,
                "pre_r2": result.pre_treatment_r2,
                "att": result.att,
                "cumulative_effect": result.cumulative_effect,
                "p_value": result.p_value,
            },
        }
