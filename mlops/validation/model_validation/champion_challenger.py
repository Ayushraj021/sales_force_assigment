"""
Champion-Challenger model comparison for automated deployment decisions.

Compares a challenger (new) model against the champion (production) model
to determine if the challenger should be promoted.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np


@dataclass
class ModelMetrics:
    """Container for model metrics."""

    model_name: str
    model_version: str
    mape: float
    rmse: float
    mae: float
    r2: float
    latency_p99_ms: float
    training_timestamp: str


@dataclass
class ComparisonThresholds:
    """Thresholds for champion-challenger comparison."""

    # Minimum improvement required (as percentage)
    min_mape_improvement_pct: float = 2.0  # Challenger must be 2% better
    min_rmse_improvement_pct: float = 2.0
    min_r2_improvement_pct: float = 1.0

    # Absolute thresholds (challenger must not exceed)
    max_latency_degradation_pct: float = 10.0  # Can be up to 10% slower

    # Statistical significance
    min_sample_size: int = 100
    confidence_level: float = 0.95


@dataclass
class ComparisonResult:
    """Result of champion-challenger comparison."""

    metric_name: str
    champion_value: float
    challenger_value: float
    improvement_pct: float
    threshold_pct: float
    passed: bool
    message: str


class ChampionChallengerComparator:
    """
    Compares challenger model against champion model.

    Determines if challenger should be promoted based on:
    1. MAPE improvement (primary metric)
    2. RMSE improvement
    3. R2 improvement
    4. Latency not degraded significantly
    """

    def __init__(self, thresholds: ComparisonThresholds | None = None):
        self.thresholds = thresholds or ComparisonThresholds()
        self.comparison_results: list[ComparisonResult] = []

    def compare_mape(
        self,
        champion_mape: float,
        challenger_mape: float,
    ) -> ComparisonResult:
        """Compare MAPE (lower is better)."""
        if champion_mape == 0:
            improvement_pct = 100.0 if challenger_mape < champion_mape else 0.0
        else:
            improvement_pct = ((champion_mape - challenger_mape) / champion_mape) * 100

        passed = improvement_pct >= self.thresholds.min_mape_improvement_pct

        result = ComparisonResult(
            metric_name="MAPE",
            champion_value=champion_mape,
            challenger_value=challenger_mape,
            improvement_pct=round(improvement_pct, 2),
            threshold_pct=self.thresholds.min_mape_improvement_pct,
            passed=passed,
            message=f"MAPE improvement: {improvement_pct:.2f}% (threshold: {self.thresholds.min_mape_improvement_pct}%)",
        )
        self.comparison_results.append(result)
        return result

    def compare_rmse(
        self,
        champion_rmse: float,
        challenger_rmse: float,
    ) -> ComparisonResult:
        """Compare RMSE (lower is better)."""
        if champion_rmse == 0:
            improvement_pct = 100.0 if challenger_rmse < champion_rmse else 0.0
        else:
            improvement_pct = ((champion_rmse - challenger_rmse) / champion_rmse) * 100

        passed = improvement_pct >= self.thresholds.min_rmse_improvement_pct

        result = ComparisonResult(
            metric_name="RMSE",
            champion_value=champion_rmse,
            challenger_value=challenger_rmse,
            improvement_pct=round(improvement_pct, 2),
            threshold_pct=self.thresholds.min_rmse_improvement_pct,
            passed=passed,
            message=f"RMSE improvement: {improvement_pct:.2f}% (threshold: {self.thresholds.min_rmse_improvement_pct}%)",
        )
        self.comparison_results.append(result)
        return result

    def compare_r2(
        self,
        champion_r2: float,
        challenger_r2: float,
    ) -> ComparisonResult:
        """Compare R2 (higher is better)."""
        if champion_r2 == 0:
            improvement_pct = 100.0 if challenger_r2 > champion_r2 else 0.0
        else:
            improvement_pct = ((challenger_r2 - champion_r2) / abs(champion_r2)) * 100

        passed = improvement_pct >= self.thresholds.min_r2_improvement_pct

        result = ComparisonResult(
            metric_name="R2",
            champion_value=champion_r2,
            challenger_value=challenger_r2,
            improvement_pct=round(improvement_pct, 2),
            threshold_pct=self.thresholds.min_r2_improvement_pct,
            passed=passed,
            message=f"R2 improvement: {improvement_pct:.2f}% (threshold: {self.thresholds.min_r2_improvement_pct}%)",
        )
        self.comparison_results.append(result)
        return result

    def compare_latency(
        self,
        champion_latency: float,
        challenger_latency: float,
    ) -> ComparisonResult:
        """Compare latency (lower is better, but small degradation allowed)."""
        if champion_latency == 0:
            degradation_pct = 0.0
        else:
            degradation_pct = ((challenger_latency - champion_latency) / champion_latency) * 100

        # Passed if degradation is within acceptable range (negative = improvement)
        passed = degradation_pct <= self.thresholds.max_latency_degradation_pct

        result = ComparisonResult(
            metric_name="Latency_P99",
            champion_value=champion_latency,
            challenger_value=challenger_latency,
            improvement_pct=round(-degradation_pct, 2),  # Negative degradation = positive improvement
            threshold_pct=-self.thresholds.max_latency_degradation_pct,  # Threshold for max degradation
            passed=passed,
            message=f"Latency change: {degradation_pct:.2f}% (max degradation: {self.thresholds.max_latency_degradation_pct}%)",
        )
        self.comparison_results.append(result)
        return result

    def compare_models(
        self,
        champion: ModelMetrics,
        challenger: ModelMetrics,
    ) -> dict[str, Any]:
        """
        Compare all metrics between champion and challenger.

        Returns comprehensive comparison result with deployment recommendation.
        """
        self.comparison_results = []

        # Run all comparisons
        mape_result = self.compare_mape(champion.mape, challenger.mape)
        rmse_result = self.compare_rmse(champion.rmse, challenger.rmse)
        r2_result = self.compare_r2(champion.r2, challenger.r2)
        latency_result = self.compare_latency(
            champion.latency_p99_ms,
            challenger.latency_p99_ms,
        )

        # Determine overall recommendation
        # Primary: MAPE must improve
        # Secondary: At least 2 of 3 other metrics must pass
        primary_passed = mape_result.passed
        secondary_passed = sum([rmse_result.passed, r2_result.passed, latency_result.passed]) >= 2

        should_promote = primary_passed and secondary_passed

        return {
            "champion": {
                "model_name": champion.model_name,
                "model_version": champion.model_version,
                "metrics": {
                    "mape": champion.mape,
                    "rmse": champion.rmse,
                    "r2": champion.r2,
                    "latency_p99_ms": champion.latency_p99_ms,
                },
            },
            "challenger": {
                "model_name": challenger.model_name,
                "model_version": challenger.model_version,
                "metrics": {
                    "mape": challenger.mape,
                    "rmse": challenger.rmse,
                    "r2": challenger.r2,
                    "latency_p99_ms": challenger.latency_p99_ms,
                },
            },
            "comparisons": [
                {
                    "metric": r.metric_name,
                    "champion": r.champion_value,
                    "challenger": r.challenger_value,
                    "improvement_pct": r.improvement_pct,
                    "threshold_pct": r.threshold_pct,
                    "passed": r.passed,
                    "message": r.message,
                }
                for r in self.comparison_results
            ],
            "summary": {
                "total_comparisons": len(self.comparison_results),
                "passed_comparisons": sum(1 for r in self.comparison_results if r.passed),
                "primary_metric_passed": primary_passed,
                "secondary_metrics_passed": secondary_passed,
            },
            "recommendation": {
                "should_promote": should_promote,
                "confidence": "high" if (primary_passed and sum(r.passed for r in self.comparison_results) >= 3) else "medium" if should_promote else "low",
                "reason": self._get_recommendation_reason(should_promote, primary_passed, secondary_passed),
            },
            "compared_at": datetime.now().isoformat(),
        }

    def _get_recommendation_reason(
        self,
        should_promote: bool,
        primary_passed: bool,
        secondary_passed: bool,
    ) -> str:
        """Generate human-readable recommendation reason."""
        if should_promote:
            return "Challenger model shows significant improvement in primary metric (MAPE) and meets secondary criteria"
        elif not primary_passed:
            return "Challenger model does not show sufficient MAPE improvement"
        else:
            return "Challenger model shows MAPE improvement but fails too many secondary metrics"


def compare_champion_challenger(
    champion_metrics: dict[str, Any],
    challenger_metrics: dict[str, Any],
    thresholds: dict[str, float] | None = None,
) -> dict[str, Any]:
    """
    Compare champion and challenger models.

    Args:
        champion_metrics: Dictionary with champion model metrics
        challenger_metrics: Dictionary with challenger model metrics
        thresholds: Optional custom comparison thresholds

    Returns:
        Comparison result with promotion recommendation
    """
    custom_thresholds = None
    if thresholds:
        custom_thresholds = ComparisonThresholds(
            min_mape_improvement_pct=thresholds.get("min_mape_improvement_pct", 2.0),
            min_rmse_improvement_pct=thresholds.get("min_rmse_improvement_pct", 2.0),
            min_r2_improvement_pct=thresholds.get("min_r2_improvement_pct", 1.0),
            max_latency_degradation_pct=thresholds.get("max_latency_degradation_pct", 10.0),
        )

    champion = ModelMetrics(
        model_name=champion_metrics.get("model_name", "champion"),
        model_version=champion_metrics.get("model_version", "1"),
        mape=champion_metrics.get("mape", 0.0),
        rmse=champion_metrics.get("rmse", 0.0),
        mae=champion_metrics.get("mae", 0.0),
        r2=champion_metrics.get("r2", 0.0),
        latency_p99_ms=champion_metrics.get("latency_p99_ms", 0.0),
        training_timestamp=champion_metrics.get("training_timestamp", ""),
    )

    challenger = ModelMetrics(
        model_name=challenger_metrics.get("model_name", "challenger"),
        model_version=challenger_metrics.get("model_version", "2"),
        mape=challenger_metrics.get("mape", 0.0),
        rmse=challenger_metrics.get("rmse", 0.0),
        mae=challenger_metrics.get("mae", 0.0),
        r2=challenger_metrics.get("r2", 0.0),
        latency_p99_ms=challenger_metrics.get("latency_p99_ms", 0.0),
        training_timestamp=challenger_metrics.get("training_timestamp", ""),
    )

    comparator = ChampionChallengerComparator(custom_thresholds)
    return comparator.compare_models(champion, challenger)
