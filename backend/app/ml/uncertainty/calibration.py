"""
Probability Calibration for Uncertainty Estimation

Ensures that predicted probabilities match observed frequencies.
"""

from dataclasses import dataclass, field
from typing import Optional, Literal, Callable, List
import numpy as np
from scipy import optimize
from scipy.special import expit, logit


@dataclass
class CalibrationConfig:
    """Configuration for probability calibration."""

    method: Literal[
        "platt", "isotonic", "beta", "temperature", "histogram"
    ] = "isotonic"

    # Histogram binning
    n_bins: int = 10

    # Beta calibration parameters
    beta_regularization: float = 0.0

    # Validation
    cv_folds: int = 5


@dataclass
class CalibrationMetrics:
    """Calibration quality metrics."""

    # Expected Calibration Error
    ece: float

    # Maximum Calibration Error
    mce: float

    # Brier score (for probability predictions)
    brier_score: Optional[float] = None

    # Log loss
    log_loss: Optional[float] = None

    # Reliability diagram data
    bin_accuracies: Optional[np.ndarray] = None
    bin_confidences: Optional[np.ndarray] = None
    bin_counts: Optional[np.ndarray] = None


@dataclass
class CalibrationResult:
    """Result of calibration."""

    # Calibrated probabilities/values
    calibrated: np.ndarray

    # Original values
    original: np.ndarray

    # Calibration metrics
    before_metrics: CalibrationMetrics
    after_metrics: CalibrationMetrics

    # Improvement
    ece_improvement: float

    # Fitted calibrator info
    calibrator_type: str
    calibrator_params: dict = field(default_factory=dict)


class ProbabilityCalibrator:
    """
    Probability Calibration for well-calibrated uncertainty.

    Transforms raw model outputs (logits or probabilities) into
    calibrated probabilities that better reflect true frequencies.

    Methods:
    - Platt Scaling: Logistic regression recalibration
    - Isotonic Regression: Non-parametric monotonic calibration
    - Temperature Scaling: Simple temperature parameter
    - Beta Calibration: Flexible beta distribution calibration
    - Histogram Binning: Binwise frequency calibration

    Example:
        calibrator = ProbabilityCalibrator()
        calibrator.fit(val_probs, val_labels)

        calibrated_probs = calibrator.calibrate(test_probs)
    """

    def __init__(self, config: Optional[CalibrationConfig] = None):
        self.config = config or CalibrationConfig()
        self.is_fitted = False
        self.calibration_fn: Optional[Callable] = None
        self.params: dict = {}

    def fit(
        self,
        probabilities: np.ndarray,
        labels: np.ndarray,
    ) -> "ProbabilityCalibrator":
        """
        Fit the calibrator on validation data.

        Args:
            probabilities: Predicted probabilities or logits
            labels: True binary labels (0 or 1)

        Returns:
            Self for chaining
        """
        probabilities = np.array(probabilities).ravel()
        labels = np.array(labels).ravel()

        method = self.config.method

        if method == "platt":
            self._fit_platt(probabilities, labels)
        elif method == "isotonic":
            self._fit_isotonic(probabilities, labels)
        elif method == "beta":
            self._fit_beta(probabilities, labels)
        elif method == "temperature":
            self._fit_temperature(probabilities, labels)
        elif method == "histogram":
            self._fit_histogram(probabilities, labels)
        else:
            raise ValueError(f"Unknown calibration method: {method}")

        self.is_fitted = True
        return self

    def calibrate(self, probabilities: np.ndarray) -> np.ndarray:
        """
        Apply calibration to new probabilities.

        Args:
            probabilities: Raw probabilities to calibrate

        Returns:
            Calibrated probabilities
        """
        if not self.is_fitted:
            raise ValueError("Calibrator not fitted. Call fit() first.")

        probabilities = np.array(probabilities).ravel()
        return self.calibration_fn(probabilities)

    def fit_calibrate(
        self,
        probabilities: np.ndarray,
        labels: np.ndarray,
        test_probabilities: np.ndarray,
    ) -> CalibrationResult:
        """
        Fit on validation data and calibrate test data.

        Returns full calibration result with metrics.
        """
        # Compute before metrics
        before_metrics = self.compute_metrics(probabilities, labels)

        # Fit calibrator
        self.fit(probabilities, labels)

        # Calibrate
        calibrated = self.calibrate(test_probabilities)

        # Compute after metrics (if labels available)
        after_metrics = before_metrics  # Placeholder if no test labels

        return CalibrationResult(
            calibrated=calibrated,
            original=test_probabilities,
            before_metrics=before_metrics,
            after_metrics=after_metrics,
            ece_improvement=0.0,  # Computed when test labels available
            calibrator_type=self.config.method,
            calibrator_params=self.params,
        )

    def _fit_platt(
        self,
        probabilities: np.ndarray,
        labels: np.ndarray,
    ) -> None:
        """Fit Platt scaling (logistic regression)."""
        # Avoid extreme values
        probs_clipped = np.clip(probabilities, 1e-6, 1 - 1e-6)

        # Convert to logits
        logits = logit(probs_clipped)

        # Fit logistic regression: sigmoid(a * logit + b)
        def loss(params):
            a, b = params
            calibrated_logits = a * logits + b
            calibrated_probs = expit(calibrated_logits)
            # Cross-entropy loss
            eps = 1e-10
            return -np.mean(
                labels * np.log(calibrated_probs + eps) +
                (1 - labels) * np.log(1 - calibrated_probs + eps)
            )

        result = optimize.minimize(loss, x0=[1.0, 0.0], method='L-BFGS-B')
        a, b = result.x

        self.params = {'a': a, 'b': b}
        self.calibration_fn = lambda p: expit(
            a * logit(np.clip(p, 1e-6, 1 - 1e-6)) + b
        )

    def _fit_isotonic(
        self,
        probabilities: np.ndarray,
        labels: np.ndarray,
    ) -> None:
        """Fit isotonic regression."""
        from sklearn.isotonic import IsotonicRegression

        iso = IsotonicRegression(out_of_bounds='clip')
        iso.fit(probabilities, labels)

        self.params = {'isotonic_model': iso}
        self.calibration_fn = lambda p: iso.predict(np.clip(p, 0, 1))

    def _fit_beta(
        self,
        probabilities: np.ndarray,
        labels: np.ndarray,
    ) -> None:
        """Fit beta calibration."""
        # Beta calibration: calibrated = 1 / (1 + 1/(exp(a)*p^b*(1-p)^c))
        probs_clipped = np.clip(probabilities, 1e-6, 1 - 1e-6)

        def loss(params):
            a, b, c = params
            calibrated = 1.0 / (
                1.0 + 1.0 / (np.exp(a) * np.power(probs_clipped, b) *
                             np.power(1 - probs_clipped, c))
            )
            eps = 1e-10
            return -np.mean(
                labels * np.log(calibrated + eps) +
                (1 - labels) * np.log(1 - calibrated + eps)
            ) + self.config.beta_regularization * (a**2 + b**2 + c**2)

        result = optimize.minimize(
            loss,
            x0=[0.0, 1.0, 1.0],
            method='L-BFGS-B',
            bounds=[(-10, 10), (0.01, 10), (0.01, 10)],
        )
        a, b, c = result.x

        self.params = {'a': a, 'b': b, 'c': c}

        def beta_calibrate(p):
            p_clip = np.clip(p, 1e-6, 1 - 1e-6)
            return 1.0 / (
                1.0 + 1.0 / (np.exp(a) * np.power(p_clip, b) *
                             np.power(1 - p_clip, c))
            )

        self.calibration_fn = beta_calibrate

    def _fit_temperature(
        self,
        probabilities: np.ndarray,
        labels: np.ndarray,
    ) -> None:
        """Fit temperature scaling."""
        probs_clipped = np.clip(probabilities, 1e-6, 1 - 1e-6)
        logits = logit(probs_clipped)

        def loss(T):
            T = max(T, 1e-6)
            scaled_logits = logits / T
            calibrated_probs = expit(scaled_logits)
            eps = 1e-10
            return -np.mean(
                labels * np.log(calibrated_probs + eps) +
                (1 - labels) * np.log(1 - calibrated_probs + eps)
            )

        result = optimize.minimize_scalar(
            loss,
            bounds=(0.1, 10.0),
            method='bounded',
        )
        T = result.x

        self.params = {'temperature': T}
        self.calibration_fn = lambda p: expit(
            logit(np.clip(p, 1e-6, 1 - 1e-6)) / T
        )

    def _fit_histogram(
        self,
        probabilities: np.ndarray,
        labels: np.ndarray,
    ) -> None:
        """Fit histogram binning."""
        n_bins = self.config.n_bins

        # Create uniform bins
        bins = np.linspace(0, 1, n_bins + 1)
        bin_indices = np.digitize(probabilities, bins) - 1
        bin_indices = np.clip(bin_indices, 0, n_bins - 1)

        # Compute bin calibration values
        bin_calibration = np.zeros(n_bins)
        for i in range(n_bins):
            mask = bin_indices == i
            if mask.sum() > 0:
                bin_calibration[i] = labels[mask].mean()
            else:
                # Empty bin: use bin center
                bin_calibration[i] = (bins[i] + bins[i + 1]) / 2

        self.params = {
            'bins': bins,
            'bin_calibration': bin_calibration,
        }

        def histogram_calibrate(p):
            p_clipped = np.clip(p, 0, 1)
            indices = np.digitize(p_clipped, bins) - 1
            indices = np.clip(indices, 0, n_bins - 1)
            return bin_calibration[indices]

        self.calibration_fn = histogram_calibrate

    def compute_metrics(
        self,
        probabilities: np.ndarray,
        labels: np.ndarray,
    ) -> CalibrationMetrics:
        """
        Compute calibration metrics.

        Args:
            probabilities: Predicted probabilities
            labels: True binary labels

        Returns:
            CalibrationMetrics
        """
        probabilities = np.array(probabilities).ravel()
        labels = np.array(labels).ravel()

        n = len(probabilities)
        n_bins = self.config.n_bins

        # Create bins
        bins = np.linspace(0, 1, n_bins + 1)
        bin_indices = np.digitize(probabilities, bins) - 1
        bin_indices = np.clip(bin_indices, 0, n_bins - 1)

        # Compute per-bin metrics
        bin_accuracies = np.zeros(n_bins)
        bin_confidences = np.zeros(n_bins)
        bin_counts = np.zeros(n_bins)

        for i in range(n_bins):
            mask = bin_indices == i
            count = mask.sum()
            bin_counts[i] = count

            if count > 0:
                bin_accuracies[i] = labels[mask].mean()
                bin_confidences[i] = probabilities[mask].mean()

        # ECE: Expected Calibration Error
        ece = np.sum(
            bin_counts * np.abs(bin_accuracies - bin_confidences)
        ) / n

        # MCE: Maximum Calibration Error
        valid_bins = bin_counts > 0
        if valid_bins.any():
            mce = np.max(np.abs(bin_accuracies[valid_bins] - bin_confidences[valid_bins]))
        else:
            mce = 0.0

        # Brier score
        brier = np.mean((probabilities - labels) ** 2)

        # Log loss
        eps = 1e-10
        log_loss = -np.mean(
            labels * np.log(probabilities + eps) +
            (1 - labels) * np.log(1 - probabilities + eps)
        )

        return CalibrationMetrics(
            ece=ece,
            mce=mce,
            brier_score=brier,
            log_loss=log_loss,
            bin_accuracies=bin_accuracies,
            bin_confidences=bin_confidences,
            bin_counts=bin_counts,
        )

    def reliability_diagram_data(
        self,
        probabilities: np.ndarray,
        labels: np.ndarray,
    ) -> dict:
        """
        Get data for plotting a reliability diagram.

        Returns dict with bin centers, accuracies, and gaps.
        """
        metrics = self.compute_metrics(probabilities, labels)
        bins = np.linspace(0, 1, self.config.n_bins + 1)
        bin_centers = (bins[:-1] + bins[1:]) / 2

        return {
            'bin_centers': bin_centers,
            'accuracies': metrics.bin_accuracies,
            'confidences': metrics.bin_confidences,
            'counts': metrics.bin_counts,
            'gaps': metrics.bin_accuracies - metrics.bin_confidences,
            'ece': metrics.ece,
            'mce': metrics.mce,
        }


def calibrate_regression_uncertainty(
    predictions: np.ndarray,
    uncertainties: np.ndarray,
    actuals: np.ndarray,
    method: Literal["scale", "optimize"] = "scale",
) -> np.ndarray:
    """
    Calibrate regression uncertainty estimates.

    Adjusts uncertainty estimates so that they reflect
    true prediction error distribution.

    Args:
        predictions: Point predictions
        uncertainties: Predicted standard deviations
        actuals: True values
        method: Calibration method

    Returns:
        Calibrated uncertainty estimates
    """
    residuals = actuals - predictions
    standardized_residuals = residuals / (uncertainties + 1e-6)

    if method == "scale":
        # Scale uncertainties by empirical std of standardized residuals
        scale = np.std(standardized_residuals)
        return uncertainties * scale

    else:  # optimize
        # Optimize scale factor for negative log likelihood
        def nll(scale):
            scaled_sigma = uncertainties * scale
            return 0.5 * np.mean(
                np.log(2 * np.pi * scaled_sigma**2) +
                (residuals**2) / (scaled_sigma**2)
            )

        result = optimize.minimize_scalar(nll, bounds=(0.1, 10.0), method='bounded')
        return uncertainties * result.x
