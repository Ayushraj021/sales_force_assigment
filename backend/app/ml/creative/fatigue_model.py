"""
Creative Fatigue Modeling

Models for predicting and measuring creative fatigue in advertising campaigns.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from scipy.stats import pearsonr
import logging

logger = logging.getLogger(__name__)


class FatiguePattern(str, Enum):
    """Types of fatigue patterns."""
    EXPONENTIAL = "exponential"  # Rapid initial decline
    LINEAR = "linear"  # Steady decline
    LOGARITHMIC = "logarithmic"  # Slow start, accelerating decline
    SIGMOID = "sigmoid"  # S-curve with plateau
    STEPWISE = "stepwise"  # Discrete drops


@dataclass
class FatigueConfig:
    """Configuration for fatigue modeling."""
    min_impressions: int = 1000  # Minimum impressions to model
    fatigue_threshold: float = 0.3  # CTR drop threshold for fatigue
    recovery_days: int = 14  # Days for creative recovery
    window_size: int = 7  # Rolling window for smoothing
    confidence_level: float = 0.95


@dataclass
class FatigueCurve:
    """Fitted fatigue curve parameters."""
    pattern: FatiguePattern
    parameters: Dict[str, float]
    r_squared: float
    half_life: Optional[float] = None  # Days to 50% effectiveness
    saturation_point: Optional[int] = None  # Impressions at saturation


@dataclass
class FatigueMetrics:
    """Creative fatigue metrics."""
    creative_id: str
    current_effectiveness: float  # 0-1 scale
    fatigue_level: float  # 0-1 scale (1 = fully fatigued)
    days_active: int
    total_impressions: int
    estimated_remaining_life: Optional[int]  # Days until refresh needed
    fatigue_curve: Optional[FatigueCurve] = None
    confidence_interval: Tuple[float, float] = (0.0, 1.0)
    recommendations: List[str] = field(default_factory=list)


class CreativeFatigueModel:
    """
    Creative Fatigue Modeling System.

    Features:
    - Multiple fatigue curve fitting
    - Effectiveness prediction
    - Refresh timing recommendations
    - Audience segment analysis

    Example:
        model = CreativeFatigueModel()

        # Fit model to historical data
        model.fit(creative_data)

        # Get fatigue metrics
        metrics = model.get_fatigue_metrics("creative_123")

        # Predict future effectiveness
        future = model.predict_effectiveness("creative_123", days_ahead=14)
    """

    def __init__(self, config: Optional[FatigueConfig] = None):
        self.config = config or FatigueConfig()
        self._creative_data: Dict[str, pd.DataFrame] = {}
        self._fitted_curves: Dict[str, FatigueCurve] = {}
        self._baseline_metrics: Dict[str, Dict] = {}

    def fit(
        self,
        data: pd.DataFrame,
        creative_id_col: str = "creative_id",
        date_col: str = "date",
        impressions_col: str = "impressions",
        clicks_col: str = "clicks",
        conversions_col: str = "conversions",
    ) -> Dict[str, FatigueCurve]:
        """
        Fit fatigue models to creative performance data.

        Args:
            data: DataFrame with creative performance data
            creative_id_col: Column name for creative ID
            date_col: Column name for date
            impressions_col: Column name for impressions
            clicks_col: Column name for clicks
            conversions_col: Column name for conversions

        Returns:
            Dict mapping creative IDs to fitted curves
        """
        results = {}

        for creative_id in data[creative_id_col].unique():
            creative_data = data[data[creative_id_col] == creative_id].copy()
            creative_data = creative_data.sort_values(date_col)

            # Calculate daily CTR
            creative_data["ctr"] = (
                creative_data[clicks_col] / creative_data[impressions_col]
            ).replace([np.inf, -np.inf], 0).fillna(0)

            # Calculate daily conversion rate
            creative_data["cvr"] = (
                creative_data[conversions_col] / creative_data[clicks_col]
            ).replace([np.inf, -np.inf], 0).fillna(0)

            # Store data
            self._creative_data[creative_id] = creative_data

            # Calculate baseline (first week average)
            baseline_data = creative_data.head(self.config.window_size)
            self._baseline_metrics[creative_id] = {
                "baseline_ctr": baseline_data["ctr"].mean(),
                "baseline_cvr": baseline_data["cvr"].mean(),
                "start_date": creative_data[date_col].min(),
            }

            # Fit fatigue curve
            if len(creative_data) >= self.config.window_size:
                curve = self._fit_fatigue_curve(creative_data)
                self._fitted_curves[creative_id] = curve
                results[creative_id] = curve

        return results

    def _fit_fatigue_curve(self, data: pd.DataFrame) -> FatigueCurve:
        """Fit the best fatigue curve to the data."""
        # Normalize CTR to effectiveness (0-1 scale)
        max_ctr = data["ctr"].head(self.config.window_size).mean()
        if max_ctr == 0:
            max_ctr = data["ctr"].max() or 1e-6

        effectiveness = (data["ctr"] / max_ctr).clip(0, 1).values
        days = np.arange(len(effectiveness))

        # Try different curve types
        best_fit = None
        best_r2 = -np.inf

        curve_functions = {
            FatiguePattern.EXPONENTIAL: self._exponential_decay,
            FatiguePattern.LINEAR: self._linear_decay,
            FatiguePattern.LOGARITHMIC: self._log_decay,
            FatiguePattern.SIGMOID: self._sigmoid_decay,
        }

        for pattern, func in curve_functions.items():
            try:
                params, r2 = self._fit_curve(func, days, effectiveness)
                if r2 > best_r2:
                    best_r2 = r2
                    best_fit = (pattern, params)
            except Exception as e:
                logger.debug(f"Could not fit {pattern}: {e}")
                continue

        if best_fit is None:
            # Default to linear if nothing fits
            slope = (effectiveness[-1] - effectiveness[0]) / len(effectiveness)
            return FatigueCurve(
                pattern=FatiguePattern.LINEAR,
                parameters={"slope": float(slope), "intercept": float(effectiveness[0])},
                r_squared=0.0,
            )

        pattern, params = best_fit

        # Calculate half-life
        half_life = self._calculate_half_life(pattern, params)

        return FatigueCurve(
            pattern=pattern,
            parameters=params,
            r_squared=best_r2,
            half_life=half_life,
        )

    def _fit_curve(
        self,
        func,
        x: np.ndarray,
        y: np.ndarray,
    ) -> Tuple[Dict[str, float], float]:
        """Fit a curve and return parameters and R-squared."""
        try:
            popt, _ = curve_fit(func, x, y, maxfev=5000)
            y_pred = func(x, *popt)
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

            # Get parameter names from function
            param_names = func.__code__.co_varnames[1:len(popt)+1]
            params = dict(zip(param_names, [float(p) for p in popt]))

            return params, r2
        except Exception:
            raise

    @staticmethod
    def _exponential_decay(x, a, b, c):
        """Exponential decay: y = a * exp(-b * x) + c"""
        return a * np.exp(-b * x) + c

    @staticmethod
    def _linear_decay(x, slope, intercept):
        """Linear decay: y = slope * x + intercept"""
        return slope * x + intercept

    @staticmethod
    def _log_decay(x, a, b, c):
        """Logarithmic decay: y = a - b * log(x + 1) + c"""
        return a - b * np.log(x + 1) + c

    @staticmethod
    def _sigmoid_decay(x, L, k, x0, b):
        """Sigmoid decay: y = L / (1 + exp(k*(x-x0))) + b"""
        return L / (1 + np.exp(k * (x - x0))) + b

    def _calculate_half_life(
        self,
        pattern: FatiguePattern,
        params: Dict[str, float],
    ) -> Optional[float]:
        """Calculate days until 50% effectiveness."""
        try:
            if pattern == FatiguePattern.EXPONENTIAL:
                # a * exp(-b * t) + c = 0.5
                # Solve for t when starting from 1.0
                a, b, c = params.get("a", 1), params.get("b", 0.1), params.get("c", 0)
                if b > 0:
                    return float(np.log(2 * a / (1 - 2 * c)) / b) if (1 - 2*c) > 0 else None

            elif pattern == FatiguePattern.LINEAR:
                slope = params.get("slope", -0.01)
                intercept = params.get("intercept", 1.0)
                if slope < 0:
                    return float((0.5 - intercept) / slope)

            return None
        except Exception:
            return None

    def get_fatigue_metrics(self, creative_id: str) -> FatigueMetrics:
        """
        Get current fatigue metrics for a creative.

        Args:
            creative_id: Creative identifier

        Returns:
            FatigueMetrics with current status
        """
        if creative_id not in self._creative_data:
            raise ValueError(f"Creative {creative_id} not found. Call fit() first.")

        data = self._creative_data[creative_id]
        baseline = self._baseline_metrics[creative_id]
        curve = self._fitted_curves.get(creative_id)

        # Calculate current effectiveness
        recent_ctr = data["ctr"].tail(self.config.window_size).mean()
        baseline_ctr = baseline["baseline_ctr"]

        if baseline_ctr > 0:
            current_effectiveness = min(1.0, recent_ctr / baseline_ctr)
        else:
            current_effectiveness = 0.0

        # Calculate fatigue level (inverse of effectiveness)
        fatigue_level = 1 - current_effectiveness

        # Days active
        days_active = len(data)

        # Total impressions
        total_impressions = int(data["impressions"].sum())

        # Estimate remaining life
        remaining_life = None
        if curve and curve.half_life:
            remaining_life = max(0, int(curve.half_life * 2 - days_active))

        # Generate recommendations
        recommendations = self._generate_recommendations(
            fatigue_level, current_effectiveness, days_active, curve
        )

        # Confidence interval
        ctr_std = data["ctr"].tail(self.config.window_size).std()
        ci_width = 1.96 * (ctr_std / baseline_ctr) if baseline_ctr > 0 else 0.1
        confidence_interval = (
            max(0, current_effectiveness - ci_width),
            min(1, current_effectiveness + ci_width),
        )

        return FatigueMetrics(
            creative_id=creative_id,
            current_effectiveness=float(current_effectiveness),
            fatigue_level=float(fatigue_level),
            days_active=days_active,
            total_impressions=total_impressions,
            estimated_remaining_life=remaining_life,
            fatigue_curve=curve,
            confidence_interval=confidence_interval,
            recommendations=recommendations,
        )

    def _generate_recommendations(
        self,
        fatigue_level: float,
        effectiveness: float,
        days_active: int,
        curve: Optional[FatigueCurve],
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        if fatigue_level > 0.7:
            recommendations.append("CRITICAL: Creative is severely fatigued. Immediate refresh recommended.")
        elif fatigue_level > 0.5:
            recommendations.append("HIGH: Consider refreshing creative within 7 days.")
        elif fatigue_level > 0.3:
            recommendations.append("MODERATE: Monitor closely. Plan refresh in 2-3 weeks.")

        if effectiveness < self.config.fatigue_threshold:
            recommendations.append(
                f"Effectiveness below threshold ({self.config.fatigue_threshold:.0%}). "
                "Consider pausing or refreshing."
            )

        if curve:
            if curve.pattern == FatiguePattern.EXPONENTIAL:
                recommendations.append(
                    "Fast decay pattern detected. Consider shorter creative rotation cycles."
                )
            elif curve.half_life and curve.half_life < 14:
                recommendations.append(
                    f"Short half-life ({curve.half_life:.0f} days). "
                    "Creative may be too similar to previous versions."
                )

        if days_active > 60 and effectiveness > 0.7:
            recommendations.append(
                "Strong longevity. Consider reusing creative elements in future campaigns."
            )

        return recommendations

    def predict_effectiveness(
        self,
        creative_id: str,
        days_ahead: int = 14,
    ) -> pd.DataFrame:
        """
        Predict future effectiveness.

        Args:
            creative_id: Creative identifier
            days_ahead: Days to predict

        Returns:
            DataFrame with predicted effectiveness
        """
        if creative_id not in self._fitted_curves:
            raise ValueError(f"No fitted curve for {creative_id}")

        curve = self._fitted_curves[creative_id]
        current_day = len(self._creative_data[creative_id])

        future_days = np.arange(current_day, current_day + days_ahead)
        predictions = []

        for day in future_days:
            if curve.pattern == FatiguePattern.EXPONENTIAL:
                pred = self._exponential_decay(
                    day,
                    curve.parameters.get("a", 1),
                    curve.parameters.get("b", 0.1),
                    curve.parameters.get("c", 0),
                )
            elif curve.pattern == FatiguePattern.LINEAR:
                pred = self._linear_decay(
                    day,
                    curve.parameters.get("slope", -0.01),
                    curve.parameters.get("intercept", 1),
                )
            elif curve.pattern == FatiguePattern.LOGARITHMIC:
                pred = self._log_decay(
                    day,
                    curve.parameters.get("a", 1),
                    curve.parameters.get("b", 0.1),
                    curve.parameters.get("c", 0),
                )
            else:
                pred = 0.5  # Default

            predictions.append({
                "day": int(day),
                "predicted_effectiveness": max(0, min(1, float(pred))),
                "days_from_now": int(day - current_day),
            })

        return pd.DataFrame(predictions)

    def compare_creatives(
        self,
        creative_ids: List[str],
    ) -> pd.DataFrame:
        """
        Compare fatigue metrics across creatives.

        Args:
            creative_ids: List of creative IDs to compare

        Returns:
            DataFrame with comparison metrics
        """
        comparisons = []

        for cid in creative_ids:
            if cid in self._creative_data:
                metrics = self.get_fatigue_metrics(cid)
                comparisons.append({
                    "creative_id": cid,
                    "current_effectiveness": metrics.current_effectiveness,
                    "fatigue_level": metrics.fatigue_level,
                    "days_active": metrics.days_active,
                    "total_impressions": metrics.total_impressions,
                    "estimated_remaining_life": metrics.estimated_remaining_life,
                    "pattern": metrics.fatigue_curve.pattern.value if metrics.fatigue_curve else None,
                    "r_squared": metrics.fatigue_curve.r_squared if metrics.fatigue_curve else None,
                })

        return pd.DataFrame(comparisons)

    def segment_analysis(
        self,
        data: pd.DataFrame,
        creative_id_col: str = "creative_id",
        segment_col: str = "audience_segment",
        date_col: str = "date",
        impressions_col: str = "impressions",
        clicks_col: str = "clicks",
    ) -> Dict[str, Dict[str, FatigueMetrics]]:
        """
        Analyze fatigue by audience segment.

        Args:
            data: DataFrame with segment-level data
            creative_id_col: Creative ID column
            segment_col: Segment column
            date_col: Date column
            impressions_col: Impressions column
            clicks_col: Clicks column

        Returns:
            Nested dict of creative_id -> segment -> metrics
        """
        results = {}

        for creative_id in data[creative_id_col].unique():
            creative_data = data[data[creative_id_col] == creative_id]
            results[creative_id] = {}

            for segment in creative_data[segment_col].unique():
                segment_data = creative_data[creative_data[segment_col] == segment].copy()

                if len(segment_data) >= self.config.window_size:
                    # Create temporary model for segment
                    segment_model = CreativeFatigueModel(self.config)
                    segment_data[creative_id_col] = f"{creative_id}_{segment}"

                    # Add dummy conversions if not present
                    if "conversions" not in segment_data.columns:
                        segment_data["conversions"] = 0

                    segment_model.fit(
                        segment_data,
                        creative_id_col=creative_id_col,
                        date_col=date_col,
                        impressions_col=impressions_col,
                        clicks_col=clicks_col,
                    )

                    metrics = segment_model.get_fatigue_metrics(f"{creative_id}_{segment}")
                    metrics.creative_id = creative_id  # Reset to original
                    results[creative_id][segment] = metrics

        return results
