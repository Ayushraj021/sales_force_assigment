"""Seasonality and trend decomposition transformers."""

from typing import Literal, Optional

import numpy as np
import pandas as pd
from numpy.typing import NDArray


class SeasonalityTransformer:
    """Seasonality feature generator using Fourier series.

    Creates sine and cosine features to capture periodic patterns.
    """

    def __init__(
        self,
        period: int,
        n_fourier_terms: int = 3,
    ) -> None:
        """Initialize seasonality transformer.

        Args:
            period: Length of the seasonal cycle (e.g., 7 for weekly, 365 for yearly).
            n_fourier_terms: Number of Fourier terms (sine/cosine pairs).
        """
        self.period = period
        self.n_fourier_terms = n_fourier_terms

    def transform(self, t: NDArray[np.int64]) -> NDArray[np.float64]:
        """Generate Fourier features for given time indices.

        Args:
            t: Array of time indices (0, 1, 2, ...).

        Returns:
            Array of shape (len(t), 2 * n_fourier_terms) with Fourier features.
        """
        features = []

        for i in range(1, self.n_fourier_terms + 1):
            # Sine and cosine for each Fourier order
            sin_feature = np.sin(2 * np.pi * i * t / self.period)
            cos_feature = np.cos(2 * np.pi * i * t / self.period)
            features.extend([sin_feature, cos_feature])

        return np.column_stack(features)

    def get_feature_names(self) -> list[str]:
        """Get feature names for the Fourier features."""
        names = []
        for i in range(1, self.n_fourier_terms + 1):
            names.extend([f"sin_{self.period}_{i}", f"cos_{self.period}_{i}"])
        return names


class MultiSeasonalityTransformer:
    """Multiple seasonality feature generator.

    Combines multiple seasonal patterns (e.g., weekly + yearly).
    """

    def __init__(
        self,
        seasonalities: list[dict],
    ) -> None:
        """Initialize multi-seasonality transformer.

        Args:
            seasonalities: List of dicts with 'period' and 'n_fourier_terms'.
                          e.g., [{'period': 7, 'n_fourier_terms': 3},
                                 {'period': 365, 'n_fourier_terms': 10}]
        """
        self.transformers = [
            SeasonalityTransformer(
                period=s["period"],
                n_fourier_terms=s.get("n_fourier_terms", 3),
            )
            for s in seasonalities
        ]

    def transform(self, t: NDArray[np.int64]) -> NDArray[np.float64]:
        """Generate all seasonality features."""
        all_features = [transformer.transform(t) for transformer in self.transformers]
        return np.hstack(all_features)

    def get_feature_names(self) -> list[str]:
        """Get all feature names."""
        names = []
        for transformer in self.transformers:
            names.extend(transformer.get_feature_names())
        return names


class HolidayTransformer:
    """Holiday effect transformer.

    Creates binary or weighted features for holidays.
    """

    def __init__(
        self,
        holidays: pd.DataFrame,
        holiday_effects_window: int = 3,
    ) -> None:
        """Initialize holiday transformer.

        Args:
            holidays: DataFrame with columns ['ds', 'holiday', 'lower_window', 'upper_window'].
            holiday_effects_window: Default window around holidays to include.
        """
        self.holidays = holidays
        self.holiday_effects_window = holiday_effects_window

    def transform(
        self,
        dates: pd.DatetimeIndex,
    ) -> pd.DataFrame:
        """Generate holiday features.

        Args:
            dates: DatetimeIndex to generate features for.

        Returns:
            DataFrame with holiday indicator columns.
        """
        result = pd.DataFrame(index=dates)

        for _, row in self.holidays.iterrows():
            holiday_name = row["holiday"]
            holiday_date = pd.to_datetime(row["ds"])
            lower_window = row.get("lower_window", -self.holiday_effects_window)
            upper_window = row.get("upper_window", self.holiday_effects_window)

            # Create feature column
            feature = np.zeros(len(dates))

            for i, d in enumerate(dates):
                days_diff = (d - holiday_date).days
                if lower_window <= days_diff <= upper_window:
                    # Weight by distance from holiday
                    weight = 1.0 - abs(days_diff) / (max(abs(lower_window), abs(upper_window)) + 1)
                    feature[i] = max(feature[i], weight)

            result[f"holiday_{holiday_name}"] = feature

        return result


class TrendTransformer:
    """Trend component transformer.

    Creates features for different types of trends.
    """

    def __init__(
        self,
        trend_type: Literal["linear", "logistic", "flat"] = "linear",
        changepoints: Optional[list[int]] = None,
        n_changepoints: int = 25,
    ) -> None:
        """Initialize trend transformer.

        Args:
            trend_type: Type of trend ('linear', 'logistic', 'flat').
            changepoints: Specific changepoint locations (indices).
            n_changepoints: Number of automatic changepoints if not specified.
        """
        self.trend_type = trend_type
        self.changepoints = changepoints
        self.n_changepoints = n_changepoints

    def transform(
        self,
        t: NDArray[np.int64],
        cap: Optional[float] = None,
    ) -> NDArray[np.float64]:
        """Generate trend features.

        Args:
            t: Time indices.
            cap: Carrying capacity for logistic trend.

        Returns:
            Trend feature array.
        """
        n = len(t)

        if self.trend_type == "flat":
            return np.ones((n, 1))

        elif self.trend_type == "linear":
            # Normalized time
            t_normalized = (t - t.min()) / (t.max() - t.min() + 1)
            features = [t_normalized]

            # Add changepoint features
            if self.changepoints is None:
                # Auto-detect changepoints
                changepoints = np.linspace(0, n - 1, self.n_changepoints + 2)[1:-1].astype(int)
            else:
                changepoints = self.changepoints

            for cp in changepoints:
                # Piecewise linear feature
                cp_feature = np.maximum(0, t - cp)
                features.append(cp_feature)

            return np.column_stack(features)

        elif self.trend_type == "logistic":
            if cap is None:
                raise ValueError("cap is required for logistic trend")

            t_normalized = (t - t.min()) / (t.max() - t.min() + 1)
            # Logistic growth
            k = 1  # Growth rate (to be fitted)
            m = 0.5  # Midpoint
            trend = cap / (1 + np.exp(-k * (t_normalized - m)))
            return trend.reshape(-1, 1)

        else:
            raise ValueError(f"Unknown trend type: {self.trend_type}")


def decompose_time_series(
    y: NDArray[np.float64],
    period: int,
    model: Literal["additive", "multiplicative"] = "additive",
) -> dict[str, NDArray[np.float64]]:
    """Decompose time series into trend, seasonal, and residual components.

    Uses a simple moving average decomposition.

    Args:
        y: Time series values.
        period: Seasonal period.
        model: 'additive' or 'multiplicative'.

    Returns:
        Dictionary with 'trend', 'seasonal', 'residual' components.
    """
    from scipy.ndimage import uniform_filter1d

    n = len(y)

    # Extract trend using moving average
    trend = uniform_filter1d(y, size=period, mode="nearest")

    # Detrend
    if model == "additive":
        detrended = y - trend
    else:
        detrended = y / np.where(trend != 0, trend, 1)

    # Calculate seasonal component (average for each period position)
    seasonal = np.zeros(n)
    for i in range(period):
        indices = np.arange(i, n, period)
        seasonal_mean = np.mean(detrended[indices])
        seasonal[indices] = seasonal_mean

    # Calculate residual
    if model == "additive":
        residual = y - trend - seasonal
    else:
        residual = y / (trend * seasonal + 1e-10)

    return {
        "trend": trend,
        "seasonal": seasonal,
        "residual": residual,
    }
