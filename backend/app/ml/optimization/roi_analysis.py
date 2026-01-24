"""ROI and marginal ROI analysis."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import structlog
from numpy.typing import NDArray

logger = structlog.get_logger()


@dataclass
class ChannelROI:
    """ROI metrics for a channel."""

    channel_name: str
    total_spend: float
    total_contribution: float
    roi: float
    marginal_roi: float
    saturation_level: float  # 0-1, how saturated the channel is


class ROIAnalyzer:
    """Analyzer for ROI and marginal ROI calculations."""

    def __init__(
        self,
        response_params: Dict[str, Dict[str, float]],
    ) -> None:
        """Initialize ROI analyzer.

        Args:
            response_params: Dictionary mapping channel names to response
                           function parameters (alpha, gamma, coefficient).
        """
        self.response_params = response_params

    def calculate_response(
        self,
        channel: str,
        spend: float,
    ) -> float:
        """Calculate response for a given spend level.

        Uses Hill saturation curve.
        """
        from app.ml.transformers.saturation import HillSaturation

        params = self.response_params.get(channel, {})
        alpha = params.get("alpha", 2.0)
        gamma = params.get("gamma", 1.0)
        coefficient = params.get("coefficient", 1.0)

        saturation = HillSaturation()
        saturated = saturation.transform(np.array([spend]), alpha=alpha, gamma=gamma)[0]

        return coefficient * saturated

    def calculate_marginal_response(
        self,
        channel: str,
        spend: float,
        delta: float = 1.0,
    ) -> float:
        """Calculate marginal response (derivative) at a spend level.

        Args:
            channel: Channel name.
            spend: Current spend level.
            delta: Small increment for numerical derivative.

        Returns:
            Marginal response (additional response per additional unit of spend).
        """
        response_at_spend = self.calculate_response(channel, spend)
        response_at_spend_plus = self.calculate_response(channel, spend + delta)

        return (response_at_spend_plus - response_at_spend) / delta

    def calculate_channel_roi(
        self,
        channel: str,
        spend: float,
    ) -> ChannelROI:
        """Calculate full ROI metrics for a channel.

        Args:
            channel: Channel name.
            spend: Spend amount.

        Returns:
            ChannelROI object with all metrics.
        """
        contribution = self.calculate_response(channel, spend)
        marginal_roi = self.calculate_marginal_response(channel, spend)

        # Calculate saturation level
        params = self.response_params.get(channel, {})
        gamma = params.get("gamma", 1.0)
        alpha = params.get("alpha", 2.0)

        # Saturation level: how close to asymptote
        # At spend = gamma, saturation = 0.5 (for Hill curve)
        saturation_level = (spend ** alpha) / (gamma ** alpha + spend ** alpha)

        return ChannelROI(
            channel_name=channel,
            total_spend=spend,
            total_contribution=contribution,
            roi=contribution / spend if spend > 0 else 0,
            marginal_roi=marginal_roi,
            saturation_level=saturation_level,
        )

    def analyze_all_channels(
        self,
        spend_by_channel: Dict[str, float],
    ) -> Dict[str, ChannelROI]:
        """Analyze ROI for all channels.

        Args:
            spend_by_channel: Dictionary mapping channel names to spend.

        Returns:
            Dictionary mapping channel names to ChannelROI objects.
        """
        results = {}
        for channel, spend in spend_by_channel.items():
            results[channel] = self.calculate_channel_roi(channel, spend)
        return results

    def get_optimal_reallocation(
        self,
        spend_by_channel: Dict[str, float],
        reallocation_amount: float,
    ) -> Dict[str, float]:
        """Find optimal reallocation of budget based on marginal ROI.

        Move budget from channels with low marginal ROI to channels
        with high marginal ROI.

        Args:
            spend_by_channel: Current spend allocation.
            reallocation_amount: Amount to reallocate.

        Returns:
            New spend allocation.
        """
        # Calculate marginal ROI for all channels
        marginal_rois = {}
        for channel, spend in spend_by_channel.items():
            marginal_rois[channel] = self.calculate_marginal_response(channel, spend)

        # Sort by marginal ROI
        sorted_channels = sorted(marginal_rois.items(), key=lambda x: x[1], reverse=True)

        # Find channels to reduce (low marginal ROI) and increase (high marginal ROI)
        new_allocation = spend_by_channel.copy()

        # Simple reallocation: take from lowest, give to highest
        if len(sorted_channels) >= 2:
            highest_channel = sorted_channels[0][0]
            lowest_channel = sorted_channels[-1][0]

            # Don't go negative
            actual_reallocation = min(reallocation_amount, new_allocation[lowest_channel])

            new_allocation[lowest_channel] -= actual_reallocation
            new_allocation[highest_channel] += actual_reallocation

        return new_allocation

    def generate_response_curve(
        self,
        channel: str,
        max_spend: float,
        n_points: int = 100,
    ) -> pd.DataFrame:
        """Generate response curve data for a channel.

        Args:
            channel: Channel name.
            max_spend: Maximum spend to evaluate.
            n_points: Number of points on the curve.

        Returns:
            DataFrame with spend, response, ROI, and marginal ROI.
        """
        spend_values = np.linspace(0, max_spend, n_points)

        data = []
        for spend in spend_values:
            if spend > 0:
                response = self.calculate_response(channel, spend)
                marginal = self.calculate_marginal_response(channel, spend)
                data.append(
                    {
                        "spend": spend,
                        "response": response,
                        "roi": response / spend,
                        "marginal_roi": marginal,
                    }
                )

        return pd.DataFrame(data)

    def find_optimal_spend(
        self,
        channel: str,
        target_marginal_roi: float = 1.0,
        max_spend: float = 1000000,
    ) -> float:
        """Find optimal spend level where marginal ROI equals target.

        Args:
            channel: Channel name.
            target_marginal_roi: Target marginal ROI (default 1.0 = break-even).
            max_spend: Maximum spend to consider.

        Returns:
            Optimal spend level.
        """
        from scipy.optimize import brentq

        def objective(spend: float) -> float:
            return self.calculate_marginal_response(channel, spend) - target_marginal_roi

        try:
            # Find where marginal ROI equals target
            optimal = brentq(objective, 1, max_spend)
            return optimal
        except ValueError:
            # If no solution in range, return max or 0
            if self.calculate_marginal_response(channel, 1) < target_marginal_roi:
                return 0
            return max_spend

    def calculate_incremental_contribution(
        self,
        channel: str,
        current_spend: float,
        additional_spend: float,
    ) -> Dict[str, float]:
        """Calculate incremental contribution from additional spend.

        Args:
            channel: Channel name.
            current_spend: Current spend level.
            additional_spend: Additional spend to evaluate.

        Returns:
            Dictionary with incremental metrics.
        """
        current_response = self.calculate_response(channel, current_spend)
        new_response = self.calculate_response(channel, current_spend + additional_spend)

        incremental_response = new_response - current_response
        incremental_roi = incremental_response / additional_spend if additional_spend > 0 else 0

        return {
            "current_spend": current_spend,
            "additional_spend": additional_spend,
            "current_response": current_response,
            "new_response": new_response,
            "incremental_response": incremental_response,
            "incremental_roi": incremental_roi,
        }
