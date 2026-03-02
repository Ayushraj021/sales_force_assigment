"""Saturation curve transformations for diminishing returns.

Saturation models the diminishing returns of marketing spend at higher levels.
"""

from abc import ABC, abstractmethod
from typing import Literal

import numpy as np
from numpy.typing import NDArray


class SaturationTransformer(ABC):
    """Base class for saturation transformations."""

    @abstractmethod
    def transform(
        self,
        x: NDArray[np.float64],
        **params,
    ) -> NDArray[np.float64]:
        """Apply saturation transformation.

        Args:
            x: Input array (typically adstock-transformed spend).
            **params: Parameters for the specific saturation model.

        Returns:
            Transformed array with saturation applied.
        """
        pass

    @abstractmethod
    def inverse_transform(
        self,
        y: NDArray[np.float64],
        **params,
    ) -> NDArray[np.float64]:
        """Inverse saturation transformation.

        Args:
            y: Saturated values.
            **params: Parameters for the specific saturation model.

        Returns:
            Original values before saturation.
        """
        pass


class HillSaturation(SaturationTransformer):
    """Hill function (sigmoid) saturation curve.

    The most common saturation model in MMM.
    y = x^alpha / (gamma^alpha + x^alpha)

    This produces an S-curve (or sigmoid) response.
    """

    def transform(
        self,
        x: NDArray[np.float64],
        alpha: float = 2.0,
        gamma: float = 1.0,
        **kwargs,
    ) -> NDArray[np.float64]:
        """Apply Hill saturation.

        Args:
            x: Input array (must be non-negative).
            alpha: Steepness/slope parameter. Controls how quickly
                   saturation occurs. Higher values = steeper curve.
            gamma: Inflection point / half-saturation point.
                   The x value at which y = 0.5.

        Returns:
            Saturated values between 0 and 1.
        """
        if alpha <= 0:
            raise ValueError("alpha must be positive")
        if gamma <= 0:
            raise ValueError("gamma must be positive")

        x_safe = np.maximum(x, 0)  # Ensure non-negative
        x_alpha = x_safe ** alpha
        gamma_alpha = gamma ** alpha

        return x_alpha / (gamma_alpha + x_alpha)

    def inverse_transform(
        self,
        y: NDArray[np.float64],
        alpha: float = 2.0,
        gamma: float = 1.0,
        **kwargs,
    ) -> NDArray[np.float64]:
        """Inverse Hill saturation."""
        y_safe = np.clip(y, 1e-10, 1 - 1e-10)  # Avoid division by zero
        return gamma * (y_safe / (1 - y_safe)) ** (1 / alpha)

    def marginal_response(
        self,
        x: NDArray[np.float64],
        alpha: float = 2.0,
        gamma: float = 1.0,
    ) -> NDArray[np.float64]:
        """Calculate marginal response (derivative of Hill function).

        This is useful for calculating marginal ROI.
        """
        x_safe = np.maximum(x, 1e-10)
        gamma_alpha = gamma ** alpha
        x_alpha = x_safe ** alpha

        # Derivative: alpha * gamma^alpha * x^(alpha-1) / (gamma^alpha + x^alpha)^2
        numerator = alpha * gamma_alpha * (x_safe ** (alpha - 1))
        denominator = (gamma_alpha + x_alpha) ** 2

        return numerator / denominator


class LogisticSaturation(SaturationTransformer):
    """Logistic (S-curve) saturation.

    y = k / (1 + exp(-s * (x - m)))

    Where k is the carrying capacity, s is steepness, and m is midpoint.
    """

    def transform(
        self,
        x: NDArray[np.float64],
        k: float = 1.0,
        s: float = 1.0,
        m: float = 0.0,
        **kwargs,
    ) -> NDArray[np.float64]:
        """Apply logistic saturation.

        Args:
            x: Input array.
            k: Carrying capacity / maximum value.
            s: Steepness of the curve.
            m: Midpoint (x value where y = k/2).

        Returns:
            Saturated values between 0 and k.
        """
        if k <= 0:
            raise ValueError("k (carrying capacity) must be positive")
        if s <= 0:
            raise ValueError("s (steepness) must be positive")

        return k / (1 + np.exp(-s * (x - m)))

    def inverse_transform(
        self,
        y: NDArray[np.float64],
        k: float = 1.0,
        s: float = 1.0,
        m: float = 0.0,
        **kwargs,
    ) -> NDArray[np.float64]:
        """Inverse logistic saturation."""
        y_safe = np.clip(y, 1e-10, k - 1e-10)
        return m - (1 / s) * np.log(k / y_safe - 1)


class MichaelisMentenSaturation(SaturationTransformer):
    """Michaelis-Menten saturation curve.

    Originally from enzyme kinetics, commonly used in marketing.
    y = (Vmax * x) / (Km + x)

    This is actually equivalent to Hill with alpha=1.
    """

    def transform(
        self,
        x: NDArray[np.float64],
        vmax: float = 1.0,
        km: float = 1.0,
        **kwargs,
    ) -> NDArray[np.float64]:
        """Apply Michaelis-Menten saturation.

        Args:
            x: Input array (must be non-negative).
            vmax: Maximum rate / saturation level.
            km: Michaelis constant (x value at half-max).

        Returns:
            Saturated values between 0 and vmax.
        """
        if vmax <= 0:
            raise ValueError("vmax must be positive")
        if km <= 0:
            raise ValueError("km must be positive")

        x_safe = np.maximum(x, 0)
        return (vmax * x_safe) / (km + x_safe)

    def inverse_transform(
        self,
        y: NDArray[np.float64],
        vmax: float = 1.0,
        km: float = 1.0,
        **kwargs,
    ) -> NDArray[np.float64]:
        """Inverse Michaelis-Menten saturation."""
        y_safe = np.clip(y, 0, vmax - 1e-10)
        return (km * y_safe) / (vmax - y_safe)


def apply_saturation(
    x: NDArray[np.float64],
    saturation_type: Literal["hill", "logistic", "michaelis_menten"],
    **params,
) -> NDArray[np.float64]:
    """Apply saturation transformation with specified type.

    Args:
        x: Input array.
        saturation_type: Type of saturation curve.
        **params: Parameters for the specific saturation type.

    Returns:
        Transformed array.
    """
    transformers = {
        "hill": HillSaturation(),
        "logistic": LogisticSaturation(),
        "michaelis_menten": MichaelisMentenSaturation(),
    }

    if saturation_type not in transformers:
        raise ValueError(f"Unknown saturation type: {saturation_type}")

    return transformers[saturation_type].transform(x, **params)


def calculate_marginal_roi(
    x: NDArray[np.float64],
    saturation_type: Literal["hill", "logistic", "michaelis_menten"],
    **params,
) -> NDArray[np.float64]:
    """Calculate marginal ROI at each spend level.

    This is the derivative of the saturation curve, which tells us
    how much additional response we get for an additional unit of spend.

    Args:
        x: Spend levels.
        saturation_type: Type of saturation curve.
        **params: Parameters for the saturation curve.

    Returns:
        Marginal response at each spend level.
    """
    # Use numerical differentiation for simplicity
    epsilon = 1e-6
    y1 = apply_saturation(x, saturation_type, **params)
    y2 = apply_saturation(x + epsilon, saturation_type, **params)
    return (y2 - y1) / epsilon
