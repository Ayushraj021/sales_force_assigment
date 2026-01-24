"""
Model Monitor

Model performance and drift monitoring.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from enum import Enum
import logging
import numpy as np

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(str, Enum):
    """Types of monitoring alerts."""
    DRIFT = "drift"
    PERFORMANCE = "performance"
    LATENCY = "latency"
    ERROR_RATE = "error_rate"
    THRESHOLD = "threshold"


@dataclass
class MonitorConfig:
    """Monitoring configuration."""
    drift_threshold: float = 0.1
    performance_threshold: float = 0.8
    latency_threshold_ms: float = 1000
    error_rate_threshold: float = 0.05
    check_interval_minutes: int = 60


@dataclass
class MonitorAlert:
    """Monitoring alert."""
    alert_id: str
    alert_type: AlertType
    severity: AlertSeverity
    model_name: str
    message: str
    metric_name: Optional[str] = None
    current_value: Optional[float] = None
    threshold_value: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "alert_type": self.alert_type.value,
            "severity": self.severity.value,
            "model_name": self.model_name,
            "message": self.message,
            "metric_name": self.metric_name,
            "current_value": self.current_value,
            "threshold_value": self.threshold_value,
            "timestamp": self.timestamp.isoformat(),
        }


class ModelMonitor:
    """
    Model Monitoring Service.

    Features:
    - Performance tracking
    - Drift detection
    - Alert management
    - Metric collection

    Example:
        monitor = ModelMonitor()

        # Log prediction
        monitor.log_prediction(
            model_name="forecast",
            prediction=100.5,
            actual=102.0,
            latency_ms=50
        )

        # Check for drift
        alerts = monitor.check_drift("forecast", new_data)
    """

    def __init__(self, config: Optional[MonitorConfig] = None):
        self.config = config or MonitorConfig()
        self._metrics: Dict[str, List[Dict]] = {}
        self._baselines: Dict[str, Dict] = {}
        self._alerts: List[MonitorAlert] = []
        self._alert_handlers: List[Callable[[MonitorAlert], None]] = []

    def log_prediction(
        self,
        model_name: str,
        prediction: float,
        actual: Optional[float] = None,
        latency_ms: float = 0,
        features: Optional[Dict[str, float]] = None,
    ) -> None:
        """
        Log a prediction for monitoring.

        Args:
            model_name: Model identifier
            prediction: Predicted value
            actual: Actual value (if known)
            latency_ms: Inference latency
            features: Input features
        """
        if model_name not in self._metrics:
            self._metrics[model_name] = []

        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "prediction": prediction,
            "actual": actual,
            "latency_ms": latency_ms,
            "features": features or {},
        }

        if actual is not None:
            entry["error"] = prediction - actual
            entry["abs_error"] = abs(entry["error"])
            entry["pct_error"] = abs(entry["error"]) / abs(actual) if actual != 0 else 0

        self._metrics[model_name].append(entry)

        # Check thresholds
        self._check_latency(model_name, latency_ms)

    def set_baseline(
        self,
        model_name: str,
        metrics: Dict[str, float],
        feature_distributions: Optional[Dict[str, Dict]] = None,
    ) -> None:
        """
        Set baseline for comparison.

        Args:
            model_name: Model identifier
            metrics: Baseline metric values
            feature_distributions: Baseline feature distributions
        """
        self._baselines[model_name] = {
            "metrics": metrics,
            "feature_distributions": feature_distributions or {},
            "timestamp": datetime.utcnow().isoformat(),
        }

    def check_drift(
        self,
        model_name: str,
        current_data: np.ndarray,
        feature_names: Optional[List[str]] = None,
    ) -> List[MonitorAlert]:
        """
        Check for data drift.

        Args:
            model_name: Model identifier
            current_data: Current feature data
            feature_names: Feature names

        Returns:
            List of drift alerts
        """
        alerts = []
        baseline = self._baselines.get(model_name, {})
        baseline_distributions = baseline.get("feature_distributions", {})

        if not baseline_distributions:
            return alerts

        feature_names = feature_names or [f"feature_{i}" for i in range(current_data.shape[1])]

        for i, name in enumerate(feature_names):
            if name not in baseline_distributions:
                continue

            base_dist = baseline_distributions[name]
            current_values = current_data[:, i]

            # Calculate distribution shift (simplified KS-like test)
            base_mean = base_dist.get("mean", 0)
            base_std = base_dist.get("std", 1)

            current_mean = np.mean(current_values)
            current_std = np.std(current_values)

            shift = abs(current_mean - base_mean) / (base_std + 1e-10)

            if shift > self.config.drift_threshold:
                alert = self._create_alert(
                    AlertType.DRIFT,
                    AlertSeverity.WARNING if shift < 2 * self.config.drift_threshold else AlertSeverity.CRITICAL,
                    model_name,
                    f"Feature '{name}' has drifted significantly (shift: {shift:.2f})",
                    metric_name=name,
                    current_value=float(current_mean),
                    threshold_value=float(base_mean),
                )
                alerts.append(alert)

        return alerts

    def check_performance(
        self,
        model_name: str,
        window_size: int = 100,
    ) -> List[MonitorAlert]:
        """
        Check model performance against baseline.

        Args:
            model_name: Model identifier
            window_size: Number of recent predictions to check

        Returns:
            List of performance alerts
        """
        alerts = []
        metrics = self._metrics.get(model_name, [])
        baseline = self._baselines.get(model_name, {}).get("metrics", {})

        if not metrics or not baseline:
            return alerts

        # Get recent metrics with actuals
        recent = [m for m in metrics[-window_size:] if m.get("actual") is not None]
        if not recent:
            return alerts

        # Calculate current MAPE
        current_mape = np.mean([m.get("pct_error", 0) for m in recent])
        baseline_mape = baseline.get("mape", 0)

        if baseline_mape > 0:
            degradation = (current_mape - baseline_mape) / baseline_mape

            if degradation > self.config.performance_threshold:
                alert = self._create_alert(
                    AlertType.PERFORMANCE,
                    AlertSeverity.WARNING if degradation < 0.5 else AlertSeverity.CRITICAL,
                    model_name,
                    f"Model performance degraded by {degradation:.1%}",
                    metric_name="mape",
                    current_value=float(current_mape),
                    threshold_value=float(baseline_mape),
                )
                alerts.append(alert)

        return alerts

    def _check_latency(self, model_name: str, latency_ms: float) -> None:
        """Check latency threshold."""
        if latency_ms > self.config.latency_threshold_ms:
            alert = self._create_alert(
                AlertType.LATENCY,
                AlertSeverity.WARNING,
                model_name,
                f"High latency detected: {latency_ms:.0f}ms",
                metric_name="latency_ms",
                current_value=latency_ms,
                threshold_value=self.config.latency_threshold_ms,
            )
            self._trigger_alert(alert)

    def _create_alert(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        model_name: str,
        message: str,
        **kwargs,
    ) -> MonitorAlert:
        """Create a monitoring alert."""
        import uuid
        alert = MonitorAlert(
            alert_id=str(uuid.uuid4()),
            alert_type=alert_type,
            severity=severity,
            model_name=model_name,
            message=message,
            **kwargs,
        )
        self._alerts.append(alert)
        self._trigger_alert(alert)
        return alert

    def _trigger_alert(self, alert: MonitorAlert) -> None:
        """Trigger alert handlers."""
        for handler in self._alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Alert handler failed: {e}")

    def add_alert_handler(
        self,
        handler: Callable[[MonitorAlert], None],
    ) -> None:
        """Add an alert handler."""
        self._alert_handlers.append(handler)

    def get_metrics(
        self,
        model_name: str,
        since: Optional[datetime] = None,
    ) -> List[Dict]:
        """Get logged metrics."""
        metrics = self._metrics.get(model_name, [])

        if since:
            metrics = [
                m for m in metrics
                if datetime.fromisoformat(m["timestamp"]) >= since
            ]

        return metrics

    def get_alerts(
        self,
        model_name: Optional[str] = None,
        severity: Optional[AlertSeverity] = None,
    ) -> List[MonitorAlert]:
        """Get alerts."""
        alerts = self._alerts

        if model_name:
            alerts = [a for a in alerts if a.model_name == model_name]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        return alerts

    def get_summary(self, model_name: str) -> Dict[str, Any]:
        """Get monitoring summary."""
        metrics = self._metrics.get(model_name, [])
        alerts = [a for a in self._alerts if a.model_name == model_name]

        if not metrics:
            return {"status": "no_data"}

        recent = metrics[-100:]
        recent_with_actual = [m for m in recent if m.get("actual") is not None]

        summary = {
            "total_predictions": len(metrics),
            "recent_predictions": len(recent),
            "avg_latency_ms": np.mean([m.get("latency_ms", 0) for m in recent]),
            "alert_count": len(alerts),
            "critical_alerts": len([a for a in alerts if a.severity == AlertSeverity.CRITICAL]),
        }

        if recent_with_actual:
            summary["current_mae"] = np.mean([m["abs_error"] for m in recent_with_actual])
            summary["current_mape"] = np.mean([m["pct_error"] for m in recent_with_actual])

        return summary
