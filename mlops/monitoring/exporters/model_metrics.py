"""
Custom Prometheus metrics exporter for ML model metrics.

Exposes model performance, inference, and drift metrics to Prometheus.
"""

import time
from typing import Any

from prometheus_client import Counter, Gauge, Histogram, Info, start_http_server

# Model performance metrics
MODEL_MAPE = Gauge(
    "model_mape",
    "Mean Absolute Percentage Error",
    ["model_name", "model_version"],
)

MODEL_RMSE = Gauge(
    "model_rmse",
    "Root Mean Square Error",
    ["model_name", "model_version"],
)

MODEL_MAE = Gauge(
    "model_mae",
    "Mean Absolute Error",
    ["model_name", "model_version"],
)

MODEL_R2 = Gauge(
    "model_r2",
    "R-squared score",
    ["model_name", "model_version"],
)

# Inference metrics
MODEL_PREDICTIONS_TOTAL = Counter(
    "model_predictions_total",
    "Total number of predictions",
    ["model_name", "model_version"],
)

MODEL_PREDICTION_ERRORS_TOTAL = Counter(
    "model_prediction_errors_total",
    "Total number of prediction errors",
    ["model_name", "model_version", "error_type"],
)

MODEL_INFERENCE_LATENCY = Histogram(
    "model_inference_latency_seconds",
    "Model inference latency in seconds",
    ["model_name", "model_version"],
    buckets=(0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 10.0),
)

# Feature cache metrics
FEATURE_CACHE_HITS = Counter(
    "feature_cache_hits_total",
    "Total number of feature cache hits",
    ["feature_group"],
)

FEATURE_CACHE_MISSES = Counter(
    "feature_cache_misses_total",
    "Total number of feature cache misses",
    ["feature_group"],
)

FEATURE_RETRIEVAL_LATENCY = Histogram(
    "feature_retrieval_latency_seconds",
    "Feature retrieval latency in seconds",
    ["feature_group"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)

# Drift detection metrics
DATA_DRIFT_DETECTED = Gauge(
    "data_drift_detected",
    "Whether data drift is detected (1=yes, 0=no)",
)

DATA_DRIFT_SCORE = Gauge(
    "data_drift_score",
    "Overall data drift score",
)

FEATURE_DRIFT_DETECTED = Gauge(
    "feature_drift_detected",
    "Whether feature drift is detected",
    ["feature_name"],
)

FEATURE_DRIFT_P_VALUE = Gauge(
    "feature_drift_p_value",
    "Feature drift p-value from KS-test",
    ["feature_name"],
)

FEATURE_DRIFT_STATISTIC = Gauge(
    "feature_drift_statistic",
    "Feature drift test statistic",
    ["feature_name"],
)

CONCEPT_DRIFT_SCORE = Gauge(
    "concept_drift_score",
    "Concept drift score",
)

# Training metrics
TRAINING_JOB_STATUS = Gauge(
    "training_job_status",
    "Training job status (1=running, 0=completed, -1=failed)",
    ["job_id", "model_name", "status"],
)

TRAINING_JOB_DURATION = Gauge(
    "training_job_duration_seconds",
    "Training job duration in seconds",
    ["job_id", "model_name", "status"],
)

TRAINING_JOB_LAST_COMPLETED = Gauge(
    "training_job_last_completed_timestamp",
    "Timestamp of last completed training job",
    ["model_name"],
)

# Model info
MODEL_INFO = Info(
    "model_info",
    "Information about the deployed model",
)


class ModelMetricsExporter:
    """
    Exporter for model-related Prometheus metrics.

    Usage:
        exporter = ModelMetricsExporter()
        exporter.start_server(port=8001)

        # Record metrics
        exporter.record_prediction("ensemble", "v1.0", latency=0.05)
        exporter.update_performance_metrics("ensemble", "v1.0", mape=0.042, rmse=1200)
    """

    def __init__(self):
        self.active_models: dict[str, dict[str, Any]] = {}

    def start_server(self, port: int = 8001) -> None:
        """Start the Prometheus metrics HTTP server."""
        start_http_server(port)
        print(f"Model metrics exporter started on port {port}")

    def record_prediction(
        self,
        model_name: str,
        model_version: str,
        latency_seconds: float,
        error: bool = False,
        error_type: str | None = None,
    ) -> None:
        """Record a prediction event."""
        MODEL_PREDICTIONS_TOTAL.labels(
            model_name=model_name,
            model_version=model_version,
        ).inc()

        MODEL_INFERENCE_LATENCY.labels(
            model_name=model_name,
            model_version=model_version,
        ).observe(latency_seconds)

        if error:
            MODEL_PREDICTION_ERRORS_TOTAL.labels(
                model_name=model_name,
                model_version=model_version,
                error_type=error_type or "unknown",
            ).inc()

    def update_performance_metrics(
        self,
        model_name: str,
        model_version: str,
        mape: float | None = None,
        rmse: float | None = None,
        mae: float | None = None,
        r2: float | None = None,
    ) -> None:
        """Update model performance metrics."""
        labels = {"model_name": model_name, "model_version": model_version}

        if mape is not None:
            MODEL_MAPE.labels(**labels).set(mape)
        if rmse is not None:
            MODEL_RMSE.labels(**labels).set(rmse)
        if mae is not None:
            MODEL_MAE.labels(**labels).set(mae)
        if r2 is not None:
            MODEL_R2.labels(**labels).set(r2)

    def record_feature_retrieval(
        self,
        feature_group: str,
        latency_seconds: float,
        cache_hit: bool,
    ) -> None:
        """Record feature retrieval metrics."""
        FEATURE_RETRIEVAL_LATENCY.labels(feature_group=feature_group).observe(
            latency_seconds
        )

        if cache_hit:
            FEATURE_CACHE_HITS.labels(feature_group=feature_group).inc()
        else:
            FEATURE_CACHE_MISSES.labels(feature_group=feature_group).inc()

    def update_drift_metrics(
        self,
        drift_detected: bool,
        drift_score: float,
        feature_drift: dict[str, dict[str, float]] | None = None,
        concept_drift_score: float | None = None,
    ) -> None:
        """Update drift detection metrics."""
        DATA_DRIFT_DETECTED.set(1 if drift_detected else 0)
        DATA_DRIFT_SCORE.set(drift_score)

        if feature_drift:
            for feature_name, metrics in feature_drift.items():
                FEATURE_DRIFT_DETECTED.labels(feature_name=feature_name).set(
                    1 if metrics.get("drift", False) else 0
                )
                if "p_value" in metrics:
                    FEATURE_DRIFT_P_VALUE.labels(feature_name=feature_name).set(
                        metrics["p_value"]
                    )
                if "statistic" in metrics:
                    FEATURE_DRIFT_STATISTIC.labels(feature_name=feature_name).set(
                        metrics["statistic"]
                    )

        if concept_drift_score is not None:
            CONCEPT_DRIFT_SCORE.set(concept_drift_score)

    def update_training_job_status(
        self,
        job_id: str,
        model_name: str,
        status: str,
        duration_seconds: float | None = None,
    ) -> None:
        """Update training job status metrics."""
        status_value = {"running": 1, "completed": 0, "failed": -1}.get(status, 0)

        TRAINING_JOB_STATUS.labels(
            job_id=job_id,
            model_name=model_name,
            status=status,
        ).set(status_value)

        if duration_seconds is not None:
            TRAINING_JOB_DURATION.labels(
                job_id=job_id,
                model_name=model_name,
                status=status,
            ).set(duration_seconds)

        if status == "completed":
            TRAINING_JOB_LAST_COMPLETED.labels(model_name=model_name).set(time.time())

    def update_model_info(
        self,
        model_name: str,
        model_version: str,
        model_type: str,
        mlflow_run_id: str | None = None,
    ) -> None:
        """Update model information metric."""
        MODEL_INFO.info({
            "model_name": model_name,
            "model_version": model_version,
            "model_type": model_type,
            "mlflow_run_id": mlflow_run_id or "",
        })


# Singleton exporter instance
_exporter: ModelMetricsExporter | None = None


def get_metrics_exporter() -> ModelMetricsExporter:
    """Get the singleton metrics exporter instance."""
    global _exporter
    if _exporter is None:
        _exporter = ModelMetricsExporter()
    return _exporter


if __name__ == "__main__":
    # Start the metrics server for testing
    exporter = get_metrics_exporter()
    exporter.start_server(port=8001)

    # Keep the server running
    print("Metrics server running. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")
