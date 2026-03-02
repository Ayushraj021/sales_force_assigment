"""
Multi-Touch Attribution Models

Implements various position-based and rule-based attribution models
for distributing conversion credit across marketing touchpoints.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

import numpy as np
import pandas as pd


class AttributionModel(str, Enum):
    """Available attribution models."""

    FIRST_TOUCH = "first_touch"
    LAST_TOUCH = "last_touch"
    LINEAR = "linear"
    TIME_DECAY = "time_decay"
    POSITION_BASED = "position_based"  # U-shaped
    CUSTOM_POSITION = "custom_position"


@dataclass
class TouchpointData:
    """Represents a customer journey with touchpoints."""

    journey_id: str
    customer_id: str
    touchpoints: list[dict]  # List of {channel, timestamp, ...}
    converted: bool
    conversion_value: float = 0.0
    conversion_timestamp: Optional[datetime] = None


@dataclass
class AttributionResult:
    """Result from attribution analysis."""

    # Per-channel attribution
    channel_attribution: dict[str, float]
    channel_conversions: dict[str, float]
    channel_touchpoints: dict[str, int]

    # Model metadata
    model: AttributionModel
    total_conversions: int
    total_value: float

    # Journey-level details (optional)
    journey_attributions: Optional[list[dict]] = None


@dataclass
class PositionWeights:
    """Custom position weights for attribution."""

    first: float = 0.4
    last: float = 0.4
    middle: float = 0.2


class MultiTouchAttribution:
    """
    Multi-Touch Attribution engine.

    Supports various attribution models for distributing conversion
    credit across customer journey touchpoints.

    Example:
        mta = MultiTouchAttribution()
        result = mta.attribute(
            journeys=journey_data,
            model=AttributionModel.POSITION_BASED
        )
    """

    def __init__(
        self,
        lookback_window_days: int = 30,
        time_decay_half_life: float = 7.0,
        position_weights: Optional[PositionWeights] = None,
    ):
        """
        Initialize MTA engine.

        Args:
            lookback_window_days: Maximum days before conversion to include
            time_decay_half_life: Half-life for time decay model (days)
            position_weights: Custom weights for position-based model
        """
        self.lookback_window_days = lookback_window_days
        self.time_decay_half_life = time_decay_half_life
        self.position_weights = position_weights or PositionWeights()

    def attribute(
        self,
        journeys: list[TouchpointData],
        model: AttributionModel = AttributionModel.LINEAR,
        include_journey_details: bool = False,
    ) -> AttributionResult:
        """
        Run attribution on customer journeys.

        Args:
            journeys: List of customer journeys with touchpoints
            model: Attribution model to use
            include_journey_details: Whether to include journey-level attribution

        Returns:
            AttributionResult with channel-level attribution
        """
        # Filter to converted journeys
        converted_journeys = [j for j in journeys if j.converted]

        channel_attribution: dict[str, float] = {}
        channel_conversions: dict[str, float] = {}
        channel_touchpoints: dict[str, int] = {}
        journey_attributions = [] if include_journey_details else None

        for journey in converted_journeys:
            # Get touchpoints within lookback window
            touchpoints = self._filter_touchpoints(journey)

            if not touchpoints:
                continue

            # Calculate attribution weights
            weights = self._calculate_weights(touchpoints, model)

            # Distribute value
            for tp, weight in zip(touchpoints, weights):
                channel = tp["channel"]
                attributed_value = weight * journey.conversion_value

                channel_attribution[channel] = channel_attribution.get(channel, 0) + attributed_value
                channel_conversions[channel] = channel_conversions.get(channel, 0) + weight
                channel_touchpoints[channel] = channel_touchpoints.get(channel, 0) + 1

            if include_journey_details:
                journey_attributions.append({
                    "journey_id": journey.journey_id,
                    "touchpoints": [
                        {"channel": tp["channel"], "weight": w}
                        for tp, w in zip(touchpoints, weights)
                    ],
                    "conversion_value": journey.conversion_value,
                })

        return AttributionResult(
            channel_attribution=channel_attribution,
            channel_conversions=channel_conversions,
            channel_touchpoints=channel_touchpoints,
            model=model,
            total_conversions=len(converted_journeys),
            total_value=sum(j.conversion_value for j in converted_journeys),
            journey_attributions=journey_attributions,
        )

    def _filter_touchpoints(self, journey: TouchpointData) -> list[dict]:
        """Filter touchpoints within lookback window."""
        if not journey.conversion_timestamp or not journey.touchpoints:
            return journey.touchpoints

        cutoff = journey.conversion_timestamp - pd.Timedelta(days=self.lookback_window_days)

        filtered = []
        for tp in journey.touchpoints:
            tp_time = tp.get("timestamp")
            if tp_time is None or tp_time >= cutoff:
                filtered.append(tp)

        return filtered

    def _calculate_weights(
        self, touchpoints: list[dict], model: AttributionModel
    ) -> list[float]:
        """Calculate attribution weights for touchpoints."""
        n = len(touchpoints)

        if n == 0:
            return []

        if model == AttributionModel.FIRST_TOUCH:
            weights = [1.0] + [0.0] * (n - 1)

        elif model == AttributionModel.LAST_TOUCH:
            weights = [0.0] * (n - 1) + [1.0]

        elif model == AttributionModel.LINEAR:
            weights = [1.0 / n] * n

        elif model == AttributionModel.TIME_DECAY:
            weights = self._time_decay_weights(touchpoints)

        elif model == AttributionModel.POSITION_BASED:
            weights = self._position_based_weights(n)

        elif model == AttributionModel.CUSTOM_POSITION:
            weights = self._custom_position_weights(n)

        else:
            raise ValueError(f"Unknown model: {model}")

        # Normalize to sum to 1
        total = sum(weights)
        if total > 0:
            weights = [w / total for w in weights]

        return weights

    def _time_decay_weights(self, touchpoints: list[dict]) -> list[float]:
        """Calculate time decay weights based on recency."""
        if not touchpoints:
            return []

        # Get timestamps
        timestamps = []
        for tp in touchpoints:
            ts = tp.get("timestamp")
            if ts is None:
                ts = datetime.now()
            timestamps.append(ts)

        # Calculate days from most recent
        most_recent = max(timestamps)
        days_ago = [(most_recent - ts).days for ts in timestamps]

        # Exponential decay
        decay_rate = np.log(2) / self.time_decay_half_life
        weights = [np.exp(-decay_rate * d) for d in days_ago]

        return weights

    def _position_based_weights(self, n: int) -> list[float]:
        """Calculate U-shaped position-based weights."""
        if n == 1:
            return [1.0]

        if n == 2:
            return [0.5, 0.5]

        # First and last get 40%, middle shares remaining 20%
        first_weight = 0.4
        last_weight = 0.4
        middle_total = 0.2
        middle_each = middle_total / (n - 2)

        weights = [first_weight]
        weights.extend([middle_each] * (n - 2))
        weights.append(last_weight)

        return weights

    def _custom_position_weights(self, n: int) -> list[float]:
        """Calculate custom position weights."""
        if n == 1:
            return [1.0]

        if n == 2:
            total = self.position_weights.first + self.position_weights.last
            return [
                self.position_weights.first / total,
                self.position_weights.last / total,
            ]

        # Distribute middle weight evenly
        middle_each = self.position_weights.middle / (n - 2)

        weights = [self.position_weights.first]
        weights.extend([middle_each] * (n - 2))
        weights.append(self.position_weights.last)

        # Normalize
        total = sum(weights)
        return [w / total for w in weights]

    def compare_models(
        self, journeys: list[TouchpointData]
    ) -> dict[str, AttributionResult]:
        """
        Compare attribution across all models.

        Args:
            journeys: List of customer journeys

        Returns:
            Dict of model name to AttributionResult
        """
        results = {}
        for model in AttributionModel:
            results[model.value] = self.attribute(journeys, model)
        return results

    def calculate_roas(
        self, attribution: AttributionResult, channel_spend: dict[str, float]
    ) -> dict[str, float]:
        """
        Calculate Return on Ad Spend by channel.

        Args:
            attribution: Attribution result
            channel_spend: Spend by channel

        Returns:
            ROAS by channel
        """
        roas = {}
        for channel, value in attribution.channel_attribution.items():
            spend = channel_spend.get(channel, 0)
            if spend > 0:
                roas[channel] = value / spend
            else:
                roas[channel] = float("inf") if value > 0 else 0

        return roas


def journeys_from_dataframe(
    df: pd.DataFrame,
    journey_id_col: str = "journey_id",
    customer_id_col: str = "customer_id",
    channel_col: str = "channel",
    timestamp_col: str = "timestamp",
    converted_col: str = "converted",
    value_col: str = "conversion_value",
) -> list[TouchpointData]:
    """
    Convert DataFrame to list of TouchpointData.

    Args:
        df: DataFrame with touchpoint data
        journey_id_col: Column with journey IDs
        customer_id_col: Column with customer IDs
        channel_col: Column with channel names
        timestamp_col: Column with timestamps
        converted_col: Column with conversion flag
        value_col: Column with conversion value

    Returns:
        List of TouchpointData objects
    """
    journeys = []

    for journey_id, group in df.groupby(journey_id_col):
        touchpoints = []
        for _, row in group.sort_values(timestamp_col).iterrows():
            touchpoints.append({
                "channel": row[channel_col],
                "timestamp": row[timestamp_col],
            })

        # Get conversion info from last row
        last_row = group.iloc[-1]

        journeys.append(TouchpointData(
            journey_id=str(journey_id),
            customer_id=str(last_row[customer_id_col]),
            touchpoints=touchpoints,
            converted=bool(last_row[converted_col]),
            conversion_value=float(last_row.get(value_col, 0)),
            conversion_timestamp=last_row[timestamp_col] if last_row[converted_col] else None,
        ))

    return journeys
