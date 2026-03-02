"""
Inference Pipeline

Model inference and serving pipeline.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class InferenceConfig:
    """Inference pipeline configuration."""
    batch_size: int = 1000
    timeout_seconds: float = 30.0
    cache_predictions: bool = True
    return_confidence: bool = True
    confidence_level: float = 0.95


@dataclass
class InferenceResult:
    """Inference result."""
    predictions: np.ndarray
    lower_bounds: Optional[np.ndarray] = None
    upper_bounds: Optional[np.ndarray] = None
    inference_time_ms: float = 0.0
    batch_id: Optional[str] = None


class InferencePipeline:
    """
    Model Inference Pipeline.

    Features:
    - Batch prediction
    - Confidence intervals
    - Caching
    - Performance monitoring

    Example:
        pipeline = InferencePipeline(model, config)
        result = pipeline.predict(X)
    """

    def __init__(
        self,
        model: Any,
        config: Optional[InferenceConfig] = None,
    ):
        self.model = model
        self.config = config or InferenceConfig()
        self._cache: Dict[str, InferenceResult] = {}
        self._prediction_count = 0

    def predict(
        self,
        X: np.ndarray,
        return_interval: bool = False,
    ) -> InferenceResult:
        """
        Make predictions.

        Args:
            X: Feature matrix
            return_interval: Return confidence intervals

        Returns:
            InferenceResult
        """
        import time
        start_time = time.time()

        # Check cache
        cache_key = self._get_cache_key(X)
        if self.config.cache_predictions and cache_key in self._cache:
            return self._cache[cache_key]

        # Batch prediction
        if len(X) > self.config.batch_size:
            predictions = self._batch_predict(X)
        else:
            predictions = self._single_predict(X)

        # Calculate confidence intervals
        lower_bounds = None
        upper_bounds = None
        if return_interval or self.config.return_confidence:
            lower_bounds, upper_bounds = self._calculate_intervals(predictions, X)

        inference_time = (time.time() - start_time) * 1000

        result = InferenceResult(
            predictions=predictions,
            lower_bounds=lower_bounds,
            upper_bounds=upper_bounds,
            inference_time_ms=inference_time,
        )

        # Cache result
        if self.config.cache_predictions:
            self._cache[cache_key] = result

        self._prediction_count += len(X)

        return result

    def _single_predict(self, X: np.ndarray) -> np.ndarray:
        """Make single batch prediction."""
        return self.model.predict(X)

    def _batch_predict(self, X: np.ndarray) -> np.ndarray:
        """Make batched predictions."""
        predictions = []

        for i in range(0, len(X), self.config.batch_size):
            batch = X[i:i + self.config.batch_size]
            batch_preds = self.model.predict(batch)
            predictions.append(batch_preds)

        return np.concatenate(predictions)

    def _calculate_intervals(
        self,
        predictions: np.ndarray,
        X: np.ndarray,
    ) -> tuple:
        """Calculate confidence intervals."""
        # Check if model has native prediction intervals
        if hasattr(self.model, "predict_interval"):
            return self.model.predict_interval(X, self.config.confidence_level)

        # Estimate intervals from prediction variance
        # This is a simple approximation
        if hasattr(self.model, "estimators_"):
            # For ensemble models, use ensemble variance
            preds = np.array([est.predict(X) for est in self.model.estimators_])
            std = np.std(preds, axis=0)
        else:
            # Simple heuristic: 10% of prediction
            std = np.abs(predictions) * 0.1

        z = 1.96 if self.config.confidence_level == 0.95 else 2.576
        lower = predictions - z * std
        upper = predictions + z * std

        return lower, upper

    def _get_cache_key(self, X: np.ndarray) -> str:
        """Generate cache key from input."""
        return str(hash(X.tobytes()))

    def clear_cache(self) -> None:
        """Clear prediction cache."""
        self._cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        return {
            "prediction_count": self._prediction_count,
            "cache_size": len(self._cache),
        }
