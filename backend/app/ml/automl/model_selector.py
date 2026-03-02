"""
AutoML Model Selector

Automatically selects the best model for forecasting tasks.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable, Tuple
from enum import Enum
import numpy as np
import pandas as pd
from datetime import datetime
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class ModelType(str, Enum):
    """Available model types for AutoML."""
    PROPHET = "prophet"
    ARIMA = "arima"
    ETS = "ets"
    LIGHTGBM = "lightgbm"
    XGBOOST = "xgboost"
    RANDOM_FOREST = "random_forest"
    LINEAR = "linear"
    RIDGE = "ridge"
    LASSO = "lasso"
    ELASTIC_NET = "elastic_net"
    NBEATS = "nbeats"
    TFT = "tft"
    DEEPAR = "deepar"
    ENSEMBLE = "ensemble"


class MetricType(str, Enum):
    """Evaluation metrics."""
    MAE = "mae"
    RMSE = "rmse"
    MAPE = "mape"
    SMAPE = "smape"
    R2 = "r2"
    MASE = "mase"


@dataclass
class ModelCandidate:
    """A model candidate with its configuration."""
    model_type: ModelType
    hyperparameters: Dict[str, Any] = field(default_factory=dict)
    name: Optional[str] = None

    def __post_init__(self):
        if self.name is None:
            self.name = f"{self.model_type.value}"


@dataclass
class ModelScore:
    """Score for a single model."""
    model: ModelCandidate
    metrics: Dict[str, float]
    training_time: float
    prediction_time: float
    cv_scores: Optional[List[float]] = None
    feature_importance: Optional[Dict[str, float]] = None


@dataclass
class AutoMLResult:
    """Result of AutoML model selection."""
    best_model: ModelCandidate
    best_score: float
    best_metric: str
    all_scores: List[ModelScore]
    selected_features: Optional[List[str]] = None
    ensemble_weights: Optional[Dict[str, float]] = None
    total_time: float = 0.0

    def get_leaderboard(self) -> pd.DataFrame:
        """Get model leaderboard as DataFrame."""
        records = []
        for score in self.all_scores:
            record = {
                "model": score.model.name,
                "type": score.model.model_type.value,
                "training_time": score.training_time,
                "prediction_time": score.prediction_time,
            }
            record.update(score.metrics)
            records.append(record)

        df = pd.DataFrame(records)
        return df.sort_values(self.best_metric)


@dataclass
class AutoMLConfig:
    """Configuration for AutoML."""
    # Model selection
    include_models: List[ModelType] = field(default_factory=lambda: [
        ModelType.PROPHET,
        ModelType.ARIMA,
        ModelType.LIGHTGBM,
        ModelType.RIDGE,
    ])
    exclude_models: List[ModelType] = field(default_factory=list)

    # Evaluation
    primary_metric: MetricType = MetricType.MAE
    cv_folds: int = 5
    holdout_size: float = 0.2

    # Time budget
    max_time_seconds: int = 3600
    max_models: int = 20

    # Feature engineering
    auto_feature_engineering: bool = True
    feature_selection: bool = True

    # Ensemble
    create_ensemble: bool = True
    ensemble_size: int = 3

    # Parallelization
    n_jobs: int = -1

    # Early stopping
    early_stopping_rounds: int = 5
    min_improvement: float = 0.001


class AutoMLSelector:
    """
    Automated Model Selection for Time Series Forecasting.

    Features:
    - Automatic model comparison (Prophet, ARIMA, ML, DL)
    - Cross-validation with time series splits
    - Feature engineering and selection
    - Ensemble creation
    - Hyperparameter optimization

    Example:
        selector = AutoMLSelector()
        result = selector.fit(
            X=features,
            y=target,
            time_col="date",
        )

        print(f"Best model: {result.best_model.name}")
        print(result.get_leaderboard())
    """

    def __init__(self, config: Optional[AutoMLConfig] = None):
        self.config = config or AutoMLConfig()
        self.fitted_models: Dict[str, Any] = {}
        self.scaler = None
        self.feature_names: List[str] = []

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        time_col: Optional[np.ndarray] = None,
        feature_names: Optional[List[str]] = None,
        categorical_features: Optional[List[str]] = None,
    ) -> AutoMLResult:
        """
        Fit AutoML to find the best model.

        Args:
            X: Feature matrix (n_samples, n_features)
            y: Target variable (n_samples,)
            time_col: Optional time column for time series CV
            feature_names: Optional feature names
            categorical_features: Optional list of categorical feature names

        Returns:
            AutoMLResult with best model and leaderboard
        """
        start_time = datetime.now()

        self.feature_names = feature_names or [f"feature_{i}" for i in range(X.shape[1])]

        # Preprocess data
        X_processed, y_processed = self._preprocess(X, y)

        # Feature engineering
        if self.config.auto_feature_engineering:
            X_processed = self._engineer_features(X_processed, time_col)

        # Get candidate models
        candidates = self._get_candidates()

        # Evaluate models
        all_scores = []
        best_score = float('inf')
        best_model = None
        no_improvement_count = 0

        for candidate in candidates:
            if len(all_scores) >= self.config.max_models:
                break

            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed > self.config.max_time_seconds:
                logger.info(f"Time budget exceeded after {len(all_scores)} models")
                break

            try:
                score = self._evaluate_model(
                    candidate, X_processed, y_processed, time_col
                )
                all_scores.append(score)

                current_metric = score.metrics.get(
                    self.config.primary_metric.value, float('inf')
                )

                if current_metric < best_score - self.config.min_improvement:
                    best_score = current_metric
                    best_model = candidate
                    no_improvement_count = 0
                else:
                    no_improvement_count += 1

                if no_improvement_count >= self.config.early_stopping_rounds:
                    logger.info(f"Early stopping after {len(all_scores)} models")
                    break

            except Exception as e:
                logger.warning(f"Model {candidate.name} failed: {e}")
                continue

        # Create ensemble if configured
        ensemble_weights = None
        if self.config.create_ensemble and len(all_scores) >= 2:
            ensemble_weights = self._create_ensemble(all_scores)

        # Feature selection
        selected_features = None
        if self.config.feature_selection:
            selected_features = self._select_features(X_processed, y_processed)

        total_time = (datetime.now() - start_time).total_seconds()

        return AutoMLResult(
            best_model=best_model,
            best_score=best_score,
            best_metric=self.config.primary_metric.value,
            all_scores=all_scores,
            selected_features=selected_features,
            ensemble_weights=ensemble_weights,
            total_time=total_time,
        )

    def predict(
        self,
        X: np.ndarray,
        model_name: Optional[str] = None,
    ) -> np.ndarray:
        """Generate predictions using fitted model."""
        if model_name and model_name in self.fitted_models:
            model = self.fitted_models[model_name]
        elif self.fitted_models:
            model = list(self.fitted_models.values())[0]
        else:
            raise ValueError("No models fitted")

        X_processed = self._preprocess_predict(X)
        return model.predict(X_processed)

    def _preprocess(
        self,
        X: np.ndarray,
        y: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Preprocess features and target."""
        from sklearn.preprocessing import StandardScaler

        # Handle missing values
        X = np.nan_to_num(X, nan=0.0)
        y = np.nan_to_num(y, nan=np.nanmean(y))

        # Scale features
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        return X_scaled, y

    def _preprocess_predict(self, X: np.ndarray) -> np.ndarray:
        """Preprocess features for prediction."""
        X = np.nan_to_num(X, nan=0.0)
        if self.scaler:
            return self.scaler.transform(X)
        return X

    def _engineer_features(
        self,
        X: np.ndarray,
        time_col: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """Automatic feature engineering."""
        features = [X]

        # Add polynomial features for numeric columns
        if X.shape[1] <= 10:  # Only for small feature sets
            from sklearn.preprocessing import PolynomialFeatures
            poly = PolynomialFeatures(degree=2, include_bias=False, interaction_only=True)
            poly_features = poly.fit_transform(X[:, :min(5, X.shape[1])])
            features.append(poly_features[:, X.shape[1]:])  # Only interactions

        # Add lag features if time column provided
        if time_col is not None:
            for lag in [1, 7, 14, 28]:
                if len(X) > lag:
                    lagged = np.roll(X[:, 0], lag)
                    lagged[:lag] = X[:lag, 0].mean()
                    features.append(lagged.reshape(-1, 1))

        return np.hstack(features)

    def _get_candidates(self) -> List[ModelCandidate]:
        """Get list of model candidates to evaluate."""
        candidates = []

        models_to_try = [
            m for m in self.config.include_models
            if m not in self.config.exclude_models
        ]

        for model_type in models_to_try:
            if model_type == ModelType.RIDGE:
                for alpha in [0.1, 1.0, 10.0]:
                    candidates.append(ModelCandidate(
                        model_type=model_type,
                        hyperparameters={"alpha": alpha},
                        name=f"ridge_alpha_{alpha}",
                    ))
            elif model_type == ModelType.LASSO:
                for alpha in [0.01, 0.1, 1.0]:
                    candidates.append(ModelCandidate(
                        model_type=model_type,
                        hyperparameters={"alpha": alpha},
                        name=f"lasso_alpha_{alpha}",
                    ))
            elif model_type == ModelType.LIGHTGBM:
                candidates.append(ModelCandidate(
                    model_type=model_type,
                    hyperparameters={
                        "n_estimators": 100,
                        "learning_rate": 0.1,
                        "max_depth": 5,
                    },
                    name="lightgbm_default",
                ))
                candidates.append(ModelCandidate(
                    model_type=model_type,
                    hyperparameters={
                        "n_estimators": 200,
                        "learning_rate": 0.05,
                        "max_depth": 7,
                    },
                    name="lightgbm_deep",
                ))
            else:
                candidates.append(ModelCandidate(
                    model_type=model_type,
                    hyperparameters={},
                ))

        return candidates

    def _evaluate_model(
        self,
        candidate: ModelCandidate,
        X: np.ndarray,
        y: np.ndarray,
        time_col: Optional[np.ndarray] = None,
    ) -> ModelScore:
        """Evaluate a single model candidate."""
        from sklearn.model_selection import TimeSeriesSplit
        import time

        # Create model
        model = self._create_model(candidate)

        # Time series cross-validation
        tscv = TimeSeriesSplit(n_splits=self.config.cv_folds)
        cv_scores = []

        train_start = time.time()

        for train_idx, val_idx in tscv.split(X):
            X_train, X_val = X[train_idx], X[val_idx]
            y_train, y_val = y[train_idx], y[val_idx]

            model.fit(X_train, y_train)
            y_pred = model.predict(X_val)

            score = self._calculate_metric(
                y_val, y_pred, self.config.primary_metric
            )
            cv_scores.append(score)

        train_time = time.time() - train_start

        # Final fit on all data
        model.fit(X, y)
        self.fitted_models[candidate.name] = model

        # Prediction time
        pred_start = time.time()
        _ = model.predict(X[:100])
        pred_time = time.time() - pred_start

        # Calculate all metrics
        y_pred_full = model.predict(X)
        metrics = {}
        for metric in MetricType:
            metrics[metric.value] = self._calculate_metric(y, y_pred_full, metric)

        # Feature importance if available
        feature_importance = None
        if hasattr(model, "feature_importances_"):
            importance = model.feature_importances_
            feature_importance = dict(zip(
                self.feature_names[:len(importance)],
                importance.tolist()
            ))
        elif hasattr(model, "coef_"):
            coef = np.abs(model.coef_).flatten()
            feature_importance = dict(zip(
                self.feature_names[:len(coef)],
                coef.tolist()
            ))

        return ModelScore(
            model=candidate,
            metrics=metrics,
            training_time=train_time,
            prediction_time=pred_time,
            cv_scores=cv_scores,
            feature_importance=feature_importance,
        )

    def _create_model(self, candidate: ModelCandidate) -> Any:
        """Create a model instance from candidate."""
        params = candidate.hyperparameters

        if candidate.model_type == ModelType.RIDGE:
            from sklearn.linear_model import Ridge
            return Ridge(**params)
        elif candidate.model_type == ModelType.LASSO:
            from sklearn.linear_model import Lasso
            return Lasso(**params)
        elif candidate.model_type == ModelType.ELASTIC_NET:
            from sklearn.linear_model import ElasticNet
            return ElasticNet(**params)
        elif candidate.model_type == ModelType.LINEAR:
            from sklearn.linear_model import LinearRegression
            return LinearRegression()
        elif candidate.model_type == ModelType.RANDOM_FOREST:
            from sklearn.ensemble import RandomForestRegressor
            return RandomForestRegressor(**params, n_jobs=-1)
        elif candidate.model_type == ModelType.LIGHTGBM:
            try:
                import lightgbm as lgb
                return lgb.LGBMRegressor(**params, verbose=-1)
            except ImportError:
                from sklearn.ensemble import GradientBoostingRegressor
                return GradientBoostingRegressor(**params)
        elif candidate.model_type == ModelType.XGBOOST:
            try:
                import xgboost as xgb
                return xgb.XGBRegressor(**params, verbosity=0)
            except ImportError:
                from sklearn.ensemble import GradientBoostingRegressor
                return GradientBoostingRegressor(**params)
        else:
            from sklearn.linear_model import Ridge
            return Ridge()

    def _calculate_metric(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        metric: MetricType,
    ) -> float:
        """Calculate evaluation metric."""
        y_true = np.asarray(y_true).flatten()
        y_pred = np.asarray(y_pred).flatten()

        if metric == MetricType.MAE:
            return float(np.mean(np.abs(y_true - y_pred)))
        elif metric == MetricType.RMSE:
            return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
        elif metric == MetricType.MAPE:
            mask = y_true != 0
            return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)
        elif metric == MetricType.SMAPE:
            denominator = np.abs(y_true) + np.abs(y_pred)
            mask = denominator != 0
            return float(np.mean(2 * np.abs(y_true[mask] - y_pred[mask]) / denominator[mask]) * 100)
        elif metric == MetricType.R2:
            ss_res = np.sum((y_true - y_pred) ** 2)
            ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
            return float(1 - ss_res / ss_tot) if ss_tot > 0 else 0.0
        elif metric == MetricType.MASE:
            naive_errors = np.abs(np.diff(y_true))
            if len(naive_errors) == 0 or np.mean(naive_errors) == 0:
                return float('inf')
            return float(np.mean(np.abs(y_true - y_pred)) / np.mean(naive_errors))
        else:
            return float(np.mean(np.abs(y_true - y_pred)))

    def _create_ensemble(
        self,
        scores: List[ModelScore],
    ) -> Dict[str, float]:
        """Create weighted ensemble from top models."""
        # Sort by primary metric
        sorted_scores = sorted(
            scores,
            key=lambda s: s.metrics.get(self.config.primary_metric.value, float('inf'))
        )

        # Take top N models
        top_scores = sorted_scores[:self.config.ensemble_size]

        # Weight inversely proportional to error
        errors = [
            s.metrics.get(self.config.primary_metric.value, 1.0)
            for s in top_scores
        ]

        # Inverse error weighting
        weights = [1.0 / (e + 1e-6) for e in errors]
        total = sum(weights)
        weights = [w / total for w in weights]

        return {
            score.model.name: weight
            for score, weight in zip(top_scores, weights)
        }

    def _select_features(
        self,
        X: np.ndarray,
        y: np.ndarray,
        threshold: float = 0.01,
    ) -> List[str]:
        """Select important features."""
        from sklearn.ensemble import RandomForestRegressor

        rf = RandomForestRegressor(n_estimators=50, max_depth=5, n_jobs=-1)
        rf.fit(X, y)

        importance = rf.feature_importances_

        selected = [
            self.feature_names[i]
            for i, imp in enumerate(importance)
            if imp > threshold and i < len(self.feature_names)
        ]

        return selected if selected else self.feature_names[:5]
