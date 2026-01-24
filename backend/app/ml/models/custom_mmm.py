"""Custom Marketing Mix Model using Ridge/ElasticNet regression.

A simpler, frequentist approach to MMM when Bayesian methods are not needed.
"""

from dataclasses import dataclass, field
from typing import Any, Literal, Optional

import numpy as np
import pandas as pd
import structlog
from numpy.typing import NDArray
from sklearn.linear_model import Ridge, ElasticNet
from sklearn.preprocessing import StandardScaler

from app.ml.transformers.adstock import apply_adstock
from app.ml.transformers.saturation import apply_saturation

logger = structlog.get_logger()


@dataclass
class CustomMMMConfig:
    """Configuration for custom MMM model."""

    target_column: str
    date_column: str

    # Channel configurations
    channel_columns: list[str]
    adstock_params: dict[str, dict] = field(default_factory=dict)
    saturation_params: dict[str, dict] = field(default_factory=dict)

    # Control variables
    control_columns: list[str] = field(default_factory=list)

    # Model type
    model_type: Literal["ridge", "elasticnet"] = "ridge"
    alpha: float = 1.0  # Regularization strength
    l1_ratio: float = 0.5  # For ElasticNet

    # Seasonality
    include_trend: bool = True
    include_yearly_seasonality: bool = True
    yearly_fourier_terms: int = 6
    include_weekly_seasonality: bool = False
    weekly_fourier_terms: int = 3


class CustomMMMModel:
    """Custom Marketing Mix Model using Ridge or ElasticNet regression.

    This model applies adstock and saturation transformations to
    channel spend data, then uses regularized regression to estimate
    channel contributions.
    """

    def __init__(self, config: CustomMMMConfig) -> None:
        """Initialize the custom MMM model.

        Args:
            config: Model configuration.
        """
        self.config = config
        self.model = None
        self.scaler = StandardScaler()
        self.is_fitted = False
        self._feature_names: list[str] = []
        self._coefficients: dict[str, float] = {}
        self._training_data: Optional[pd.DataFrame] = None

    def _apply_transformations(
        self,
        data: pd.DataFrame,
    ) -> pd.DataFrame:
        """Apply adstock and saturation to channel columns.

        Args:
            data: Input DataFrame.

        Returns:
            DataFrame with transformed channels.
        """
        df = data.copy()

        for channel in self.config.channel_columns:
            x = df[channel].values

            # Get adstock params for this channel
            adstock_params = self.config.adstock_params.get(
                channel,
                {"adstock_type": "geometric", "decay_rate": 0.5},
            )

            # Apply adstock
            x_adstock = apply_adstock(
                x,
                adstock_type=adstock_params.get("adstock_type", "geometric"),
                max_lag=adstock_params.get("max_lag", 8),
                **{k: v for k, v in adstock_params.items() if k not in ["adstock_type", "max_lag"]},
            )

            # Get saturation params for this channel
            sat_params = self.config.saturation_params.get(
                channel,
                {"saturation_type": "hill", "alpha": 2.0, "gamma": 1.0},
            )

            # Apply saturation
            x_saturated = apply_saturation(
                x_adstock,
                saturation_type=sat_params.get("saturation_type", "hill"),
                **{k: v for k, v in sat_params.items() if k != "saturation_type"},
            )

            df[f"{channel}_transformed"] = x_saturated

        return df

    def _create_seasonality_features(
        self,
        dates: pd.Series,
    ) -> pd.DataFrame:
        """Create seasonality features.

        Args:
            dates: Series of dates.

        Returns:
            DataFrame with seasonality features.
        """
        df = pd.DataFrame(index=range(len(dates)))

        # Convert to day of year / week
        day_of_year = dates.dt.dayofyear
        day_of_week = dates.dt.dayofweek

        if self.config.include_yearly_seasonality:
            for i in range(1, self.config.yearly_fourier_terms + 1):
                df[f"yearly_sin_{i}"] = np.sin(2 * np.pi * i * day_of_year / 365.25)
                df[f"yearly_cos_{i}"] = np.cos(2 * np.pi * i * day_of_year / 365.25)

        if self.config.include_weekly_seasonality:
            for i in range(1, self.config.weekly_fourier_terms + 1):
                df[f"weekly_sin_{i}"] = np.sin(2 * np.pi * i * day_of_week / 7)
                df[f"weekly_cos_{i}"] = np.cos(2 * np.pi * i * day_of_week / 7)

        return df

    def _prepare_features(
        self,
        data: pd.DataFrame,
    ) -> NDArray[np.float64]:
        """Prepare all features for the model.

        Args:
            data: Input DataFrame.

        Returns:
            Feature matrix.
        """
        # Apply transformations
        df = self._apply_transformations(data)

        # Get transformed channel columns
        transformed_cols = [f"{ch}_transformed" for ch in self.config.channel_columns]

        # Get control columns
        control_cols = self.config.control_columns

        # Create seasonality features
        dates = pd.to_datetime(df[self.config.date_column])
        seasonality_df = self._create_seasonality_features(dates)

        # Combine all features
        feature_list = []
        self._feature_names = []

        # Transformed channels
        for col in transformed_cols:
            feature_list.append(df[col].values.reshape(-1, 1))
            self._feature_names.append(col)

        # Control variables
        for col in control_cols:
            feature_list.append(df[col].values.reshape(-1, 1))
            self._feature_names.append(col)

        # Seasonality
        for col in seasonality_df.columns:
            feature_list.append(seasonality_df[col].values.reshape(-1, 1))
            self._feature_names.append(col)

        # Trend
        if self.config.include_trend:
            t = np.arange(len(df)).reshape(-1, 1)
            t_normalized = t / len(df)
            feature_list.append(t_normalized)
            self._feature_names.append("trend")

        return np.hstack(feature_list)

    def fit(
        self,
        data: pd.DataFrame,
        **kwargs: Any,
    ) -> "CustomMMMModel":
        """Fit the model.

        Args:
            data: Training data.
            **kwargs: Additional arguments.

        Returns:
            Self for method chaining.
        """
        logger.info(
            "Starting custom MMM training",
            n_channels=len(self.config.channel_columns),
            model_type=self.config.model_type,
        )

        self._training_data = data.copy()

        # Prepare features
        X = self._prepare_features(data)
        y = data[self.config.target_column].values

        # Scale features
        X_scaled = self.scaler.fit_transform(X)

        # Create and fit model
        if self.config.model_type == "ridge":
            self.model = Ridge(alpha=self.config.alpha, **kwargs)
        else:
            self.model = ElasticNet(
                alpha=self.config.alpha,
                l1_ratio=self.config.l1_ratio,
                **kwargs,
            )

        self.model.fit(X_scaled, y)

        # Store coefficients
        self._coefficients = dict(zip(self._feature_names, self.model.coef_))
        self._coefficients["intercept"] = self.model.intercept_

        self.is_fitted = True

        logger.info("Custom MMM training completed")

        return self

    def predict(
        self,
        data: Optional[pd.DataFrame] = None,
    ) -> NDArray[np.float64]:
        """Generate predictions.

        Args:
            data: Data to predict on. Uses training data if None.

        Returns:
            Predicted values.
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before prediction")

        if data is None:
            data = self._training_data

        X = self._prepare_features(data)
        X_scaled = self.scaler.transform(X)

        return self.model.predict(X_scaled)

    def get_channel_contributions(self) -> dict[str, dict[str, float]]:
        """Get channel contribution breakdown.

        Returns:
            Dictionary with channel metrics.
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before getting contributions")

        contributions = {}
        total_contribution = 0

        # Get predictions
        predictions = self.predict()
        baseline = self._coefficients.get("intercept", 0)

        for channel in self.config.channel_columns:
            coef = self._coefficients.get(f"{channel}_transformed", 0)

            # Calculate contribution
            X = self._prepare_features(self._training_data)
            col_idx = self._feature_names.index(f"{channel}_transformed")
            channel_values = self.scaler.transform(X)[:, col_idx]
            channel_contribution = coef * channel_values.sum()

            # Calculate spend
            total_spend = self._training_data[channel].sum()

            contributions[channel] = {
                "coefficient": coef,
                "total_contribution": channel_contribution,
                "roi": channel_contribution / total_spend if total_spend > 0 else 0,
            }
            total_contribution += abs(channel_contribution)

        # Add contribution shares
        for channel in contributions:
            contributions[channel]["contribution_share"] = (
                abs(contributions[channel]["total_contribution"]) / total_contribution
                if total_contribution > 0
                else 0
            )

        return contributions

    def get_metrics(self) -> dict[str, float]:
        """Get model fit metrics.

        Returns:
            Dictionary with R², RMSE, MAE.
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before getting metrics")

        y_true = self._training_data[self.config.target_column].values
        y_pred = self.predict()

        # R²
        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - y_true.mean()) ** 2)
        r2 = 1 - (ss_res / ss_tot)

        # RMSE
        rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))

        # MAE
        mae = np.mean(np.abs(y_true - y_pred))

        # MAPE
        mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100

        return {
            "r2": r2,
            "rmse": rmse,
            "mae": mae,
            "mape": mape,
        }

    def save(self, path: str) -> None:
        """Save model to disk."""
        import pickle

        with open(path, "wb") as f:
            pickle.dump(
                {
                    "model": self.model,
                    "scaler": self.scaler,
                    "config": self.config,
                    "feature_names": self._feature_names,
                    "coefficients": self._coefficients,
                },
                f,
            )

    @classmethod
    def load(cls, path: str) -> "CustomMMMModel":
        """Load model from disk."""
        import pickle

        with open(path, "rb") as f:
            data = pickle.load(f)

        instance = cls(config=data["config"])
        instance.model = data["model"]
        instance.scaler = data["scaler"]
        instance._feature_names = data["feature_names"]
        instance._coefficients = data["coefficients"]
        instance.is_fitted = True

        return instance
