"""
Model Evaluation Metrics

Comprehensive metrics for model evaluation.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union
import numpy as np
import logging

logger = logging.getLogger(__name__)


@dataclass
class ForecastMetrics:
    """Metrics for forecast evaluation."""
    mape: float  # Mean Absolute Percentage Error
    rmse: float  # Root Mean Square Error
    mae: float  # Mean Absolute Error
    mse: float  # Mean Square Error
    smape: float  # Symmetric MAPE
    mase: float  # Mean Absolute Scaled Error
    r2: float  # R-squared
    bias: float  # Mean error (bias)
    coverage_50: float  # 50% prediction interval coverage
    coverage_95: float  # 95% prediction interval coverage
    winkler_score: Optional[float] = None  # Winkler score for intervals
    pinball_loss: Optional[Dict[float, float]] = None  # Pinball loss by quantile

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mape": self.mape,
            "rmse": self.rmse,
            "mae": self.mae,
            "mse": self.mse,
            "smape": self.smape,
            "mase": self.mase,
            "r2": self.r2,
            "bias": self.bias,
            "coverage_50": self.coverage_50,
            "coverage_95": self.coverage_95,
            "winkler_score": self.winkler_score,
        }

    @property
    def summary(self) -> str:
        return f"MAPE: {self.mape:.2%}, RMSE: {self.rmse:.2f}, R²: {self.r2:.3f}"


@dataclass
class RegressionMetrics:
    """Metrics for regression models."""
    mse: float
    rmse: float
    mae: float
    r2: float
    adjusted_r2: float
    mape: Optional[float] = None
    explained_variance: float = 0.0
    max_error: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {
            "mse": self.mse,
            "rmse": self.rmse,
            "mae": self.mae,
            "r2": self.r2,
            "adjusted_r2": self.adjusted_r2,
            "mape": self.mape,
            "explained_variance": self.explained_variance,
            "max_error": self.max_error,
        }


@dataclass
class ClassificationMetrics:
    """Metrics for classification models."""
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    auc_roc: Optional[float] = None
    auc_pr: Optional[float] = None
    log_loss: Optional[float] = None
    confusion_matrix: Optional[np.ndarray] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "accuracy": self.accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "auc_roc": self.auc_roc,
            "auc_pr": self.auc_pr,
            "log_loss": self.log_loss,
        }


def calculate_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_train: Optional[np.ndarray] = None,
    lower: Optional[np.ndarray] = None,
    upper: Optional[np.ndarray] = None,
    metric_type: str = "forecast",
    n_features: int = 1,
) -> Union[ForecastMetrics, RegressionMetrics]:
    """
    Calculate comprehensive metrics.

    Args:
        y_true: True values
        y_pred: Predicted values
        y_train: Training data (for MASE)
        lower: Lower prediction interval
        upper: Upper prediction interval
        metric_type: "forecast" or "regression"
        n_features: Number of features (for adjusted R²)

    Returns:
        Metrics object
    """
    y_true = np.asarray(y_true).flatten()
    y_pred = np.asarray(y_pred).flatten()

    # Basic metrics
    errors = y_true - y_pred
    abs_errors = np.abs(errors)
    squared_errors = errors ** 2

    mse = float(np.mean(squared_errors))
    rmse = float(np.sqrt(mse))
    mae = float(np.mean(abs_errors))

    # R-squared
    ss_res = np.sum(squared_errors)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    r2 = float(1 - ss_res / ss_tot) if ss_tot > 0 else 0.0

    # MAPE (handle zeros)
    non_zero_mask = y_true != 0
    if np.any(non_zero_mask):
        mape = float(np.mean(np.abs(errors[non_zero_mask] / y_true[non_zero_mask])))
    else:
        mape = np.inf

    if metric_type == "regression":
        # Adjusted R²
        n = len(y_true)
        adjusted_r2 = 1 - (1 - r2) * (n - 1) / (n - n_features - 1) if n > n_features + 1 else r2

        # Explained variance
        explained_variance = float(1 - np.var(errors) / np.var(y_true)) if np.var(y_true) > 0 else 0.0

        return RegressionMetrics(
            mse=mse,
            rmse=rmse,
            mae=mae,
            r2=r2,
            adjusted_r2=adjusted_r2,
            mape=mape if mape != np.inf else None,
            explained_variance=explained_variance,
            max_error=float(np.max(abs_errors)),
        )

    # Forecast-specific metrics
    # SMAPE
    smape = float(np.mean(2 * abs_errors / (np.abs(y_true) + np.abs(y_pred) + 1e-10)))

    # MASE (requires training data)
    if y_train is not None and len(y_train) > 1:
        naive_errors = np.abs(np.diff(y_train))
        scale = np.mean(naive_errors)
        mase = float(mae / scale) if scale > 0 else np.inf
    else:
        mase = np.inf

    # Bias
    bias = float(np.mean(errors))

    # Coverage (if intervals provided)
    coverage_50 = 0.0
    coverage_95 = 0.0
    winkler_score = None

    if lower is not None and upper is not None:
        lower = np.asarray(lower).flatten()
        upper = np.asarray(upper).flatten()

        # 95% coverage (assume provided intervals are 95%)
        in_interval = (y_true >= lower) & (y_true <= upper)
        coverage_95 = float(np.mean(in_interval))

        # Estimate 50% coverage (narrower interval)
        interval_width = upper - lower
        lower_50 = y_pred - interval_width * 0.25
        upper_50 = y_pred + interval_width * 0.25
        in_interval_50 = (y_true >= lower_50) & (y_true <= upper_50)
        coverage_50 = float(np.mean(in_interval_50))

        # Winkler score
        alpha = 0.05
        penalty = 2 / alpha
        winkler = interval_width.copy()
        winkler[y_true < lower] += penalty * (lower[y_true < lower] - y_true[y_true < lower])
        winkler[y_true > upper] += penalty * (y_true[y_true > upper] - upper[y_true > upper])
        winkler_score = float(np.mean(winkler))

    return ForecastMetrics(
        mape=mape,
        rmse=rmse,
        mae=mae,
        mse=mse,
        smape=smape,
        mase=mase if mase != np.inf else 1.0,
        r2=r2,
        bias=bias,
        coverage_50=coverage_50,
        coverage_95=coverage_95,
        winkler_score=winkler_score,
    )


def calculate_pinball_loss(
    y_true: np.ndarray,
    y_pred_quantiles: Dict[float, np.ndarray],
) -> Dict[float, float]:
    """
    Calculate pinball loss for quantile predictions.

    Args:
        y_true: True values
        y_pred_quantiles: Dict mapping quantile to predictions

    Returns:
        Dict mapping quantile to pinball loss
    """
    y_true = np.asarray(y_true).flatten()
    losses = {}

    for q, y_pred in y_pred_quantiles.items():
        y_pred = np.asarray(y_pred).flatten()
        errors = y_true - y_pred
        losses[q] = float(np.mean(np.where(errors >= 0, q * errors, (q - 1) * errors)))

    return losses


def calculate_skill_score(
    metric_value: float,
    baseline_value: float,
    perfect_value: float = 0.0,
) -> float:
    """
    Calculate skill score relative to baseline.

    Args:
        metric_value: Model's metric value
        baseline_value: Baseline model's metric value
        perfect_value: Perfect score value

    Returns:
        Skill score (0 = baseline, 1 = perfect)
    """
    if baseline_value == perfect_value:
        return 0.0

    return (baseline_value - metric_value) / (baseline_value - perfect_value)


def forecast_horizon_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    horizon: int,
) -> List[Dict[str, float]]:
    """
    Calculate metrics for each forecast horizon.

    Args:
        y_true: True values (2D: samples x horizons)
        y_pred: Predicted values (2D: samples x horizons)
        horizon: Maximum horizon

    Returns:
        List of metrics per horizon
    """
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)

    if y_true.ndim == 1:
        y_true = y_true.reshape(-1, horizon)
        y_pred = y_pred.reshape(-1, horizon)

    results = []
    for h in range(min(horizon, y_true.shape[1])):
        metrics = calculate_metrics(y_true[:, h], y_pred[:, h], metric_type="forecast")
        results.append({
            "horizon": h + 1,
            "mape": metrics.mape,
            "rmse": metrics.rmse,
            "mae": metrics.mae,
        })

    return results
