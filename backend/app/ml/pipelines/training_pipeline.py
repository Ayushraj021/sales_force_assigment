"""
Training Pipeline

End-to-end model training pipeline.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class TrainingConfig:
    """Training pipeline configuration."""
    model_type: str = "linear"
    test_size: float = 0.2
    validation_size: float = 0.1
    random_state: int = 42
    cross_validation_folds: int = 5
    early_stopping: bool = True
    early_stopping_rounds: int = 10
    hyperparameter_tuning: bool = False
    n_trials: int = 50


@dataclass
class TrainingResult:
    """Training pipeline result."""
    model: Any = None
    train_metrics: Dict[str, float] = field(default_factory=dict)
    validation_metrics: Dict[str, float] = field(default_factory=dict)
    test_metrics: Dict[str, float] = field(default_factory=dict)
    feature_importance: Optional[Dict[str, float]] = None
    training_time_seconds: float = 0.0
    hyperparameters: Dict[str, Any] = field(default_factory=dict)
    cv_scores: List[float] = field(default_factory=list)


class TrainingPipeline:
    """
    Model Training Pipeline.

    Features:
    - Data preprocessing
    - Model training
    - Hyperparameter tuning
    - Cross-validation
    - Evaluation

    Example:
        pipeline = TrainingPipeline(config)
        result = pipeline.run(X, y)
    """

    def __init__(self, config: Optional[TrainingConfig] = None):
        self.config = config or TrainingConfig()

    def run(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: Optional[List[str]] = None,
    ) -> TrainingResult:
        """
        Run the training pipeline.

        Args:
            X: Feature matrix
            y: Target vector
            feature_names: Feature names

        Returns:
            TrainingResult
        """
        import time
        start_time = time.time()

        # Split data
        X_train, X_val, X_test, y_train, y_val, y_test = self._split_data(X, y)

        # Get model
        model = self._get_model()

        # Hyperparameter tuning
        if self.config.hyperparameter_tuning:
            model = self._tune_hyperparameters(model, X_train, y_train, X_val, y_val)

        # Train model
        model.fit(X_train, y_train)

        # Evaluate
        train_metrics = self._evaluate(model, X_train, y_train)
        val_metrics = self._evaluate(model, X_val, y_val)
        test_metrics = self._evaluate(model, X_test, y_test)

        # Cross-validation
        cv_scores = self._cross_validate(model, X_train, y_train)

        # Feature importance
        feature_importance = self._get_feature_importance(model, feature_names)

        training_time = time.time() - start_time

        return TrainingResult(
            model=model,
            train_metrics=train_metrics,
            validation_metrics=val_metrics,
            test_metrics=test_metrics,
            feature_importance=feature_importance,
            training_time_seconds=training_time,
            hyperparameters=self._get_hyperparameters(model),
            cv_scores=cv_scores,
        )

    def _split_data(self, X: np.ndarray, y: np.ndarray):
        """Split data into train/val/test."""
        from sklearn.model_selection import train_test_split

        # First split: train+val vs test
        X_temp, X_test, y_temp, y_test = train_test_split(
            X, y,
            test_size=self.config.test_size,
            random_state=self.config.random_state,
        )

        # Second split: train vs val
        val_ratio = self.config.validation_size / (1 - self.config.test_size)
        X_train, X_val, y_train, y_val = train_test_split(
            X_temp, y_temp,
            test_size=val_ratio,
            random_state=self.config.random_state,
        )

        return X_train, X_val, X_test, y_train, y_val, y_test

    def _get_model(self):
        """Get model instance."""
        model_types = {
            "linear": "sklearn.linear_model.Ridge",
            "random_forest": "sklearn.ensemble.RandomForestRegressor",
            "gradient_boosting": "sklearn.ensemble.GradientBoostingRegressor",
            "xgboost": "xgboost.XGBRegressor",
            "lightgbm": "lightgbm.LGBMRegressor",
        }

        model_path = model_types.get(self.config.model_type, "sklearn.linear_model.Ridge")

        try:
            module_path, class_name = model_path.rsplit(".", 1)
            import importlib
            module = importlib.import_module(module_path)
            model_class = getattr(module, class_name)
            return model_class()
        except Exception as e:
            logger.warning(f"Could not load {model_path}: {e}, using Ridge")
            from sklearn.linear_model import Ridge
            return Ridge()

    def _tune_hyperparameters(self, model, X_train, y_train, X_val, y_val):
        """Tune hyperparameters using Optuna."""
        try:
            import optuna

            def objective(trial):
                # Get hyperparameters based on model type
                if "Ridge" in type(model).__name__:
                    alpha = trial.suggest_float("alpha", 0.01, 10.0, log=True)
                    model.set_params(alpha=alpha)
                elif "RandomForest" in type(model).__name__:
                    n_estimators = trial.suggest_int("n_estimators", 10, 200)
                    max_depth = trial.suggest_int("max_depth", 3, 15)
                    model.set_params(n_estimators=n_estimators, max_depth=max_depth)

                model.fit(X_train, y_train)
                y_pred = model.predict(X_val)
                mse = np.mean((y_val - y_pred) ** 2)
                return mse

            study = optuna.create_study(direction="minimize")
            study.optimize(objective, n_trials=self.config.n_trials, show_progress_bar=False)

            # Set best params
            model.set_params(**study.best_params)

        except ImportError:
            logger.warning("Optuna not available, skipping hyperparameter tuning")

        return model

    def _evaluate(self, model, X, y) -> Dict[str, float]:
        """Evaluate model."""
        y_pred = model.predict(X)

        errors = y - y_pred
        abs_errors = np.abs(errors)

        return {
            "mse": float(np.mean(errors ** 2)),
            "rmse": float(np.sqrt(np.mean(errors ** 2))),
            "mae": float(np.mean(abs_errors)),
            "r2": float(1 - np.sum(errors ** 2) / np.sum((y - np.mean(y)) ** 2)),
        }

    def _cross_validate(self, model, X, y) -> List[float]:
        """Perform cross-validation."""
        from sklearn.model_selection import cross_val_score

        scores = cross_val_score(
            model, X, y,
            cv=self.config.cross_validation_folds,
            scoring="neg_mean_squared_error",
        )
        return (-scores).tolist()

    def _get_feature_importance(
        self,
        model,
        feature_names: Optional[List[str]],
    ) -> Optional[Dict[str, float]]:
        """Extract feature importance."""
        if feature_names is None:
            return None

        importance = None
        if hasattr(model, "feature_importances_"):
            importance = model.feature_importances_
        elif hasattr(model, "coef_"):
            importance = np.abs(model.coef_)

        if importance is not None:
            return dict(zip(feature_names, importance.tolist()))
        return None

    def _get_hyperparameters(self, model) -> Dict[str, Any]:
        """Get model hyperparameters."""
        if hasattr(model, "get_params"):
            return model.get_params()
        return {}
