"""
Shapley Value Attribution

Game-theoretic approach to attribution using Shapley values
to fairly distribute conversion credit across channels.
"""

from dataclasses import dataclass
from itertools import combinations, permutations
from typing import Callable, Optional

import numpy as np
import pandas as pd
from collections import Counter


@dataclass
class ShapleyResult:
    """Result from Shapley value attribution."""

    # Shapley values per channel
    shapley_values: dict[str, float]

    # Normalized to sum to 1
    attribution_share: dict[str, float]

    # Channel statistics
    channel_frequency: dict[str, int]
    channel_conversion_rate: dict[str, float]

    # Computation metadata
    n_journeys: int
    n_channels: int
    computation_method: str


class ShapleyAttribution:
    """
    Shapley value attribution for marketing.

    Uses cooperative game theory to fairly allocate conversion
    credit based on each channel's marginal contribution.

    Example:
        shapley = ShapleyAttribution()
        result = shapley.calculate(journeys_df)
    """

    def __init__(
        self,
        max_channels_exact: int = 10,
        n_samples_approx: int = 1000,
        seed: Optional[int] = None,
    ):
        """
        Initialize Shapley attribution.

        Args:
            max_channels_exact: Max channels for exact computation
            n_samples_approx: Samples for approximation if too many channels
            seed: Random seed for reproducibility
        """
        self.max_channels_exact = max_channels_exact
        self.n_samples_approx = n_samples_approx
        self.seed = seed
        self._rng = np.random.default_rng(seed)

    def calculate(
        self,
        journeys_df: pd.DataFrame,
        channel_col: str = "channel",
        converted_col: str = "converted",
        journey_id_col: str = "journey_id",
    ) -> ShapleyResult:
        """
        Calculate Shapley values from journey data.

        Args:
            journeys_df: DataFrame with journey touchpoints
            channel_col: Column with channel names
            converted_col: Column with conversion flag
            journey_id_col: Column with journey IDs

        Returns:
            ShapleyResult with Shapley values
        """
        # Get unique channels
        channels = journeys_df[channel_col].unique().tolist()
        n_channels = len(channels)

        # Build conversion lookup by channel set
        conversion_rates = self._build_conversion_rates(
            journeys_df, channel_col, converted_col, journey_id_col
        )

        # Calculate Shapley values
        if n_channels <= self.max_channels_exact:
            shapley_values = self._exact_shapley(channels, conversion_rates)
            method = "exact"
        else:
            shapley_values = self._approximate_shapley(
                channels, conversion_rates, self.n_samples_approx
            )
            method = "approximate"

        # Calculate channel statistics
        channel_frequency = journeys_df[channel_col].value_counts().to_dict()

        # Conversion rate per channel
        channel_conv_rate = {}
        for channel in channels:
            channel_journeys = journeys_df[
                journeys_df[journey_id_col].isin(
                    journeys_df[journeys_df[channel_col] == channel][journey_id_col]
                )
            ].drop_duplicates(journey_id_col)
            n_total = len(channel_journeys)
            n_converted = channel_journeys[converted_col].sum()
            channel_conv_rate[channel] = n_converted / n_total if n_total > 0 else 0

        # Normalize Shapley values
        total = sum(shapley_values.values())
        attribution_share = {
            ch: v / total if total > 0 else 0
            for ch, v in shapley_values.items()
        }

        return ShapleyResult(
            shapley_values=shapley_values,
            attribution_share=attribution_share,
            channel_frequency=channel_frequency,
            channel_conversion_rate=channel_conv_rate,
            n_journeys=journeys_df[journey_id_col].nunique(),
            n_channels=n_channels,
            computation_method=method,
        )

    def _build_conversion_rates(
        self,
        df: pd.DataFrame,
        channel_col: str,
        converted_col: str,
        journey_id_col: str,
    ) -> dict[frozenset, float]:
        """Build lookup of conversion rates by channel set."""
        # Group by journey and get channels + conversion
        journey_data = df.groupby(journey_id_col).agg({
            channel_col: lambda x: frozenset(x),
            converted_col: "max",
        }).reset_index()

        # Count conversions for each channel set
        channel_sets: dict[frozenset, list[int]] = {}
        for _, row in journey_data.iterrows():
            channels = row[channel_col]
            converted = row[converted_col]
            if channels not in channel_sets:
                channel_sets[channels] = []
            channel_sets[channels].append(converted)

        # Calculate conversion rate for each set
        conversion_rates = {}
        for channels, conversions in channel_sets.items():
            conversion_rates[channels] = np.mean(conversions)

        return conversion_rates

    def _characteristic_function(
        self,
        coalition: frozenset,
        conversion_rates: dict[frozenset, float],
    ) -> float:
        """
        Characteristic function v(S) = expected conversion rate
        for journeys touching all channels in coalition S.
        """
        matching_rates = [
            rate for channels, rate in conversion_rates.items()
            if coalition.issubset(channels)
        ]

        if matching_rates:
            return np.mean(matching_rates)
        return 0.0

    def _exact_shapley(
        self,
        channels: list[str],
        conversion_rates: dict[frozenset, float],
    ) -> dict[str, float]:
        """Calculate exact Shapley values (factorial complexity)."""
        n = len(channels)
        shapley = {ch: 0.0 for ch in channels}

        for channel in channels:
            others = [ch for ch in channels if ch != channel]

            for size in range(len(others) + 1):
                for subset in combinations(others, size):
                    coalition = frozenset(subset)
                    coalition_with = coalition | {channel}

                    # Marginal contribution
                    v_with = self._characteristic_function(coalition_with, conversion_rates)
                    v_without = self._characteristic_function(coalition, conversion_rates)
                    marginal = v_with - v_without

                    # Shapley weight
                    weight = (
                        np.math.factorial(size) *
                        np.math.factorial(n - size - 1) /
                        np.math.factorial(n)
                    )

                    shapley[channel] += weight * marginal

        return shapley

    def _approximate_shapley(
        self,
        channels: list[str],
        conversion_rates: dict[frozenset, float],
        n_samples: int,
    ) -> dict[str, float]:
        """Approximate Shapley values using permutation sampling."""
        shapley = {ch: 0.0 for ch in channels}
        channel_list = list(channels)

        for _ in range(n_samples):
            # Random permutation
            perm = self._rng.permutation(channel_list)

            coalition = frozenset()
            for channel in perm:
                # Marginal contribution
                v_with = self._characteristic_function(
                    coalition | {channel}, conversion_rates
                )
                v_without = self._characteristic_function(coalition, conversion_rates)

                shapley[channel] += v_with - v_without
                coalition = coalition | {channel}

        # Average over samples
        return {ch: v / n_samples for ch, v in shapley.items()}

    def calculate_from_journeys(
        self,
        journeys: list[dict],
    ) -> ShapleyResult:
        """
        Calculate Shapley values from list of journey dicts.

        Args:
            journeys: List of dicts with 'channels' (list) and 'converted' (bool)

        Returns:
            ShapleyResult with Shapley values
        """
        # Convert to DataFrame format
        rows = []
        for i, journey in enumerate(journeys):
            for channel in journey["channels"]:
                rows.append({
                    "journey_id": i,
                    "channel": channel,
                    "converted": journey["converted"],
                })

        df = pd.DataFrame(rows)
        return self.calculate(df)


def shapley_interaction_index(
    channels: list[str],
    conversion_rates: dict[frozenset, float],
    channel_i: str,
    channel_j: str,
) -> float:
    """
    Calculate Shapley interaction index between two channels.

    Measures synergy (positive) or substitution (negative) effects.
    """
    n = len(channels)
    others = [ch for ch in channels if ch not in (channel_i, channel_j)]
    interaction = 0.0

    for size in range(len(others) + 1):
        for subset in combinations(others, size):
            coalition = frozenset(subset)

            # Calculate interaction term
            v_both = _cf(coalition | {channel_i, channel_j}, conversion_rates)
            v_i = _cf(coalition | {channel_i}, conversion_rates)
            v_j = _cf(coalition | {channel_j}, conversion_rates)
            v_neither = _cf(coalition, conversion_rates)

            delta = (v_both - v_i) - (v_j - v_neither)

            # Weight
            weight = (
                np.math.factorial(size) *
                np.math.factorial(n - size - 2) /
                np.math.factorial(n - 1)
            )

            interaction += weight * delta

    return interaction / 2


def _cf(coalition: frozenset, rates: dict[frozenset, float]) -> float:
    """Helper characteristic function."""
    matching = [r for c, r in rates.items() if coalition.issubset(c)]
    return np.mean(matching) if matching else 0.0
