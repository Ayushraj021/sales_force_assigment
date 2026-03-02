"""PyMC-Marketing integration for Bayesian Marketing Mix Modeling.

This module provides a wrapper around the pymc-marketing library for
building and training Bayesian MMM models.
"""

from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np
import pandas as pd
import structlog
from numpy.typing import NDArray

logger = structlog.get_logger()


@dataclass
class ChannelConfig:
    """Configuration for a marketing channel."""

    name: str
    spend_column: str
    adstock_type: str = "geometric"
    adstock_max_lag: int = 8
    saturation_type: str = "logistic"

    # Adstock priors
    adstock_alpha_prior: tuple[float, float] = (1.0, 3.0)  # (mean, sigma)

    # Saturation priors
    saturation_lambda_prior: tuple[float, float] = (0.5, 1.0)


@dataclass
class MMMConfig:
    """Configuration for the Marketing Mix Model."""

    target_column: str
    date_column: str
    channels: list[ChannelConfig]
    control_columns: list[str] = field(default_factory=list)

    # Model settings
    yearly_seasonality: bool = True
    weekly_seasonality: bool = False
    include_intercept: bool = True

    # Sampling settings
    n_samples: int = 2000
    n_chains: int = 4
    target_accept: float = 0.9
    random_seed: int = 42


class PyMCMarketingMixModel:
    """Bayesian Marketing Mix Model using PyMC-Marketing.

    This model estimates the contribution of each marketing channel
    to the target variable (usually revenue or conversions) while
    accounting for adstock (carryover) effects and saturation
    (diminishing returns).
    """

    def __init__(self, config: MMMConfig) -> None:
        """Initialize the MMM model.

        Args:
            config: Model configuration.
        """
        self.config = config
        self.model = None
        self.trace = None
        self.is_fitted = False
        self._data: Optional[pd.DataFrame] = None

    def _prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Prepare data for model training.

        Args:
            data: Raw input DataFrame.

        Returns:
            Preprocessed DataFrame.
        """
        df = data.copy()

        # Ensure date column is datetime
        df[self.config.date_column] = pd.to_datetime(df[self.config.date_column])
        df = df.sort_values(self.config.date_column).reset_index(drop=True)

        # Extract time index
        df["time_index"] = np.arange(len(df))

        return df

    def fit(
        self,
        data: pd.DataFrame,
        **kwargs: Any,
    ) -> "PyMCMarketingMixModel":
        """Fit the MMM model to data.

        Args:
            data: Training data with spend and target columns.
            **kwargs: Additional arguments passed to the sampler.

        Returns:
            Self for method chaining.
        """
        try:
            import pymc as pm
            import pymc_marketing.mmm as mmm
        except ImportError:
            logger.error("pymc-marketing not installed")
            raise ImportError(
                "pymc-marketing is required. Install with: pip install pymc-marketing"
            )

        logger.info(
            "Starting MMM training",
            n_channels=len(self.config.channels),
            n_samples=self.config.n_samples,
        )

        # Prepare data
        self._data = self._prepare_data(data)

        # Extract channel columns
        channel_columns = [ch.spend_column for ch in self.config.channels]

        # Build the model using pymc-marketing
        self.model = mmm.MMM(
            date_column=self.config.date_column,
            channel_columns=channel_columns,
            control_columns=self.config.control_columns if self.config.control_columns else None,
            adstock="geometric",
            saturation="logistic",
            yearly_seasonality=self.config.yearly_seasonality,
        )

        # Prepare X and y
        X = self._data[channel_columns + self.config.control_columns]
        y = self._data[self.config.target_column]

        # Fit the model
        self.model.fit(
            X=X,
            y=y,
            target_accept=self.config.target_accept,
            chains=self.config.n_chains,
            draws=self.config.n_samples,
            random_seed=self.config.random_seed,
            **kwargs,
        )

        self.is_fitted = True
        self.trace = self.model.fit_result

        logger.info("MMM training completed")

        return self

    def predict(
        self,
        data: Optional[pd.DataFrame] = None,
        include_contributions: bool = True,
    ) -> dict[str, NDArray[np.float64]]:
        """Generate predictions from the fitted model.

        Args:
            data: Data to predict on. If None, uses training data.
            include_contributions: Whether to include channel contributions.

        Returns:
            Dictionary with predictions and optionally contributions.
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before prediction")

        if data is None:
            data = self._data

        # Get channel columns
        channel_columns = [ch.spend_column for ch in self.config.channels]
        X = data[channel_columns + self.config.control_columns]

        # Generate predictions
        predictions = self.model.predict(X)

        result = {
            "predictions": predictions.mean(axis=0),
            "predictions_lower": np.percentile(predictions, 2.5, axis=0),
            "predictions_upper": np.percentile(predictions, 97.5, axis=0),
        }

        if include_contributions:
            contributions = self.get_channel_contributions()
            result["contributions"] = contributions

        return result

    def get_channel_contributions(self) -> dict[str, dict[str, float]]:
        """Get channel contribution decomposition.

        Returns:
            Dictionary mapping channel names to their contribution metrics.
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before getting contributions")

        contributions = {}

        # Get posterior means for channel effects
        for channel in self.config.channels:
            # Calculate contribution for this channel
            # This is a simplified calculation - actual implementation
            # would use the full posterior
            contribution = {
                "total_contribution": 0.0,
                "contribution_share": 0.0,
                "roi": 0.0,
                "marginal_roi": 0.0,
            }
            contributions[channel.name] = contribution

        return contributions

    def get_response_curves(
        self,
        spend_range: Optional[tuple[float, float]] = None,
        n_points: int = 100,
    ) -> dict[str, pd.DataFrame]:
        """Get response curves for each channel.

        Args:
            spend_range: Optional (min, max) spend range to evaluate.
            n_points: Number of points to evaluate.

        Returns:
            Dictionary mapping channel names to response curve DataFrames.
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before getting response curves")

        response_curves = {}

        for channel in self.config.channels:
            # Generate spend range
            if spend_range is None:
                channel_data = self._data[channel.spend_column]
                min_spend = 0
                max_spend = channel_data.max() * 1.5
            else:
                min_spend, max_spend = spend_range

            spend_values = np.linspace(min_spend, max_spend, n_points)

            # Calculate response at each spend level
            # This would use the model's saturation function
            response = np.zeros(n_points)  # Placeholder

            response_curves[channel.name] = pd.DataFrame(
                {
                    "spend": spend_values,
                    "response": response,
                }
            )

        return response_curves

    def get_model_diagnostics(self) -> dict[str, Any]:
        """Get model diagnostics and convergence metrics.

        Returns:
            Dictionary with diagnostic metrics.
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before getting diagnostics")

        try:
            import arviz as az
        except ImportError:
            return {"error": "arviz not installed"}

        # Calculate diagnostics
        diagnostics = {
            "r_hat": {},
            "ess": {},
            "divergences": 0,
        }

        if self.trace is not None:
            summary = az.summary(self.trace)
            diagnostics["r_hat"] = summary["r_hat"].to_dict()
            diagnostics["ess"] = summary["ess_bulk"].to_dict()

        return diagnostics

    def save(self, path: str) -> None:
        """Save the fitted model to disk.

        Args:
            path: Path to save the model.
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before saving")

        import pickle

        with open(path, "wb") as f:
            pickle.dump(
                {
                    "config": self.config,
                    "trace": self.trace,
                },
                f,
            )

    @classmethod
    def load(cls, path: str) -> "PyMCMarketingMixModel":
        """Load a fitted model from disk.

        Args:
            path: Path to load the model from.

        Returns:
            Loaded model instance.
        """
        import pickle

        with open(path, "rb") as f:
            data = pickle.load(f)

        model = cls(config=data["config"])
        model.trace = data["trace"]
        model.is_fitted = True

        return model
