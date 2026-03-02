"""ARIMA/SARIMA forecasting models."""

from dataclasses import dataclass
from typing import Any, Optional, Tuple

import numpy as np
import pandas as pd
import structlog
from numpy.typing import NDArray

logger = structlog.get_logger()


@dataclass
class ARIMAConfig:
    """Configuration for ARIMA model."""

    # ARIMA order (p, d, q)
    order: Tuple[int, int, int] = (1, 1, 1)

    # Seasonal order (P, D, Q, s)
    seasonal_order: Optional[Tuple[int, int, int, int]] = None

    # Model settings
    trend: Optional[str] = "c"  # 'n', 'c', 't', 'ct'
    enforce_stationarity: bool = True
    enforce_invertibility: bool = True

    # Auto selection
    auto_order: bool = False
    max_p: int = 5
    max_d: int = 2
    max_q: int = 5

    # Confidence interval
    confidence_level: float = 0.95


class ARIMAForecaster:
    """ARIMA/SARIMA time series forecaster."""

    def __init__(self, config: ARIMAConfig) -> None:
        """Initialize ARIMA forecaster."""
        self.config = config
        self.model = None
        self.results = None
        self.is_fitted = False
        self._training_data: Optional[pd.Series] = None

    def _auto_select_order(
        self,
        y: pd.Series,
    ) -> Tuple[Tuple[int, int, int], Optional[Tuple[int, int, int, int]]]:
        """Automatically select ARIMA order using AIC."""
        try:
            from pmdarima import auto_arima
        except ImportError:
            logger.warning("pmdarima not installed, using default order")
            return self.config.order, self.config.seasonal_order

        result = auto_arima(
            y,
            start_p=0,
            max_p=self.config.max_p,
            start_q=0,
            max_q=self.config.max_q,
            max_d=self.config.max_d,
            seasonal=self.config.seasonal_order is not None,
            m=self.config.seasonal_order[3] if self.config.seasonal_order else 1,
            trace=False,
            error_action="ignore",
            suppress_warnings=True,
            stepwise=True,
        )

        order = result.order
        seasonal_order = result.seasonal_order if hasattr(result, "seasonal_order") else None

        return order, seasonal_order

    def fit(
        self,
        data: pd.DataFrame,
        date_column: str = "date",
        target_column: str = "y",
        **kwargs: Any,
    ) -> "ARIMAForecaster":
        """Fit the ARIMA model."""
        try:
            from statsmodels.tsa.statespace.sarimax import SARIMAX
        except ImportError:
            raise ImportError("statsmodels required. Install with: pip install statsmodels")

        logger.info("Starting ARIMA training")

        # Prepare data
        df = data.copy()
        df[date_column] = pd.to_datetime(df[date_column])
        df = df.sort_values(date_column)
        y = df.set_index(date_column)[target_column]
        self._training_data = y

        # Auto-select order if configured
        order = self.config.order
        seasonal_order = self.config.seasonal_order

        if self.config.auto_order:
            order, seasonal_order = self._auto_select_order(y)
            logger.info(f"Auto-selected order: {order}, seasonal: {seasonal_order}")

        # Fit model
        self.model = SARIMAX(
            y,
            order=order,
            seasonal_order=seasonal_order or (0, 0, 0, 0),
            trend=self.config.trend,
            enforce_stationarity=self.config.enforce_stationarity,
            enforce_invertibility=self.config.enforce_invertibility,
            **kwargs,
        )

        self.results = self.model.fit(disp=False)
        self.is_fitted = True

        logger.info("ARIMA training completed", aic=self.results.aic)

        return self

    def predict(
        self,
        periods: int = 30,
        include_confidence: bool = True,
    ) -> pd.DataFrame:
        """Generate forecasts."""
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before prediction")

        # Get forecast
        forecast = self.results.get_forecast(steps=periods)
        pred = forecast.predicted_mean

        # Create result DataFrame
        last_date = self._training_data.index[-1]
        freq = pd.infer_freq(self._training_data.index) or "D"
        future_dates = pd.date_range(start=last_date, periods=periods + 1, freq=freq)[1:]

        result = pd.DataFrame(
            {
                "ds": future_dates,
                "yhat": pred.values,
            }
        )

        if include_confidence:
            conf_int = forecast.conf_int(alpha=1 - self.config.confidence_level)
            result["yhat_lower"] = conf_int.iloc[:, 0].values
            result["yhat_upper"] = conf_int.iloc[:, 1].values

        return result

    def get_diagnostics(self) -> dict[str, Any]:
        """Get model diagnostics."""
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted")

        return {
            "aic": self.results.aic,
            "bic": self.results.bic,
            "hqic": self.results.hqic,
            "llf": self.results.llf,
            "order": self.model.order,
            "seasonal_order": self.model.seasonal_order,
        }

    def save(self, path: str) -> None:
        """Save model."""
        import pickle
        with open(path, "wb") as f:
            pickle.dump({"results": self.results, "config": self.config}, f)

    @classmethod
    def load(cls, path: str) -> "ARIMAForecaster":
        """Load model."""
        import pickle
        with open(path, "rb") as f:
            data = pickle.load(f)
        instance = cls(config=data["config"])
        instance.results = data["results"]
        instance.is_fitted = True
        return instance
