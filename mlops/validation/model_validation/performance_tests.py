"""
Model performance validation tests.

Validates model performance against defined thresholds:
- MAPE (Mean Absolute Percentage Error)
- RMSE (Root Mean Square Error)
- R2 Score
- Inference latency
"""

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class PerformanceThresholds:
    """Performance thresholds for model validation."""

    max_mape: float = 0.15  # Maximum acceptable MAPE (15%)
    max_rmse: float = 5000.0  # Maximum acceptable RMSE
    min_r2: float = 0.80  # Minimum acceptable R2 score
    max_mae: float = 3000.0  # Maximum acceptable MAE
    max_latency_p99_ms: float = 500.0  # Maximum P99 inference latency


@dataclass
class PerformanceResult:
    """Result of a performance test."""

    metric_name: str
    metric_value: float
    threshold: float
    passed: bool
    message: str


class ModelPerformanceValidator:
    """Validates model performance against thresholds."""

    def __init__(self, thresholds: PerformanceThresholds | None = None):
        self.thresholds = thresholds or PerformanceThresholds()
        self.results: list[PerformanceResult] = []

    def validate_mape(self, y_true: np.ndarray, y_pred: np.ndarray) -> PerformanceResult:
        """Validate Mean Absolute Percentage Error."""
        # Avoid division by zero
        mask = y_true != 0
        mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask]))

        passed = mape <= self.thresholds.max_mape
        result = PerformanceResult(
            metric_name="MAPE",
            metric_value=float(mape),
            threshold=self.thresholds.max_mape,
            passed=passed,
            message=f"MAPE: {mape:.4f} {'<=' if passed else '>'} {self.thresholds.max_mape}",
        )
        self.results.append(result)
        return result

    def validate_rmse(self, y_true: np.ndarray, y_pred: np.ndarray) -> PerformanceResult:
        """Validate Root Mean Square Error."""
        rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))

        passed = rmse <= self.thresholds.max_rmse
        result = PerformanceResult(
            metric_name="RMSE",
            metric_value=float(rmse),
            threshold=self.thresholds.max_rmse,
            passed=passed,
            message=f"RMSE: {rmse:.2f} {'<=' if passed else '>'} {self.thresholds.max_rmse}",
        )
        self.results.append(result)
        return result

    def validate_r2(self, y_true: np.ndarray, y_pred: np.ndarray) -> PerformanceResult:
        """Validate R-squared score."""
        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

        passed = r2 >= self.thresholds.min_r2
        result = PerformanceResult(
            metric_name="R2",
            metric_value=float(r2),
            threshold=self.thresholds.min_r2,
            passed=passed,
            message=f"R2: {r2:.4f} {'>=' if passed else '<'} {self.thresholds.min_r2}",
        )
        self.results.append(result)
        return result

    def validate_mae(self, y_true: np.ndarray, y_pred: np.ndarray) -> PerformanceResult:
        """Validate Mean Absolute Error."""
        mae = np.mean(np.abs(y_true - y_pred))

        passed = mae <= self.thresholds.max_mae
        result = PerformanceResult(
            metric_name="MAE",
            metric_value=float(mae),
            threshold=self.thresholds.max_mae,
            passed=passed,
            message=f"MAE: {mae:.2f} {'<=' if passed else '>'} {self.thresholds.max_mae}",
        )
        self.results.append(result)
        return result

    def validate_latency(self, latencies_ms: list[float]) -> PerformanceResult:
        """Validate inference latency (P99)."""
        sorted_latencies = sorted(latencies_ms)
        p99_idx = int(len(sorted_latencies) * 0.99)
        p99_latency = sorted_latencies[min(p99_idx, len(sorted_latencies) - 1)]

        passed = p99_latency <= self.thresholds.max_latency_p99_ms
        result = PerformanceResult(
            metric_name="Latency_P99",
            metric_value=float(p99_latency),
            threshold=self.thresholds.max_latency_p99_ms,
            passed=passed,
            message=f"P99 Latency: {p99_latency:.2f}ms {'<=' if passed else '>'} {self.thresholds.max_latency_p99_ms}ms",
        )
        self.results.append(result)
        return result

    def validate_all(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        latencies_ms: list[float] | None = None,
    ) -> dict[str, Any]:
        """Run all performance validations."""
        self.results = []

        self.validate_mape(y_true, y_pred)
        self.validate_rmse(y_true, y_pred)
        self.validate_r2(y_true, y_pred)
        self.validate_mae(y_true, y_pred)

        if latencies_ms:
            self.validate_latency(latencies_ms)

        all_passed = all(r.passed for r in self.results)

        return {
            "passed": all_passed,
            "results": [
                {
                    "metric": r.metric_name,
                    "value": r.metric_value,
                    "threshold": r.threshold,
                    "passed": r.passed,
                    "message": r.message,
                }
                for r in self.results
            ],
            "summary": {
                "total_tests": len(self.results),
                "passed_tests": sum(1 for r in self.results if r.passed),
                "failed_tests": sum(1 for r in self.results if not r.passed),
            },
        }


def run_performance_tests(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    thresholds: dict[str, float] | None = None,
    latencies_ms: list[float] | None = None,
) -> dict[str, Any]:
    """
    Run performance tests on model predictions.

    Args:
        y_true: Actual values
        y_pred: Predicted values
        thresholds: Optional custom thresholds
        latencies_ms: Optional inference latencies for latency testing

    Returns:
        Dictionary with validation results
    """
    custom_thresholds = None
    if thresholds:
        custom_thresholds = PerformanceThresholds(
            max_mape=thresholds.get("max_mape", 0.15),
            max_rmse=thresholds.get("max_rmse", 5000.0),
            min_r2=thresholds.get("min_r2", 0.80),
            max_mae=thresholds.get("max_mae", 3000.0),
            max_latency_p99_ms=thresholds.get("max_latency_p99_ms", 500.0),
        )

    validator = ModelPerformanceValidator(custom_thresholds)
    return validator.validate_all(y_true, y_pred, latencies_ms)
