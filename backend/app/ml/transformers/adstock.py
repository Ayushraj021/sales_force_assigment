"""Adstock transformations for marketing spend carryover effects.

Adstock models the delayed and decaying effect of advertising over time.
"""

from abc import ABC, abstractmethod
from typing import Literal

import numpy as np
from numpy.typing import NDArray
from scipy.special import gammainc


class AdstockTransformer(ABC):
    """Base class for adstock transformations."""

    def __init__(self, max_lag: int = 8, normalize: bool = True) -> None:
        """Initialize adstock transformer.

        Args:
            max_lag: Maximum number of time periods for carryover effect.
            normalize: Whether to normalize weights to sum to 1.
        """
        self.max_lag = max_lag
        self.normalize = normalize

    @abstractmethod
    def get_weights(self, **params) -> NDArray[np.float64]:
        """Get adstock weights for each lag period.

        Returns:
            Array of weights for lags 0 to max_lag.
        """
        pass

    def transform(
        self,
        x: NDArray[np.float64],
        **params,
    ) -> NDArray[np.float64]:
        """Apply adstock transformation to input data.

        Args:
            x: Input array of marketing spend/impressions.
            **params: Parameters for the specific adstock model.

        Returns:
            Transformed array with carryover effects applied.
        """
        weights = self.get_weights(**params)

        if self.normalize:
            weights = weights / weights.sum()

        # Apply convolution for carryover effect
        result = np.convolve(x, weights, mode="full")[: len(x)]
        return result


class GeometricAdstock(AdstockTransformer):
    """Geometric (exponential) decay adstock.

    The most common adstock model where the effect decays exponentially.
    weight[t] = decay_rate^t
    """

    def get_weights(
        self,
        decay_rate: float = 0.5,
        **kwargs,
    ) -> NDArray[np.float64]:
        """Get geometric adstock weights.

        Args:
            decay_rate: Decay rate per period (0 < decay_rate < 1).
                       Higher values mean slower decay.

        Returns:
            Array of exponentially decaying weights.
        """
        if not 0 < decay_rate < 1:
            raise ValueError("decay_rate must be between 0 and 1")

        lags = np.arange(self.max_lag + 1)
        weights = decay_rate ** lags
        return weights

    @staticmethod
    def geometric_adstock_numpy(
        x: NDArray[np.float64],
        decay_rate: float,
    ) -> NDArray[np.float64]:
        """Apply geometric adstock using cumulative calculation.

        This is more efficient for long time series.
        """
        result = np.zeros_like(x)
        result[0] = x[0]
        for t in range(1, len(x)):
            result[t] = x[t] + decay_rate * result[t - 1]
        return result


class WeibullAdstock(AdstockTransformer):
    """Weibull distribution-based adstock.

    Allows for flexible peak timing and decay patterns.
    Useful when the maximum effect doesn't occur immediately.
    """

    def get_weights(
        self,
        shape: float = 1.0,
        scale: float = 1.0,
        **kwargs,
    ) -> NDArray[np.float64]:
        """Get Weibull adstock weights.

        Args:
            shape: Shape parameter (k). Controls peak timing.
                   k < 1: Decreasing hazard (peak at t=0)
                   k = 1: Constant hazard (exponential)
                   k > 1: Increasing then decreasing (delayed peak)
            scale: Scale parameter (lambda). Controls spread.

        Returns:
            Array of Weibull-distributed weights.
        """
        if shape <= 0 or scale <= 0:
            raise ValueError("shape and scale must be positive")

        lags = np.arange(self.max_lag + 1)

        # Weibull PDF: (k/lambda) * (t/lambda)^(k-1) * exp(-(t/lambda)^k)
        # Use CDF difference for discrete weights
        weights = np.zeros(self.max_lag + 1)
        for i, lag in enumerate(lags):
            # Probability mass in interval [lag, lag+1)
            cdf_lower = 1 - np.exp(-((lag / scale) ** shape)) if lag > 0 else 0
            cdf_upper = 1 - np.exp(-(((lag + 1) / scale) ** shape))
            weights[i] = cdf_upper - cdf_lower

        return weights


class DelayedAdstock(AdstockTransformer):
    """Delayed adstock with configurable peak timing.

    Models situations where advertising effect peaks after a delay.
    Uses a gamma distribution shape.
    """

    def get_weights(
        self,
        peak_lag: float = 2.0,
        decay_speed: float = 1.0,
        **kwargs,
    ) -> NDArray[np.float64]:
        """Get delayed adstock weights.

        Args:
            peak_lag: Expected lag for peak effect (mean of gamma).
            decay_speed: How quickly the effect decays after peak.
                        Higher values = faster decay.

        Returns:
            Array of gamma-distributed weights.
        """
        if peak_lag <= 0 or decay_speed <= 0:
            raise ValueError("peak_lag and decay_speed must be positive")

        lags = np.arange(self.max_lag + 1)

        # Use gamma distribution
        # shape (k) = peak_lag * decay_speed
        # rate = decay_speed
        shape = peak_lag * decay_speed
        rate = decay_speed

        # Gamma CDF differences for discrete weights
        weights = np.zeros(self.max_lag + 1)
        for i, lag in enumerate(lags):
            cdf_lower = gammainc(shape, rate * lag) if lag > 0 else 0
            cdf_upper = gammainc(shape, rate * (lag + 1))
            weights[i] = cdf_upper - cdf_lower

        return weights


def apply_adstock(
    x: NDArray[np.float64],
    adstock_type: Literal["geometric", "weibull", "delayed"],
    max_lag: int = 8,
    normalize: bool = True,
    **params,
) -> NDArray[np.float64]:
    """Apply adstock transformation with specified type.

    Args:
        x: Input array.
        adstock_type: Type of adstock transformation.
        max_lag: Maximum lag periods.
        normalize: Whether to normalize weights.
        **params: Parameters for the specific adstock type.

    Returns:
        Transformed array.
    """
    transformers = {
        "geometric": GeometricAdstock,
        "weibull": WeibullAdstock,
        "delayed": DelayedAdstock,
    }

    if adstock_type not in transformers:
        raise ValueError(f"Unknown adstock type: {adstock_type}")

    transformer = transformers[adstock_type](max_lag=max_lag, normalize=normalize)
    return transformer.transform(x, **params)
