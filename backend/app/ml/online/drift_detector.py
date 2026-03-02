"""
Drift Detection

Detect concept drift and data drift in streaming data.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
import numpy as np
from datetime import datetime
import logging
from collections import deque

logger = logging.getLogger(__name__)


class DriftType(str, Enum):
    """Types of drift."""
    SUDDEN = "sudden"  # Abrupt change
    GRADUAL = "gradual"  # Slow transition
    INCREMENTAL = "incremental"  # Small continuous changes
    RECURRING = "recurring"  # Periodic patterns


class DriftStatus(str, Enum):
    """Drift detection status."""
    NO_DRIFT = "no_drift"
    WARNING = "warning"
    DRIFT = "drift"


@dataclass
class DriftResult:
    """Result of drift detection."""
    timestamp: datetime
    status: DriftStatus
    drift_type: Optional[DriftType]
    p_value: Optional[float]
    statistic: float
    threshold: float
    feature_drifts: Dict[str, float] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DriftConfig:
    """Configuration for drift detection."""
    # Detection method
    method: str = "ks"  # ks, psi, adwin, ddm, eddm

    # Thresholds
    warning_threshold: float = 0.05
    drift_threshold: float = 0.01

    # Window settings
    reference_window: int = 1000
    test_window: int = 500

    # PSI specific
    psi_threshold: float = 0.2
    n_bins: int = 10

    # ADWIN specific
    adwin_delta: float = 0.002

    # Feature drift
    detect_feature_drift: bool = True


class DriftDetector:
    """
    Drift Detection for Streaming Data.

    Features:
    - Multiple detection methods (KS, PSI, ADWIN, DDM, EDDM)
    - Concept drift and data drift detection
    - Per-feature drift analysis
    - Warning and drift levels

    Example:
        detector = DriftDetector(config)
        detector.fit(reference_data)

        for batch in stream:
            result = detector.detect(batch)
            if result.status == DriftStatus.DRIFT:
                print("Drift detected!")
                retrain_model()
    """

    def __init__(self, config: Optional[DriftConfig] = None):
        self.config = config or DriftConfig()

        # Reference data statistics
        self._reference_data: Optional[np.ndarray] = None
        self._reference_stats: Dict[str, Any] = {}

        # Streaming data buffer
        self._buffer: deque = deque(maxlen=self.config.test_window)

        # Detection history
        self._detection_history: List[DriftResult] = []

        # ADWIN-specific state
        self._adwin_windows: Dict[int, List[float]] = {}

        # DDM-specific state
        self._ddm_min_error = float('inf')
        self._ddm_min_std = float('inf')
        self._ddm_n_samples = 0

    def fit(self, reference_data: np.ndarray) -> "DriftDetector":
        """
        Fit detector with reference data.

        Args:
            reference_data: Reference data to compare against

        Returns:
            self
        """
        self._reference_data = np.atleast_2d(reference_data)
        self._reference_stats = self._compute_stats(self._reference_data)

        # Initialize ADWIN windows
        n_features = self._reference_data.shape[1]
        for i in range(n_features):
            self._adwin_windows[i] = list(self._reference_data[:, i])

        return self

    def detect(
        self,
        data: np.ndarray,
        y_pred: Optional[np.ndarray] = None,
        y_true: Optional[np.ndarray] = None,
    ) -> DriftResult:
        """
        Detect drift in new data.

        Args:
            data: New data to check for drift
            y_pred: Optional predictions (for concept drift)
            y_true: Optional ground truth (for concept drift)

        Returns:
            DriftResult with drift status and details
        """
        data = np.atleast_2d(data)

        # Add to buffer
        for row in data:
            self._buffer.append(row)

        if len(self._buffer) < self.config.test_window // 2:
            return DriftResult(
                timestamp=datetime.now(),
                status=DriftStatus.NO_DRIFT,
                drift_type=None,
                p_value=None,
                statistic=0.0,
                threshold=self.config.drift_threshold,
            )

        # Perform detection based on method
        test_data = np.array(list(self._buffer))

        if self.config.method == "ks":
            result = self._ks_test(test_data)
        elif self.config.method == "psi":
            result = self._psi_test(test_data)
        elif self.config.method == "adwin":
            result = self._adwin_test(test_data)
        elif self.config.method == "ddm":
            if y_pred is not None and y_true is not None:
                result = self._ddm_test(y_pred, y_true)
            else:
                result = self._ks_test(test_data)
        else:
            result = self._ks_test(test_data)

        # Detect per-feature drift
        if self.config.detect_feature_drift:
            result.feature_drifts = self._detect_feature_drift(test_data)

        self._detection_history.append(result)

        return result

    def _compute_stats(self, data: np.ndarray) -> Dict[str, Any]:
        """Compute statistics for reference data."""
        return {
            "mean": np.mean(data, axis=0),
            "std": np.std(data, axis=0) + 1e-6,
            "min": np.min(data, axis=0),
            "max": np.max(data, axis=0),
            "quantiles": np.percentile(data, [25, 50, 75], axis=0),
        }

    def _ks_test(self, test_data: np.ndarray) -> DriftResult:
        """Kolmogorov-Smirnov test for distribution shift."""
        from scipy import stats

        if self._reference_data is None:
            raise ValueError("Detector not fitted")

        # Test each feature
        p_values = []
        statistics = []

        for i in range(test_data.shape[1]):
            ref_col = self._reference_data[:, i]
            test_col = test_data[:, i]

            stat, p_value = stats.ks_2samp(ref_col, test_col)
            p_values.append(p_value)
            statistics.append(stat)

        # Use minimum p-value (most significant drift)
        min_p = min(p_values)
        max_stat = max(statistics)

        # Determine status
        if min_p < self.config.drift_threshold:
            status = DriftStatus.DRIFT
            drift_type = DriftType.SUDDEN
        elif min_p < self.config.warning_threshold:
            status = DriftStatus.WARNING
            drift_type = DriftType.GRADUAL
        else:
            status = DriftStatus.NO_DRIFT
            drift_type = None

        return DriftResult(
            timestamp=datetime.now(),
            status=status,
            drift_type=drift_type,
            p_value=min_p,
            statistic=max_stat,
            threshold=self.config.drift_threshold,
            details={"p_values": p_values, "statistics": statistics},
        )

    def _psi_test(self, test_data: np.ndarray) -> DriftResult:
        """Population Stability Index test."""
        if self._reference_data is None:
            raise ValueError("Detector not fitted")

        psi_values = []

        for i in range(test_data.shape[1]):
            ref_col = self._reference_data[:, i]
            test_col = test_data[:, i]

            psi = self._calculate_psi(ref_col, test_col)
            psi_values.append(psi)

        max_psi = max(psi_values)

        if max_psi > self.config.psi_threshold:
            status = DriftStatus.DRIFT
            drift_type = DriftType.SUDDEN
        elif max_psi > self.config.psi_threshold * 0.5:
            status = DriftStatus.WARNING
            drift_type = DriftType.GRADUAL
        else:
            status = DriftStatus.NO_DRIFT
            drift_type = None

        return DriftResult(
            timestamp=datetime.now(),
            status=status,
            drift_type=drift_type,
            p_value=None,
            statistic=max_psi,
            threshold=self.config.psi_threshold,
            details={"psi_values": psi_values},
        )

    def _calculate_psi(
        self,
        reference: np.ndarray,
        test: np.ndarray,
    ) -> float:
        """Calculate PSI between two distributions."""
        # Create bins from reference
        min_val = min(reference.min(), test.min())
        max_val = max(reference.max(), test.max())
        bins = np.linspace(min_val, max_val, self.config.n_bins + 1)

        # Calculate proportions
        ref_hist, _ = np.histogram(reference, bins=bins)
        test_hist, _ = np.histogram(test, bins=bins)

        ref_prop = ref_hist / len(reference) + 1e-10
        test_prop = test_hist / len(test) + 1e-10

        # Calculate PSI
        psi = np.sum((test_prop - ref_prop) * np.log(test_prop / ref_prop))

        return float(psi)

    def _adwin_test(self, test_data: np.ndarray) -> DriftResult:
        """ADWIN (ADaptive WINdowing) test."""
        drift_detected = False
        drift_features = []

        for i in range(test_data.shape[1]):
            # Add new data to window
            self._adwin_windows[i].extend(test_data[:, i].tolist())

            # Check for drift using ADWIN logic
            if self._adwin_check(i):
                drift_detected = True
                drift_features.append(i)

        if drift_detected:
            status = DriftStatus.DRIFT
            drift_type = DriftType.SUDDEN
        else:
            status = DriftStatus.NO_DRIFT
            drift_type = None

        return DriftResult(
            timestamp=datetime.now(),
            status=status,
            drift_type=drift_type,
            p_value=None,
            statistic=len(drift_features),
            threshold=1.0,
            details={"drift_features": drift_features},
        )

    def _adwin_check(self, feature_idx: int) -> bool:
        """Check ADWIN condition for a feature."""
        window = self._adwin_windows[feature_idx]
        n = len(window)

        if n < 10:
            return False

        # Check all possible splits
        for i in range(5, n - 5):
            w1 = window[:i]
            w2 = window[i:]

            mean1 = np.mean(w1)
            mean2 = np.mean(w2)

            # ADWIN threshold
            m = 1.0 / len(w1) + 1.0 / len(w2)
            delta = self.config.adwin_delta
            epsilon = np.sqrt(2 * m * np.log(2.0 / delta))

            if abs(mean1 - mean2) > epsilon:
                # Drift detected, shrink window
                self._adwin_windows[feature_idx] = window[i:]
                return True

        return False

    def _ddm_test(
        self,
        y_pred: np.ndarray,
        y_true: np.ndarray,
    ) -> DriftResult:
        """DDM (Drift Detection Method) for concept drift."""
        # Calculate error rate
        errors = (y_pred != y_true).astype(float)

        for error in errors:
            self._ddm_n_samples += 1
            error_rate = error  # Binary error for this sample

            # Update running statistics
            if self._ddm_n_samples == 1:
                self._ddm_min_error = error_rate
                self._ddm_min_std = 0.0
            else:
                # Standard deviation estimate
                std_error = np.sqrt(error_rate * (1 - error_rate) / self._ddm_n_samples)

                if error_rate + std_error <= self._ddm_min_error + self._ddm_min_std:
                    self._ddm_min_error = error_rate
                    self._ddm_min_std = std_error

        # Current statistics
        current_error = np.mean(errors)
        current_std = np.std(errors)

        # DDM thresholds
        warning_level = self._ddm_min_error + 2 * self._ddm_min_std
        drift_level = self._ddm_min_error + 3 * self._ddm_min_std

        if current_error > drift_level:
            status = DriftStatus.DRIFT
            drift_type = DriftType.SUDDEN
            # Reset after drift
            self._ddm_n_samples = 0
        elif current_error > warning_level:
            status = DriftStatus.WARNING
            drift_type = DriftType.GRADUAL
        else:
            status = DriftStatus.NO_DRIFT
            drift_type = None

        return DriftResult(
            timestamp=datetime.now(),
            status=status,
            drift_type=drift_type,
            p_value=None,
            statistic=current_error,
            threshold=drift_level,
            details={
                "current_error": current_error,
                "min_error": self._ddm_min_error,
                "warning_level": warning_level,
                "drift_level": drift_level,
            },
        )

    def _detect_feature_drift(
        self,
        test_data: np.ndarray,
    ) -> Dict[str, float]:
        """Detect drift for individual features."""
        from scipy import stats

        if self._reference_data is None:
            return {}

        feature_drifts = {}

        for i in range(test_data.shape[1]):
            ref_col = self._reference_data[:, i]
            test_col = test_data[:, i]

            stat, p_value = stats.ks_2samp(ref_col, test_col)
            feature_drifts[f"feature_{i}"] = float(stat)

        return feature_drifts

    def get_detection_history(self) -> List[DriftResult]:
        """Get history of drift detections."""
        return self._detection_history

    def reset(self) -> None:
        """Reset detector state."""
        self._buffer.clear()
        self._detection_history.clear()
        self._ddm_min_error = float('inf')
        self._ddm_min_std = float('inf')
        self._ddm_n_samples = 0


class ConceptDriftDetector:
    """
    Specialized detector for concept drift (change in P(y|X)).

    Uses prediction errors to detect when model needs retraining.
    """

    def __init__(
        self,
        warning_threshold: float = 2.0,
        drift_threshold: float = 3.0,
        window_size: int = 100,
    ):
        self.warning_threshold = warning_threshold
        self.drift_threshold = drift_threshold
        self.window_size = window_size

        self._error_buffer: deque = deque(maxlen=window_size)
        self._baseline_mean: Optional[float] = None
        self._baseline_std: Optional[float] = None

    def set_baseline(self, errors: np.ndarray) -> None:
        """Set baseline error distribution."""
        self._baseline_mean = float(np.mean(errors))
        self._baseline_std = float(np.std(errors)) + 1e-6

    def update(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
    ) -> DriftStatus:
        """Update with new predictions and check for drift."""
        errors = np.abs(y_true - y_pred)

        for error in errors.flatten():
            self._error_buffer.append(error)

        if self._baseline_mean is None:
            if len(self._error_buffer) >= self.window_size:
                self.set_baseline(np.array(list(self._error_buffer)))
            return DriftStatus.NO_DRIFT

        # Calculate z-score of current error rate
        current_mean = np.mean(list(self._error_buffer))
        z_score = (current_mean - self._baseline_mean) / self._baseline_std

        if z_score > self.drift_threshold:
            return DriftStatus.DRIFT
        elif z_score > self.warning_threshold:
            return DriftStatus.WARNING
        else:
            return DriftStatus.NO_DRIFT
