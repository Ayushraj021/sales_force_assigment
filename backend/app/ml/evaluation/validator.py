"""
Model Validation

Validation frameworks and cross-validation utilities.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Protocol, Callable
import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class ModelProtocol(Protocol):
    """Protocol for models that can be validated."""

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        ...

    def predict(self, X: np.ndarray) -> np.ndarray:
        ...


@dataclass
class ValidationResult:
    """Result from model validation."""
    is_valid: bool
    metrics: Dict[str, float]
    fold_results: List[Dict[str, float]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "metrics": self.metrics,
            "fold_results": self.fold_results,
            "warnings": self.warnings,
            "errors": self.errors,
            "recommendations": self.recommendations,
        }


class ModelValidator:
    """
    Model Validation Framework.

    Features:
    - Data quality checks
    - Model sanity checks
    - Performance validation
    - Recommendations

    Example:
        validator = ModelValidator()

        # Validate model
        result = validator.validate(model, X_train, y_train, X_test, y_test)

        if not result.is_valid:
            print(result.errors)
    """

    def __init__(
        self,
        min_r2: float = 0.0,
        max_mape: float = 1.0,
        min_samples: int = 30,
    ):
        self.min_r2 = min_r2
        self.max_mape = max_mape
        self.min_samples = min_samples

    def validate(
        self,
        model: Any,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_test: np.ndarray,
        y_test: np.ndarray,
    ) -> ValidationResult:
        """
        Validate a model.

        Args:
            model: Model to validate
            X_train: Training features
            y_train: Training target
            X_test: Test features
            y_test: Test target

        Returns:
            ValidationResult
        """
        warnings = []
        errors = []
        recommendations = []

        # Data checks
        data_issues = self._check_data_quality(X_train, y_train, X_test, y_test)
        warnings.extend(data_issues["warnings"])
        errors.extend(data_issues["errors"])

        if errors:
            return ValidationResult(
                is_valid=False,
                metrics={},
                warnings=warnings,
                errors=errors,
            )

        # Model checks
        try:
            y_pred_train = model.predict(X_train)
            y_pred_test = model.predict(X_test)
        except Exception as e:
            errors.append(f"Model prediction failed: {e}")
            return ValidationResult(
                is_valid=False,
                metrics={},
                warnings=warnings,
                errors=errors,
            )

        # Calculate metrics
        from .metrics import calculate_metrics

        train_metrics = calculate_metrics(y_train, y_pred_train, metric_type="regression")
        test_metrics = calculate_metrics(y_test, y_pred_test, metric_type="regression")

        metrics = {
            "train_r2": train_metrics.r2,
            "test_r2": test_metrics.r2,
            "train_rmse": train_metrics.rmse,
            "test_rmse": test_metrics.rmse,
            "train_mae": train_metrics.mae,
            "test_mae": test_metrics.mae,
            "train_mape": train_metrics.mape or 0,
            "test_mape": test_metrics.mape or 0,
        }

        # Performance checks
        if test_metrics.r2 < self.min_r2:
            warnings.append(f"Test R² ({test_metrics.r2:.3f}) below threshold ({self.min_r2})")
            recommendations.append("Consider feature engineering or model tuning")

        if test_metrics.mape and test_metrics.mape > self.max_mape:
            warnings.append(f"Test MAPE ({test_metrics.mape:.2%}) above threshold ({self.max_mape:.2%})")

        # Overfitting check
        if train_metrics.r2 - test_metrics.r2 > 0.1:
            warnings.append("Potential overfitting detected (train-test R² gap > 0.1)")
            recommendations.append("Consider regularization or reducing model complexity")

        # Underfitting check
        if train_metrics.r2 < 0.5 and test_metrics.r2 < 0.5:
            warnings.append("Potential underfitting (both train and test R² < 0.5)")
            recommendations.append("Consider adding features or using more complex model")

        is_valid = len(errors) == 0 and test_metrics.r2 >= self.min_r2

        return ValidationResult(
            is_valid=is_valid,
            metrics=metrics,
            warnings=warnings,
            errors=errors,
            recommendations=recommendations,
        )

    def _check_data_quality(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_test: np.ndarray,
        y_test: np.ndarray,
    ) -> Dict[str, List[str]]:
        """Check data quality."""
        warnings = []
        errors = []

        # Sample size
        if len(X_train) < self.min_samples:
            errors.append(f"Training set too small ({len(X_train)} < {self.min_samples})")

        if len(X_test) < 10:
            warnings.append("Test set is very small (<10 samples)")

        # Missing values
        if np.isnan(X_train).any():
            warnings.append("Training features contain NaN values")

        if np.isnan(y_train).any():
            errors.append("Training target contains NaN values")

        if np.isnan(X_test).any():
            warnings.append("Test features contain NaN values")

        # Constant features
        if X_train.ndim == 2:
            constant_cols = np.where(X_train.std(axis=0) == 0)[0]
            if len(constant_cols) > 0:
                warnings.append(f"{len(constant_cols)} constant feature(s) detected")

        # Target variance
        if np.var(y_train) < 1e-10:
            errors.append("Target variable has near-zero variance")

        # Distribution shift
        if X_train.ndim == 2 and X_test.ndim == 2:
            train_means = X_train.mean(axis=0)
            test_means = X_test.mean(axis=0)
            train_stds = X_train.std(axis=0) + 1e-10
            shift = np.abs(train_means - test_means) / train_stds
            if np.any(shift > 2):
                warnings.append("Potential distribution shift between train and test")

        return {"warnings": warnings, "errors": errors}


class CrossValidator:
    """
    Cross-Validation Framework.

    Features:
    - Time series cross-validation
    - K-fold cross-validation
    - Expanding window
    - Sliding window

    Example:
        cv = CrossValidator(method="time_series", n_splits=5)

        results = cv.cross_validate(model, X, y)
    """

    def __init__(
        self,
        method: str = "kfold",  # kfold, time_series, expanding, sliding
        n_splits: int = 5,
        gap: int = 0,
        min_train_size: Optional[int] = None,
        max_train_size: Optional[int] = None,
    ):
        self.method = method
        self.n_splits = n_splits
        self.gap = gap
        self.min_train_size = min_train_size
        self.max_train_size = max_train_size

    def cross_validate(
        self,
        model: Any,
        X: np.ndarray,
        y: np.ndarray,
        metric_fn: Optional[Callable] = None,
    ) -> ValidationResult:
        """
        Perform cross-validation.

        Args:
            model: Model to validate
            X: Features
            y: Target
            metric_fn: Optional custom metric function

        Returns:
            ValidationResult with fold metrics
        """
        from .metrics import calculate_metrics

        fold_results = []
        all_predictions = []
        all_actuals = []

        splits = list(self._get_splits(X, y))

        for fold_idx, (train_idx, test_idx) in enumerate(splits):
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]

            try:
                # Clone model if possible
                if hasattr(model, "clone"):
                    fold_model = model.clone()
                elif hasattr(model, "__class__"):
                    fold_model = model.__class__()
                else:
                    fold_model = model

                # Fit and predict
                fold_model.fit(X_train, y_train)
                y_pred = fold_model.predict(X_test)

                # Calculate metrics
                if metric_fn:
                    fold_metrics = metric_fn(y_test, y_pred)
                else:
                    metrics_obj = calculate_metrics(y_test, y_pred, metric_type="regression")
                    fold_metrics = {
                        "r2": metrics_obj.r2,
                        "rmse": metrics_obj.rmse,
                        "mae": metrics_obj.mae,
                    }

                fold_metrics["fold"] = fold_idx + 1
                fold_results.append(fold_metrics)

                all_predictions.extend(y_pred.flatten())
                all_actuals.extend(y_test.flatten())

            except Exception as e:
                logger.warning(f"Fold {fold_idx + 1} failed: {e}")
                fold_results.append({
                    "fold": fold_idx + 1,
                    "error": str(e),
                })

        # Aggregate metrics
        valid_folds = [f for f in fold_results if "error" not in f]
        if not valid_folds:
            return ValidationResult(
                is_valid=False,
                metrics={},
                fold_results=fold_results,
                errors=["All folds failed"],
            )

        aggregated_metrics = {}
        for key in valid_folds[0].keys():
            if key != "fold" and isinstance(valid_folds[0][key], (int, float)):
                values = [f[key] for f in valid_folds]
                aggregated_metrics[f"mean_{key}"] = float(np.mean(values))
                aggregated_metrics[f"std_{key}"] = float(np.std(values))

        # Overall metrics
        if all_predictions and all_actuals:
            overall = calculate_metrics(
                np.array(all_actuals),
                np.array(all_predictions),
                metric_type="regression"
            )
            aggregated_metrics["overall_r2"] = overall.r2
            aggregated_metrics["overall_rmse"] = overall.rmse

        return ValidationResult(
            is_valid=True,
            metrics=aggregated_metrics,
            fold_results=fold_results,
        )

    def _get_splits(self, X: np.ndarray, y: np.ndarray):
        """Generate train/test split indices."""
        n_samples = len(X)

        if self.method == "kfold":
            fold_size = n_samples // self.n_splits
            indices = np.arange(n_samples)
            np.random.shuffle(indices)

            for i in range(self.n_splits):
                test_start = i * fold_size
                test_end = (i + 1) * fold_size if i < self.n_splits - 1 else n_samples
                test_idx = indices[test_start:test_end]
                train_idx = np.concatenate([indices[:test_start], indices[test_end:]])
                yield train_idx, test_idx

        elif self.method == "time_series":
            # Time series split (expanding window)
            min_train = self.min_train_size or n_samples // (self.n_splits + 1)

            for i in range(self.n_splits):
                train_end = min_train + i * ((n_samples - min_train) // self.n_splits)
                test_start = train_end + self.gap
                test_end = test_start + (n_samples - min_train) // self.n_splits

                if test_end > n_samples:
                    test_end = n_samples

                train_idx = np.arange(0, train_end)
                test_idx = np.arange(test_start, test_end)

                if len(test_idx) > 0:
                    yield train_idx, test_idx

        elif self.method == "sliding":
            # Sliding window
            window_size = self.min_train_size or n_samples // 2
            step = (n_samples - window_size) // self.n_splits

            for i in range(self.n_splits):
                train_start = i * step
                train_end = train_start + window_size
                test_start = train_end + self.gap
                test_end = test_start + step

                if test_end > n_samples:
                    test_end = n_samples

                train_idx = np.arange(train_start, train_end)
                test_idx = np.arange(test_start, test_end)

                if len(test_idx) > 0:
                    yield train_idx, test_idx
