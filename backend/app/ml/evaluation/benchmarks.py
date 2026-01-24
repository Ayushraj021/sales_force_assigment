"""
Model Benchmarking

Compare models against baselines and each other.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
import numpy as np
import pandas as pd
import time
import logging

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Result from model benchmark."""
    model_name: str
    metrics: Dict[str, float]
    training_time_seconds: float
    inference_time_seconds: float
    memory_usage_mb: Optional[float] = None
    model_size_mb: Optional[float] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    rank: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "metrics": self.metrics,
            "training_time_seconds": self.training_time_seconds,
            "inference_time_seconds": self.inference_time_seconds,
            "memory_usage_mb": self.memory_usage_mb,
            "model_size_mb": self.model_size_mb,
            "rank": self.rank,
        }


class ModelBenchmark:
    """
    Model Benchmarking Framework.

    Features:
    - Compare multiple models
    - Baseline comparisons
    - Performance profiling
    - Results ranking

    Example:
        benchmark = ModelBenchmark()

        # Add models
        benchmark.add_model("Linear", LinearRegression())
        benchmark.add_model("XGBoost", XGBRegressor())

        # Run benchmark
        results = benchmark.run(X_train, y_train, X_test, y_test)

        # Get ranking
        ranking = benchmark.get_ranking(metric="rmse")
    """

    def __init__(
        self,
        include_baselines: bool = True,
        primary_metric: str = "rmse",
        cv_folds: int = 0,
    ):
        self.include_baselines = include_baselines
        self.primary_metric = primary_metric
        self.cv_folds = cv_folds
        self._models: Dict[str, Any] = {}
        self._results: List[BenchmarkResult] = []

    def add_model(
        self,
        name: str,
        model: Any,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Add a model to benchmark.

        Args:
            name: Model name
            model: Model instance
            parameters: Model parameters (for logging)
        """
        self._models[name] = {
            "model": model,
            "parameters": parameters or {},
        }

    def run(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_test: np.ndarray,
        y_test: np.ndarray,
        metric_fn: Optional[Callable] = None,
    ) -> List[BenchmarkResult]:
        """
        Run benchmark on all models.

        Args:
            X_train: Training features
            y_train: Training target
            X_test: Test features
            y_test: Test target
            metric_fn: Optional custom metric function

        Returns:
            List of BenchmarkResult
        """
        from .metrics import calculate_metrics

        self._results = []

        # Add baselines if requested
        if self.include_baselines:
            self._add_baselines()

        for name, model_info in self._models.items():
            model = model_info["model"]
            parameters = model_info["parameters"]

            try:
                # Time training
                start_time = time.time()
                model.fit(X_train, y_train)
                training_time = time.time() - start_time

                # Time inference
                start_time = time.time()
                y_pred = model.predict(X_test)
                inference_time = time.time() - start_time

                # Calculate metrics
                if metric_fn:
                    metrics = metric_fn(y_test, y_pred)
                else:
                    metrics_obj = calculate_metrics(y_test, y_pred, metric_type="regression")
                    metrics = {
                        "r2": metrics_obj.r2,
                        "rmse": metrics_obj.rmse,
                        "mae": metrics_obj.mae,
                        "mape": metrics_obj.mape or 0,
                    }

                # Estimate model size
                model_size = self._estimate_model_size(model)

                result = BenchmarkResult(
                    model_name=name,
                    metrics=metrics,
                    training_time_seconds=training_time,
                    inference_time_seconds=inference_time,
                    model_size_mb=model_size,
                    parameters=parameters,
                )
                self._results.append(result)

            except Exception as e:
                logger.error(f"Benchmark failed for {name}: {e}")
                self._results.append(BenchmarkResult(
                    model_name=name,
                    metrics={"error": str(e)},
                    training_time_seconds=0,
                    inference_time_seconds=0,
                ))

        # Rank results
        self._rank_results()

        return self._results

    def _add_baselines(self) -> None:
        """Add baseline models."""
        from sklearn.dummy import DummyRegressor
        from sklearn.linear_model import LinearRegression

        if "Mean Baseline" not in self._models:
            self._models["Mean Baseline"] = {
                "model": DummyRegressor(strategy="mean"),
                "parameters": {"strategy": "mean"},
            }

        if "Linear Regression" not in self._models:
            self._models["Linear Regression"] = {
                "model": LinearRegression(),
                "parameters": {},
            }

    def _estimate_model_size(self, model: Any) -> Optional[float]:
        """Estimate model size in MB."""
        try:
            import pickle
            serialized = pickle.dumps(model)
            return len(serialized) / (1024 * 1024)
        except Exception:
            return None

    def _rank_results(self) -> None:
        """Rank results by primary metric."""
        # Lower is better for error metrics
        lower_is_better = self.primary_metric in ["rmse", "mae", "mse", "mape"]

        valid_results = [r for r in self._results if self.primary_metric in r.metrics]
        sorted_results = sorted(
            valid_results,
            key=lambda x: x.metrics.get(self.primary_metric, float("inf")),
            reverse=not lower_is_better,
        )

        for rank, result in enumerate(sorted_results, 1):
            result.rank = rank

    def get_ranking(
        self,
        metric: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Get model ranking.

        Args:
            metric: Metric to rank by (default: primary metric)

        Returns:
            DataFrame with rankings
        """
        metric = metric or self.primary_metric

        data = []
        for result in self._results:
            row = {
                "rank": result.rank,
                "model": result.model_name,
                metric: result.metrics.get(metric),
                "training_time_s": result.training_time_seconds,
                "inference_time_s": result.inference_time_seconds,
            }
            data.append(row)

        df = pd.DataFrame(data)
        return df.sort_values("rank")

    def get_best_model(self) -> Optional[BenchmarkResult]:
        """Get the best performing model."""
        ranked = [r for r in self._results if r.rank == 1]
        return ranked[0] if ranked else None

    def compare_to_baseline(
        self,
        baseline_name: str = "Mean Baseline",
    ) -> pd.DataFrame:
        """
        Compare all models to a baseline.

        Args:
            baseline_name: Name of baseline model

        Returns:
            DataFrame with improvement percentages
        """
        baseline = next((r for r in self._results if r.model_name == baseline_name), None)
        if not baseline:
            return pd.DataFrame()

        data = []
        for result in self._results:
            if result.model_name == baseline_name:
                continue

            row = {"model": result.model_name}
            for metric in baseline.metrics:
                if metric in result.metrics:
                    baseline_val = baseline.metrics[metric]
                    model_val = result.metrics[metric]
                    if baseline_val != 0:
                        improvement = (baseline_val - model_val) / baseline_val * 100
                        row[f"{metric}_improvement_%"] = improvement

            data.append(row)

        return pd.DataFrame(data)

    def to_dataframe(self) -> pd.DataFrame:
        """Convert all results to DataFrame."""
        data = []
        for result in self._results:
            row = {
                "model": result.model_name,
                "rank": result.rank,
                "training_time_s": result.training_time_seconds,
                "inference_time_s": result.inference_time_seconds,
                "model_size_mb": result.model_size_mb,
            }
            row.update(result.metrics)
            data.append(row)

        return pd.DataFrame(data)


def run_benchmark(
    models: Dict[str, Any],
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    primary_metric: str = "rmse",
) -> pd.DataFrame:
    """
    Quick benchmark function.

    Args:
        models: Dict of model name to model instance
        X_train: Training features
        y_train: Training target
        X_test: Test features
        y_test: Test target
        primary_metric: Metric to rank by

    Returns:
        DataFrame with benchmark results
    """
    benchmark = ModelBenchmark(primary_metric=primary_metric)

    for name, model in models.items():
        benchmark.add_model(name, model)

    benchmark.run(X_train, y_train, X_test, y_test)
    return benchmark.to_dataframe()
