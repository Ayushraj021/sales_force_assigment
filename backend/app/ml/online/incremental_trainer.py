"""
Incremental Model Trainer

Online learning with incremental model updates.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
import numpy as np
from datetime import datetime
import logging
from collections import deque

logger = logging.getLogger(__name__)


class UpdateStrategy(str, Enum):
    """Strategies for incremental updates."""
    PARTIAL_FIT = "partial_fit"  # Use partial_fit if available
    WINDOW = "window"  # Sliding window retraining
    WEIGHTED = "weighted"  # Weighted combination of old and new
    ENSEMBLE = "ensemble"  # Maintain ensemble of models


@dataclass
class UpdateResult:
    """Result of an incremental update."""
    timestamp: datetime
    n_samples: int
    old_metrics: Dict[str, float]
    new_metrics: Dict[str, float]
    improvement: float
    update_duration: float
    model_version: int


@dataclass
class IncrementalConfig:
    """Configuration for incremental training."""
    strategy: UpdateStrategy = UpdateStrategy.PARTIAL_FIT
    window_size: int = 1000
    min_samples_for_update: int = 50
    update_frequency: int = 100  # Update every N samples
    learning_rate: float = 0.1
    decay_factor: float = 0.99  # For weighted strategy
    max_ensemble_size: int = 5  # For ensemble strategy
    validation_split: float = 0.2
    early_stopping: bool = True
    patience: int = 3


class IncrementalTrainer:
    """
    Incremental Model Trainer for Online Learning.

    Features:
    - Multiple update strategies (partial_fit, window, weighted, ensemble)
    - Automatic performance monitoring
    - Buffer management for batch updates
    - Model versioning

    Example:
        trainer = IncrementalTrainer(model, config)

        for batch in data_stream:
            result = trainer.update(X_batch, y_batch)
            print(f"New performance: {result.new_metrics}")
    """

    def __init__(
        self,
        model: Any,
        config: Optional[IncrementalConfig] = None,
        feature_names: Optional[List[str]] = None,
    ):
        self.model = model
        self.config = config or IncrementalConfig()
        self.feature_names = feature_names

        # Data buffer
        self._X_buffer: deque = deque(maxlen=self.config.window_size)
        self._y_buffer: deque = deque(maxlen=self.config.window_size)

        # Model versioning
        self._model_version = 0
        self._model_history: List[Any] = []

        # Performance tracking
        self._update_history: List[UpdateResult] = []
        self._samples_since_update = 0

        # Ensemble models (for ensemble strategy)
        self._ensemble_models: List[Any] = []
        self._ensemble_weights: List[float] = []

    def update(
        self,
        X: np.ndarray,
        y: np.ndarray,
        validate: bool = True,
    ) -> Optional[UpdateResult]:
        """
        Update model with new data.

        Args:
            X: New feature data
            y: New target data
            validate: Whether to compute validation metrics

        Returns:
            UpdateResult if update was performed, None otherwise
        """
        X = np.atleast_2d(X)
        y = np.atleast_1d(y)

        # Add to buffer
        for i in range(len(X)):
            self._X_buffer.append(X[i])
            self._y_buffer.append(y[i])

        self._samples_since_update += len(X)

        # Check if update should be triggered
        if self._samples_since_update < self.config.update_frequency:
            return None

        if len(self._X_buffer) < self.config.min_samples_for_update:
            return None

        # Perform update
        start_time = datetime.now()

        X_buffer = np.array(list(self._X_buffer))
        y_buffer = np.array(list(self._y_buffer))

        # Get old metrics if validate
        old_metrics = {}
        if validate:
            old_metrics = self._evaluate(X_buffer, y_buffer)

        # Update based on strategy
        if self.config.strategy == UpdateStrategy.PARTIAL_FIT:
            self._partial_fit_update(X_buffer, y_buffer)
        elif self.config.strategy == UpdateStrategy.WINDOW:
            self._window_update(X_buffer, y_buffer)
        elif self.config.strategy == UpdateStrategy.WEIGHTED:
            self._weighted_update(X_buffer, y_buffer)
        elif self.config.strategy == UpdateStrategy.ENSEMBLE:
            self._ensemble_update(X_buffer, y_buffer)

        # Get new metrics
        new_metrics = {}
        if validate:
            new_metrics = self._evaluate(X_buffer, y_buffer)

        # Calculate improvement
        improvement = 0.0
        if "mae" in old_metrics and "mae" in new_metrics:
            improvement = old_metrics["mae"] - new_metrics["mae"]

        # Update version
        self._model_version += 1
        self._samples_since_update = 0

        update_duration = (datetime.now() - start_time).total_seconds()

        result = UpdateResult(
            timestamp=datetime.now(),
            n_samples=len(X_buffer),
            old_metrics=old_metrics,
            new_metrics=new_metrics,
            improvement=improvement,
            update_duration=update_duration,
            model_version=self._model_version,
        )

        self._update_history.append(result)

        return result

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Generate predictions using current model."""
        X = np.atleast_2d(X)

        if self.config.strategy == UpdateStrategy.ENSEMBLE and self._ensemble_models:
            # Weighted ensemble prediction
            predictions = np.zeros(len(X))
            total_weight = sum(self._ensemble_weights)

            for model, weight in zip(self._ensemble_models, self._ensemble_weights):
                predictions += (weight / total_weight) * model.predict(X)

            return predictions
        else:
            return self.model.predict(X)

    def _partial_fit_update(
        self,
        X: np.ndarray,
        y: np.ndarray,
    ) -> None:
        """Update using partial_fit."""
        if hasattr(self.model, "partial_fit"):
            self.model.partial_fit(X, y)
        else:
            # Fallback to full retraining
            self.model.fit(X, y)

    def _window_update(
        self,
        X: np.ndarray,
        y: np.ndarray,
    ) -> None:
        """Retrain on sliding window."""
        self.model.fit(X, y)

    def _weighted_update(
        self,
        X: np.ndarray,
        y: np.ndarray,
    ) -> None:
        """Weighted combination update."""
        # Create sample weights with exponential decay
        n_samples = len(X)
        weights = np.array([
            self.config.decay_factor ** (n_samples - i - 1)
            for i in range(n_samples)
        ])
        weights /= weights.sum()

        if hasattr(self.model, "fit"):
            # Try to use sample_weight if supported
            try:
                self.model.fit(X, y, sample_weight=weights)
            except TypeError:
                self.model.fit(X, y)

    def _ensemble_update(
        self,
        X: np.ndarray,
        y: np.ndarray,
    ) -> None:
        """Update ensemble of models."""
        import copy

        # Train new model on recent data
        new_model = copy.deepcopy(self.model)
        new_model.fit(X, y)

        # Evaluate on validation set
        n_val = int(len(X) * self.config.validation_split)
        X_val, y_val = X[-n_val:], y[-n_val:]

        # Calculate weight based on performance
        y_pred = new_model.predict(X_val)
        mae = np.mean(np.abs(y_val - y_pred))
        weight = 1.0 / (mae + 1e-6)

        # Add to ensemble
        self._ensemble_models.append(new_model)
        self._ensemble_weights.append(weight)

        # Prune ensemble if too large
        if len(self._ensemble_models) > self.config.max_ensemble_size:
            # Remove worst performing model
            min_idx = np.argmin(self._ensemble_weights)
            self._ensemble_models.pop(min_idx)
            self._ensemble_weights.pop(min_idx)

    def _evaluate(
        self,
        X: np.ndarray,
        y: np.ndarray,
    ) -> Dict[str, float]:
        """Evaluate current model."""
        try:
            y_pred = self.predict(X)

            mae = float(np.mean(np.abs(y - y_pred)))
            rmse = float(np.sqrt(np.mean((y - y_pred) ** 2)))

            return {"mae": mae, "rmse": rmse}
        except Exception:
            return {}

    def get_update_history(self) -> List[UpdateResult]:
        """Get history of updates."""
        return self._update_history

    def get_model_version(self) -> int:
        """Get current model version."""
        return self._model_version

    def reset_buffer(self) -> None:
        """Clear data buffer."""
        self._X_buffer.clear()
        self._y_buffer.clear()
        self._samples_since_update = 0


class StreamingForecaster:
    """
    Streaming forecaster for real-time predictions.

    Combines incremental learning with streaming predictions.
    """

    def __init__(
        self,
        base_model: Any,
        config: Optional[IncrementalConfig] = None,
    ):
        self.trainer = IncrementalTrainer(base_model, config)
        self._prediction_history: List[Dict] = []

    def process(
        self,
        X: np.ndarray,
        y_true: Optional[np.ndarray] = None,
    ) -> Dict[str, Any]:
        """
        Process new data point(s).

        Args:
            X: Feature data
            y_true: Optional ground truth (for learning)

        Returns:
            Dict with prediction and metadata
        """
        X = np.atleast_2d(X)

        # Generate prediction
        y_pred = self.trainer.predict(X)

        result = {
            "timestamp": datetime.now(),
            "prediction": y_pred.tolist(),
            "model_version": self.trainer.get_model_version(),
        }

        # Update model if ground truth provided
        if y_true is not None:
            update_result = self.trainer.update(X, y_true)
            if update_result:
                result["updated"] = True
                result["new_metrics"] = update_result.new_metrics

        self._prediction_history.append(result)

        return result

    def get_prediction_history(self) -> List[Dict]:
        """Get history of predictions."""
        return self._prediction_history
