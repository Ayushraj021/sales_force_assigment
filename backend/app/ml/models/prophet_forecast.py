"""Prophet-based time series forecasting.

This module provides a wrapper around Facebook Prophet for
demand and sales forecasting.
"""

from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np
import pandas as pd
import structlog
from numpy.typing import NDArray

logger = structlog.get_logger()


@dataclass
class ProphetConfig:
    """Configuration for Prophet forecasting model."""

    # Seasonality settings
    yearly_seasonality: bool | int = True
    weekly_seasonality: bool | int = True
    daily_seasonality: bool = False

    # Growth settings
    growth: str = "linear"  # 'linear' or 'logistic'
    cap: Optional[float] = None  # For logistic growth
    floor: Optional[float] = None

    # Changepoints
    n_changepoints: int = 25
    changepoint_prior_scale: float = 0.05
    changepoint_range: float = 0.8

    # Seasonality prior
    seasonality_prior_scale: float = 10.0
    seasonality_mode: str = "additive"  # 'additive' or 'multiplicative'

    # Holidays
    holidays: Optional[pd.DataFrame] = None
    holidays_prior_scale: float = 10.0

    # Uncertainty
    uncertainty_samples: int = 1000
    interval_width: float = 0.95

    # Regressors
    regressors: list[str] = field(default_factory=list)


class ProphetForecaster:
    """Prophet-based time series forecaster.

    Wrapper around Facebook Prophet with additional features
    for sales and demand forecasting.
    """

    def __init__(self, config: ProphetConfig) -> None:
        """Initialize the Prophet forecaster.

        Args:
            config: Forecaster configuration.
        """
        self.config = config
        self.model = None
        self.is_fitted = False
        self._training_data: Optional[pd.DataFrame] = None

    def _prepare_data(
        self,
        data: pd.DataFrame,
        date_column: str,
        target_column: str,
    ) -> pd.DataFrame:
        """Prepare data for Prophet.

        Prophet requires columns named 'ds' and 'y'.

        Args:
            data: Input DataFrame.
            date_column: Name of the date column.
            target_column: Name of the target column.

        Returns:
            DataFrame formatted for Prophet.
        """
        df = data.copy()

        # Rename columns for Prophet
        df = df.rename(columns={date_column: "ds", target_column: "y"})

        # Ensure ds is datetime
        df["ds"] = pd.to_datetime(df["ds"])

        # Handle logistic growth
        if self.config.growth == "logistic":
            if self.config.cap is not None:
                df["cap"] = self.config.cap
            if self.config.floor is not None:
                df["floor"] = self.config.floor

        return df

    def fit(
        self,
        data: pd.DataFrame,
        date_column: str = "date",
        target_column: str = "y",
        **kwargs: Any,
    ) -> "ProphetForecaster":
        """Fit the Prophet model.

        Args:
            data: Training data.
            date_column: Name of the date column.
            target_column: Name of the target column.
            **kwargs: Additional arguments passed to Prophet.

        Returns:
            Self for method chaining.
        """
        try:
            from prophet import Prophet
        except ImportError:
            logger.error("Prophet not installed")
            raise ImportError("Prophet is required. Install with: pip install prophet")

        logger.info("Starting Prophet training", n_rows=len(data))

        # Prepare data
        self._training_data = self._prepare_data(data, date_column, target_column)

        # Initialize Prophet model
        self.model = Prophet(
            growth=self.config.growth,
            yearly_seasonality=self.config.yearly_seasonality,
            weekly_seasonality=self.config.weekly_seasonality,
            daily_seasonality=self.config.daily_seasonality,
            n_changepoints=self.config.n_changepoints,
            changepoint_prior_scale=self.config.changepoint_prior_scale,
            changepoint_range=self.config.changepoint_range,
            seasonality_prior_scale=self.config.seasonality_prior_scale,
            seasonality_mode=self.config.seasonality_mode,
            holidays=self.config.holidays,
            holidays_prior_scale=self.config.holidays_prior_scale,
            uncertainty_samples=self.config.uncertainty_samples,
            interval_width=self.config.interval_width,
            **kwargs,
        )

        # Add regressors
        for regressor in self.config.regressors:
            self.model.add_regressor(regressor)

        # Fit the model
        self.model.fit(self._training_data)
        self.is_fitted = True

        logger.info("Prophet training completed")

        return self

    def predict(
        self,
        periods: int = 30,
        frequency: str = "D",
        future_data: Optional[pd.DataFrame] = None,
        include_history: bool = True,
    ) -> pd.DataFrame:
        """Generate forecasts.

        Args:
            periods: Number of periods to forecast.
            frequency: Frequency of predictions ('D', 'W', 'M', etc.).
            future_data: Optional DataFrame with future regressor values.
            include_history: Whether to include historical predictions.

        Returns:
            DataFrame with forecasts.
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before prediction")

        # Create future dataframe
        if future_data is not None:
            future = future_data.copy()
            future["ds"] = pd.to_datetime(future["ds"])
        else:
            future = self.model.make_future_dataframe(
                periods=periods,
                freq=frequency,
                include_history=include_history,
            )

        # Handle logistic growth
        if self.config.growth == "logistic":
            if self.config.cap is not None:
                future["cap"] = self.config.cap
            if self.config.floor is not None:
                future["floor"] = self.config.floor

        # Generate predictions
        forecast = self.model.predict(future)

        return forecast

    def predict_components(
        self,
        periods: int = 30,
        frequency: str = "D",
    ) -> pd.DataFrame:
        """Get forecast decomposition by component.

        Args:
            periods: Number of periods to forecast.
            frequency: Frequency of predictions.

        Returns:
            DataFrame with component contributions.
        """
        forecast = self.predict(periods=periods, frequency=frequency)

        # Extract components
        components = ["trend", "yhat"]

        if self.config.yearly_seasonality:
            components.append("yearly")
        if self.config.weekly_seasonality:
            components.append("weekly")
        if self.config.daily_seasonality:
            components.append("daily")

        # Add regressor components
        for regressor in self.config.regressors:
            if regressor in forecast.columns:
                components.append(regressor)

        return forecast[["ds"] + [c for c in components if c in forecast.columns]]

    def get_changepoints(self) -> pd.DataFrame:
        """Get detected changepoints.

        Returns:
            DataFrame with changepoint dates and magnitudes.
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before getting changepoints")

        changepoints = self.model.changepoints
        deltas = self.model.params["delta"].mean(axis=0)

        return pd.DataFrame(
            {
                "ds": changepoints,
                "delta": deltas[: len(changepoints)],
            }
        )

    def cross_validate(
        self,
        initial: str = "730 days",
        period: str = "180 days",
        horizon: str = "365 days",
    ) -> pd.DataFrame:
        """Perform cross-validation.

        Args:
            initial: Initial training period.
            period: Period between cutoff dates.
            horizon: Forecast horizon.

        Returns:
            DataFrame with cross-validation results.
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before cross-validation")

        from prophet.diagnostics import cross_validation, performance_metrics

        cv_results = cross_validation(
            self.model,
            initial=initial,
            period=period,
            horizon=horizon,
        )

        metrics = performance_metrics(cv_results)

        return metrics

    def get_metrics(
        self,
        cv_results: Optional[pd.DataFrame] = None,
    ) -> dict[str, float]:
        """Get forecast accuracy metrics.

        Args:
            cv_results: Optional cross-validation results.

        Returns:
            Dictionary with accuracy metrics.
        """
        if cv_results is None:
            cv_results = self.cross_validate()

        return {
            "mape": cv_results["mape"].mean(),
            "rmse": cv_results["rmse"].mean(),
            "mae": cv_results["mae"].mean(),
            "coverage": cv_results["coverage"].mean() if "coverage" in cv_results else None,
        }

    def plot_forecast(
        self,
        forecast: Optional[pd.DataFrame] = None,
        periods: int = 30,
    ) -> Any:
        """Plot the forecast.

        Args:
            forecast: Optional pre-computed forecast.
            periods: Periods to forecast if forecast not provided.

        Returns:
            Matplotlib figure.
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before plotting")

        if forecast is None:
            forecast = self.predict(periods=periods)

        return self.model.plot(forecast)

    def plot_components(
        self,
        forecast: Optional[pd.DataFrame] = None,
        periods: int = 30,
    ) -> Any:
        """Plot forecast components.

        Args:
            forecast: Optional pre-computed forecast.
            periods: Periods to forecast if forecast not provided.

        Returns:
            Matplotlib figure.
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before plotting")

        if forecast is None:
            forecast = self.predict(periods=periods)

        return self.model.plot_components(forecast)

    def save(self, path: str) -> None:
        """Save the model to disk.

        Args:
            path: Path to save the model.
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before saving")

        import pickle

        with open(path, "wb") as f:
            pickle.dump(
                {
                    "model": self.model,
                    "config": self.config,
                },
                f,
            )

    @classmethod
    def load(cls, path: str) -> "ProphetForecaster":
        """Load a model from disk.

        Args:
            path: Path to load the model from.

        Returns:
            Loaded model instance.
        """
        import pickle

        with open(path, "rb") as f:
            data = pickle.load(f)

        forecaster = cls(config=data["config"])
        forecaster.model = data["model"]
        forecaster.is_fitted = True

        return forecaster
