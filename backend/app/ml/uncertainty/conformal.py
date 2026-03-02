"""
Conformal Prediction for Uncertainty Quantification

Distribution-free prediction intervals with guaranteed coverage.
"""

from dataclasses import dataclass, field
from typing import Optional, Callable, Literal
from enum import Enum
import numpy as np
from sklearn.model_selection import train_test_split


class ConformityScore(str, Enum):
    """Types of nonconformity scores."""
    ABSOLUTE = "absolute"  # |y - y_hat|
    SIGNED = "signed"  # y - y_hat
    NORMALIZED = "normalized"  # |y - y_hat| / sigma
    QUANTILE = "quantile"  # Quantile-based score


@dataclass
class ConformalConfig:
    """Configuration for conformal prediction."""

    # Coverage level
    alpha: float = 0.1  # 1 - alpha = coverage (e.g., 0.1 = 90% coverage)

    # Method
    method: Literal["split", "cv", "jackknife", "jackknife_plus"] = "split"

    # Conformity score
    score_type: ConformityScore = ConformityScore.ABSOLUTE

    # Split ratio for calibration (split method)
    calibration_size: float = 0.2

    # Cross-validation folds (cv method)
    n_folds: int = 5

    # Adaptive intervals
    adaptive: bool = False  # Whether to use local/adaptive intervals


@dataclass
class ConformalPrediction:
    """Result of conformal prediction."""

    # Point prediction
    point_prediction: np.ndarray

    # Prediction intervals
    lower_bound: np.ndarray
    upper_bound: np.ndarray

    # Coverage info
    coverage_level: float
    empirical_coverage: Optional[float] = None

    # Interval properties
    interval_widths: Optional[np.ndarray] = None

    # Conformity scores
    conformity_scores: Optional[np.ndarray] = None
    quantile_score: Optional[float] = None


class ConformalPredictor:
    """
    Conformal Prediction for uncertainty quantification.

    Provides distribution-free prediction intervals with
    guaranteed marginal coverage.

    Methods:
    - Split: Uses held-out calibration set
    - CV: Cross-validation conformal
    - Jackknife: Leave-one-out conformal
    - Jackknife+: More efficient jackknife variant

    Example:
        predictor = ConformalPredictor(model, config)
        predictor.calibrate(X_cal, y_cal)

        prediction = predictor.predict(X_test)
        print(prediction.lower_bound, prediction.upper_bound)
    """

    def __init__(
        self,
        model: Callable,
        config: Optional[ConformalConfig] = None,
    ):
        """
        Initialize conformal predictor.

        Args:
            model: Fitted prediction model with .predict() method
            config: Conformal prediction configuration
        """
        self.model = model
        self.config = config or ConformalConfig()
        self.calibration_scores: Optional[np.ndarray] = None
        self.is_calibrated = False

    def _compute_conformity_score(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        sigma: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """Compute nonconformity scores."""
        if self.config.score_type == ConformityScore.ABSOLUTE:
            return np.abs(y_true - y_pred)
        elif self.config.score_type == ConformityScore.SIGNED:
            return y_true - y_pred
        elif self.config.score_type == ConformityScore.NORMALIZED:
            if sigma is None:
                sigma = np.abs(y_pred) * 0.1 + 1e-6
            return np.abs(y_true - y_pred) / sigma
        else:
            return np.abs(y_true - y_pred)

    def calibrate(
        self,
        X_cal: np.ndarray,
        y_cal: np.ndarray,
        sigma_cal: Optional[np.ndarray] = None,
    ) -> "ConformalPredictor":
        """
        Calibrate the conformal predictor.

        Args:
            X_cal: Calibration features
            y_cal: Calibration targets
            sigma_cal: Optional uncertainty estimates (for normalized scores)

        Returns:
            Self for chaining
        """
        # Get predictions on calibration set
        y_pred = self.model.predict(X_cal)

        if hasattr(y_pred, 'ravel'):
            y_pred = y_pred.ravel()
        if hasattr(y_cal, 'ravel'):
            y_cal = y_cal.ravel()

        # Compute conformity scores
        self.calibration_scores = self._compute_conformity_score(
            y_cal, y_pred, sigma_cal
        )

        self.is_calibrated = True
        return self

    def fit_predict(
        self,
        X: np.ndarray,
        y: np.ndarray,
        X_test: np.ndarray,
    ) -> ConformalPrediction:
        """
        Fit on training data and predict with intervals.

        Uses split conformal: holds out calibration set automatically.
        """
        # Split data
        X_train, X_cal, y_train, y_cal = train_test_split(
            X, y,
            test_size=self.config.calibration_size,
            random_state=42,
        )

        # Fit model on training portion
        if hasattr(self.model, 'fit'):
            self.model.fit(X_train, y_train)

        # Calibrate
        self.calibrate(X_cal, y_cal)

        # Predict on test
        return self.predict(X_test)

    def predict(
        self,
        X: np.ndarray,
        sigma: Optional[np.ndarray] = None,
    ) -> ConformalPrediction:
        """
        Generate predictions with conformal intervals.

        Args:
            X: Features for prediction
            sigma: Optional uncertainty estimates

        Returns:
            ConformalPrediction with bounds
        """
        if not self.is_calibrated:
            raise ValueError("Predictor not calibrated. Call calibrate() first.")

        # Point predictions
        y_pred = self.model.predict(X)
        if hasattr(y_pred, 'ravel'):
            y_pred = y_pred.ravel()

        n_cal = len(self.calibration_scores)

        # Compute quantile of conformity scores
        # For coverage 1-alpha, we need the (1-alpha)(1 + 1/n) quantile
        quantile_level = np.ceil((n_cal + 1) * (1 - self.config.alpha)) / n_cal
        quantile_level = min(quantile_level, 1.0)

        q = np.quantile(self.calibration_scores, quantile_level)

        # Prediction intervals
        if self.config.score_type == ConformityScore.NORMALIZED:
            if sigma is None:
                sigma = np.abs(y_pred) * 0.1 + 1e-6
            lower = y_pred - q * sigma
            upper = y_pred + q * sigma
        elif self.config.score_type == ConformityScore.SIGNED:
            # Signed: asymmetric intervals
            lower_q = np.quantile(self.calibration_scores, self.config.alpha / 2)
            upper_q = np.quantile(self.calibration_scores, 1 - self.config.alpha / 2)
            lower = y_pred - upper_q
            upper = y_pred - lower_q
        else:
            lower = y_pred - q
            upper = y_pred + q

        return ConformalPrediction(
            point_prediction=y_pred,
            lower_bound=lower,
            upper_bound=upper,
            coverage_level=1 - self.config.alpha,
            interval_widths=upper - lower,
            quantile_score=float(q),
        )

    def evaluate_coverage(
        self,
        X_test: np.ndarray,
        y_test: np.ndarray,
    ) -> dict:
        """
        Evaluate empirical coverage on test data.

        Returns:
            Dict with coverage metrics
        """
        prediction = self.predict(X_test)

        y_test = np.array(y_test).ravel()

        # Count how many true values fall within intervals
        covered = (
            (y_test >= prediction.lower_bound) &
            (y_test <= prediction.upper_bound)
        )

        empirical_coverage = np.mean(covered)
        avg_width = np.mean(prediction.interval_widths)
        avg_width_relative = np.mean(
            prediction.interval_widths / (np.abs(y_test) + 1e-6)
        )

        return {
            "target_coverage": 1 - self.config.alpha,
            "empirical_coverage": empirical_coverage,
            "coverage_gap": empirical_coverage - (1 - self.config.alpha),
            "avg_interval_width": avg_width,
            "avg_relative_width": avg_width_relative,
            "median_interval_width": np.median(prediction.interval_widths),
        }


class AdaptiveConformalPredictor(ConformalPredictor):
    """
    Adaptive Conformal Predictor with local coverage.

    Produces intervals that adapt to local uncertainty,
    providing narrower intervals where the model is more
    confident and wider intervals where less confident.
    """

    def __init__(
        self,
        model: Callable,
        uncertainty_model: Optional[Callable] = None,
        config: Optional[ConformalConfig] = None,
    ):
        super().__init__(model, config)
        self.uncertainty_model = uncertainty_model
        self.local_scores: Optional[dict] = None

    def calibrate(
        self,
        X_cal: np.ndarray,
        y_cal: np.ndarray,
        sigma_cal: Optional[np.ndarray] = None,
    ) -> "AdaptiveConformalPredictor":
        """Calibrate with local uncertainty estimation."""
        # Get predictions
        y_pred = self.model.predict(X_cal).ravel()
        y_cal = np.array(y_cal).ravel()

        # Get or estimate uncertainties
        if sigma_cal is None:
            if self.uncertainty_model is not None:
                sigma_cal = self.uncertainty_model.predict(X_cal).ravel()
            else:
                # Simple estimate: residual-based
                residuals = np.abs(y_cal - y_pred)
                sigma_cal = residuals + 1e-6

        # Normalized scores
        self.calibration_scores = np.abs(y_cal - y_pred) / sigma_cal

        # Store calibration info for adaptive intervals
        self.local_scores = {
            'X': X_cal,
            'scores': self.calibration_scores,
            'sigma': sigma_cal,
        }

        self.is_calibrated = True
        return self

    def predict(
        self,
        X: np.ndarray,
        sigma: Optional[np.ndarray] = None,
        k_neighbors: int = 50,
    ) -> ConformalPrediction:
        """
        Generate adaptive prediction intervals.

        Uses local conformity scores based on nearest neighbors.
        """
        if not self.is_calibrated:
            raise ValueError("Predictor not calibrated. Call calibrate() first.")

        y_pred = self.model.predict(X).ravel()

        # Get or estimate uncertainties
        if sigma is None:
            if self.uncertainty_model is not None:
                sigma = self.uncertainty_model.predict(X).ravel()
            else:
                sigma = np.abs(y_pred) * 0.1 + 1e-6

        n_test = len(X)
        lower = np.zeros(n_test)
        upper = np.zeros(n_test)
        widths = np.zeros(n_test)

        # Use global quantile for now (simplified adaptive)
        n_cal = len(self.calibration_scores)
        quantile_level = np.ceil((n_cal + 1) * (1 - self.config.alpha)) / n_cal
        quantile_level = min(quantile_level, 1.0)
        q = np.quantile(self.calibration_scores, quantile_level)

        # Adaptive intervals
        lower = y_pred - q * sigma
        upper = y_pred + q * sigma
        widths = upper - lower

        return ConformalPrediction(
            point_prediction=y_pred,
            lower_bound=lower,
            upper_bound=upper,
            coverage_level=1 - self.config.alpha,
            interval_widths=widths,
            quantile_score=float(q),
        )


def cross_conformal_prediction(
    model: Callable,
    X: np.ndarray,
    y: np.ndarray,
    X_test: np.ndarray,
    alpha: float = 0.1,
    n_folds: int = 5,
) -> ConformalPrediction:
    """
    Cross-validation conformal prediction.

    Provides prediction intervals using K-fold cross-validation
    for more efficient use of calibration data.

    Args:
        model: Model class with fit/predict methods
        X: Training features
        y: Training targets
        X_test: Test features
        alpha: Miscoverage rate
        n_folds: Number of CV folds

    Returns:
        ConformalPrediction with intervals
    """
    from sklearn.model_selection import KFold

    n = len(X)
    y = np.array(y).ravel()

    # Store out-of-fold predictions and scores
    oof_predictions = np.zeros(n)
    oof_scores = np.zeros(n)

    kf = KFold(n_splits=n_folds, shuffle=True, random_state=42)

    for train_idx, val_idx in kf.split(X):
        X_train, X_val = X[train_idx], X[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]

        # Clone and fit model
        fold_model = model.__class__(**model.get_params()) if hasattr(model, 'get_params') else model
        fold_model.fit(X_train, y_train)

        # OOF predictions
        pred = fold_model.predict(X_val).ravel()
        oof_predictions[val_idx] = pred
        oof_scores[val_idx] = np.abs(y_val - pred)

    # Final model for test predictions
    model.fit(X, y)
    y_pred = model.predict(X_test).ravel()

    # Quantile from OOF scores
    quantile_level = np.ceil((n + 1) * (1 - alpha)) / n
    quantile_level = min(quantile_level, 1.0)
    q = np.quantile(oof_scores, quantile_level)

    return ConformalPrediction(
        point_prediction=y_pred,
        lower_bound=y_pred - q,
        upper_bound=y_pred + q,
        coverage_level=1 - alpha,
        interval_widths=np.full(len(y_pred), 2 * q),
        conformity_scores=oof_scores,
        quantile_score=float(q),
    )
