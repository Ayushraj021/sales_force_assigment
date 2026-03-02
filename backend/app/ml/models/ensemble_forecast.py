"""Ensemble forecasting combining multiple models."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

import numpy as np
import pandas as pd
import structlog
from numpy.typing import NDArray

logger = structlog.get_logger()


@dataclass
class EnsembleConfig:
    """Configuration for ensemble forecaster."""

    # Models to include
    models: List[str] = field(default_factory=lambda: ["prophet", "arima"])

    # Ensemble method
    method: Literal["average", "weighted", "stacking"] = "weighted"

    # Weights for weighted averaging (auto-computed if None)
    weights: Optional[Dict[str, float]] = None

    # Cross-validation settings for weight optimization
    cv_folds: int = 5
    optimize_weights: bool = True


class EnsembleForecaster:
    """Ensemble forecaster combining multiple forecasting models."""

    def __init__(self, config: EnsembleConfig) -> None:
        """Initialize ensemble forecaster."""
        self.config = config
        self.models: Dict[str, Any] = {}
        self.weights: Dict[str, float] = {}
        self.is_fitted = False
        self._training_data: Optional[pd.DataFrame] = None

    def _create_model(self, model_type: str) -> Any:
        """Create a model instance by type."""
        from app.ml.models.prophet_forecast import ProphetForecaster, ProphetConfig
        from app.ml.models.arima_forecast import ARIMAForecaster, ARIMAConfig

        if model_type == "prophet":
            return ProphetForecaster(ProphetConfig())
        elif model_type == "arima":
            return ARIMAForecaster(ARIMAConfig(auto_order=True))
        else:
            raise ValueError(f"Unknown model type: {model_type}")

    def _compute_weights(
        self,
        data: pd.DataFrame,
        date_column: str,
        target_column: str,
    ) -> Dict[str, float]:
        """Compute optimal weights using cross-validation."""
        from sklearn.model_selection import TimeSeriesSplit

        n = len(data)
        tscv = TimeSeriesSplit(n_splits=self.config.cv_folds)

        model_errors: Dict[str, List[float]] = {m: [] for m in self.config.models}

        for train_idx, val_idx in tscv.split(data):
            train_data = data.iloc[train_idx]
            val_data = data.iloc[val_idx]

            for model_type in self.config.models:
                try:
                    model = self._create_model(model_type)
                    model.fit(train_data, date_column=date_column, target_column=target_column)

                    # Predict on validation set
                    predictions = model.predict(periods=len(val_idx))

                    # Calculate RMSE
                    y_true = val_data[target_column].values
                    y_pred = predictions["yhat"].values[: len(y_true)]

                    rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))
                    model_errors[model_type].append(rmse)

                except Exception as e:
                    logger.warning(f"Model {model_type} failed in CV: {e}")
                    model_errors[model_type].append(np.inf)

        # Compute weights inversely proportional to error
        avg_errors = {m: np.mean(errors) for m, errors in model_errors.items()}
        total_inv_error = sum(1 / e for e in avg_errors.values() if e < np.inf)

        weights = {}
        for model, error in avg_errors.items():
            if error < np.inf:
                weights[model] = (1 / error) / total_inv_error
            else:
                weights[model] = 0

        return weights

    def fit(
        self,
        data: pd.DataFrame,
        date_column: str = "date",
        target_column: str = "y",
        **kwargs: Any,
    ) -> "EnsembleForecaster":
        """Fit all models in the ensemble."""
        logger.info(
            "Starting ensemble training",
            models=self.config.models,
            method=self.config.method,
        )

        self._training_data = data.copy()

        # Fit individual models
        for model_type in self.config.models:
            try:
                model = self._create_model(model_type)
                model.fit(data, date_column=date_column, target_column=target_column, **kwargs)
                self.models[model_type] = model
                logger.info(f"Trained {model_type} model")
            except Exception as e:
                logger.error(f"Failed to train {model_type}: {e}")

        # Compute weights
        if self.config.method == "weighted":
            if self.config.weights:
                self.weights = self.config.weights
            elif self.config.optimize_weights:
                self.weights = self._compute_weights(data, date_column, target_column)
            else:
                # Equal weights
                n_models = len(self.models)
                self.weights = {m: 1 / n_models for m in self.models}

        self.is_fitted = True
        logger.info("Ensemble training completed", weights=self.weights)

        return self

    def predict(
        self,
        periods: int = 30,
        include_individual: bool = False,
    ) -> pd.DataFrame:
        """Generate ensemble forecast."""
        if not self.is_fitted:
            raise RuntimeError("Ensemble must be fitted before prediction")

        predictions: Dict[str, pd.DataFrame] = {}

        # Get predictions from each model
        for model_type, model in self.models.items():
            try:
                pred = model.predict(periods=periods)
                predictions[model_type] = pred
            except Exception as e:
                logger.warning(f"Prediction failed for {model_type}: {e}")

        if not predictions:
            raise RuntimeError("All models failed to predict")

        # Combine predictions
        result = predictions[list(predictions.keys())[0]][["ds"]].copy()

        if self.config.method == "average":
            # Simple average
            result["yhat"] = np.mean(
                [pred["yhat"].values for pred in predictions.values()],
                axis=0,
            )
        elif self.config.method == "weighted":
            # Weighted average
            weighted_preds = []
            total_weight = 0
            for model_type, pred in predictions.items():
                weight = self.weights.get(model_type, 0)
                weighted_preds.append(pred["yhat"].values * weight)
                total_weight += weight

            result["yhat"] = np.sum(weighted_preds, axis=0) / total_weight
        else:
            # Default to average
            result["yhat"] = np.mean(
                [pred["yhat"].values for pred in predictions.values()],
                axis=0,
            )

        # Add confidence intervals (using prediction spread)
        all_preds = np.array([pred["yhat"].values for pred in predictions.values()])
        result["yhat_lower"] = np.percentile(all_preds, 2.5, axis=0)
        result["yhat_upper"] = np.percentile(all_preds, 97.5, axis=0)

        # Add individual predictions if requested
        if include_individual:
            for model_type, pred in predictions.items():
                result[f"yhat_{model_type}"] = pred["yhat"].values

        return result

    def get_model_weights(self) -> Dict[str, float]:
        """Get model weights."""
        return self.weights.copy()

    def save(self, path: str) -> None:
        """Save ensemble."""
        import pickle

        # Save model weights and config only
        with open(path, "wb") as f:
            pickle.dump(
                {
                    "config": self.config,
                    "weights": self.weights,
                },
                f,
            )

    @classmethod
    def load(cls, path: str) -> "EnsembleForecaster":
        """Load ensemble (requires refitting models)."""
        import pickle

        with open(path, "rb") as f:
            data = pickle.load(f)

        instance = cls(config=data["config"])
        instance.weights = data["weights"]
        # Note: Individual models need to be refit

        return instance
