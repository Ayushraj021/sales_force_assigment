"""
Markov Chain Attribution

Probabilistic attribution model based on Markov chains
to model customer journey state transitions.
"""

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
from collections import defaultdict


@dataclass
class TransitionMatrix:
    """Markov transition matrix representation."""

    matrix: np.ndarray
    states: list[str]
    state_to_idx: dict[str, int]

    def get_probability(self, from_state: str, to_state: str) -> float:
        """Get transition probability between states."""
        i = self.state_to_idx.get(from_state)
        j = self.state_to_idx.get(to_state)
        if i is None or j is None:
            return 0.0
        return self.matrix[i, j]

    def to_dataframe(self) -> pd.DataFrame:
        """Convert to labeled DataFrame."""
        return pd.DataFrame(
            self.matrix,
            index=self.states,
            columns=self.states,
        )


@dataclass
class MarkovResult:
    """Result from Markov chain attribution."""

    # Attribution values (removal effect)
    channel_attribution: dict[str, float]

    # Normalized attribution share
    attribution_share: dict[str, float]

    # Transition probabilities
    transition_matrix: TransitionMatrix

    # Conversion probabilities
    total_conversion_rate: float
    channel_conversion_rates: dict[str, float]

    # Model metadata
    n_journeys: int
    n_channels: int


class MarkovAttribution:
    """
    Markov Chain Attribution Model.

    Models customer journeys as Markov chains and calculates
    channel importance based on removal effect.

    Example:
        markov = MarkovAttribution()
        result = markov.calculate(journeys_df)
    """

    # Special states
    START_STATE = "(start)"
    CONVERSION_STATE = "(conversion)"
    NULL_STATE = "(null)"

    def __init__(
        self,
        order: int = 1,
        min_transitions: int = 1,
    ):
        """
        Initialize Markov attribution.

        Args:
            order: Markov chain order (1 = first-order)
            min_transitions: Minimum transitions to include channel
        """
        self.order = order
        self.min_transitions = min_transitions

    def calculate(
        self,
        journeys_df: pd.DataFrame,
        channel_col: str = "channel",
        converted_col: str = "converted",
        journey_id_col: str = "journey_id",
    ) -> MarkovResult:
        """
        Calculate Markov chain attribution.

        Args:
            journeys_df: DataFrame with journey touchpoints
            channel_col: Column with channel names
            converted_col: Column with conversion flag
            journey_id_col: Column with journey IDs

        Returns:
            MarkovResult with attribution values
        """
        # Build transition counts
        transitions = self._count_transitions(
            journeys_df, channel_col, converted_col, journey_id_col
        )

        # Get unique channels (excluding special states)
        channels = [
            ch for ch in set(
                list(transitions.keys()) +
                [to_state for from_trans in transitions.values() for to_state in from_trans]
            )
            if ch not in (self.START_STATE, self.CONVERSION_STATE, self.NULL_STATE)
        ]

        # Build transition matrix
        all_states = [self.START_STATE] + sorted(channels) + [self.CONVERSION_STATE, self.NULL_STATE]
        trans_matrix = self._build_transition_matrix(transitions, all_states)

        # Calculate total conversion probability
        total_conv_prob = self._calculate_conversion_probability(trans_matrix)

        # Calculate removal effect for each channel
        channel_attribution = {}
        channel_conv_rates = {}

        for channel in channels:
            # Probability without this channel
            prob_without = self._calculate_removal_effect(
                trans_matrix, channel
            )

            # Removal effect = baseline - probability without channel
            removal_effect = total_conv_prob - prob_without
            channel_attribution[channel] = max(0, removal_effect)

            # Individual channel conversion rate
            channel_conv_rates[channel] = self._channel_conversion_rate(
                journeys_df, channel, channel_col, converted_col, journey_id_col
            )

        # Normalize attribution
        total_attr = sum(channel_attribution.values())
        attribution_share = {
            ch: v / total_attr if total_attr > 0 else 0
            for ch, v in channel_attribution.items()
        }

        return MarkovResult(
            channel_attribution=channel_attribution,
            attribution_share=attribution_share,
            transition_matrix=trans_matrix,
            total_conversion_rate=total_conv_prob,
            channel_conversion_rates=channel_conv_rates,
            n_journeys=journeys_df[journey_id_col].nunique(),
            n_channels=len(channels),
        )

    def _count_transitions(
        self,
        df: pd.DataFrame,
        channel_col: str,
        converted_col: str,
        journey_id_col: str,
    ) -> dict[str, dict[str, int]]:
        """Count state transitions from journey data."""
        transitions: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        for journey_id, group in df.groupby(journey_id_col):
            # Sort by timestamp if available
            journey = group.sort_index()
            channels = journey[channel_col].tolist()
            converted = journey[converted_col].iloc[-1]

            # Add start transition
            if channels:
                transitions[self.START_STATE][channels[0]] += 1

            # Add channel-to-channel transitions
            for i in range(len(channels) - 1):
                from_ch = channels[i]
                to_ch = channels[i + 1]
                transitions[from_ch][to_ch] += 1

            # Add final transition
            if channels:
                last_channel = channels[-1]
                if converted:
                    transitions[last_channel][self.CONVERSION_STATE] += 1
                else:
                    transitions[last_channel][self.NULL_STATE] += 1

        return dict(transitions)

    def _build_transition_matrix(
        self,
        transitions: dict[str, dict[str, int]],
        states: list[str],
    ) -> TransitionMatrix:
        """Build normalized transition probability matrix."""
        n = len(states)
        state_to_idx = {s: i for i, s in enumerate(states)}
        matrix = np.zeros((n, n))

        for from_state, to_states in transitions.items():
            if from_state not in state_to_idx:
                continue

            i = state_to_idx[from_state]
            total = sum(to_states.values())

            for to_state, count in to_states.items():
                if to_state not in state_to_idx:
                    continue
                j = state_to_idx[to_state]
                matrix[i, j] = count / total if total > 0 else 0

        # Absorbing states (conversion, null)
        conv_idx = state_to_idx[self.CONVERSION_STATE]
        null_idx = state_to_idx[self.NULL_STATE]
        matrix[conv_idx, conv_idx] = 1.0
        matrix[null_idx, null_idx] = 1.0

        return TransitionMatrix(
            matrix=matrix,
            states=states,
            state_to_idx=state_to_idx,
        )

    def _calculate_conversion_probability(
        self, trans_matrix: TransitionMatrix
    ) -> float:
        """Calculate probability of conversion from start state."""
        return self._absorption_probability(
            trans_matrix,
            self.START_STATE,
            self.CONVERSION_STATE,
        )

    def _absorption_probability(
        self,
        trans_matrix: TransitionMatrix,
        start_state: str,
        absorbing_state: str,
        max_steps: int = 1000,
    ) -> float:
        """Calculate absorption probability using matrix powers."""
        P = trans_matrix.matrix
        states = trans_matrix.states
        state_to_idx = trans_matrix.state_to_idx

        start_idx = state_to_idx[start_state]
        absorb_idx = state_to_idx[absorbing_state]

        # Create distribution starting from start state
        dist = np.zeros(len(states))
        dist[start_idx] = 1.0

        # Iterate until convergence
        prob = 0.0
        for _ in range(max_steps):
            dist = dist @ P
            new_prob = dist[absorb_idx]
            if abs(new_prob - prob) < 1e-10:
                break
            prob = new_prob

        return prob

    def _calculate_removal_effect(
        self,
        trans_matrix: TransitionMatrix,
        channel: str,
    ) -> float:
        """Calculate conversion probability with channel removed."""
        # Create modified transition matrix
        P_mod = trans_matrix.matrix.copy()
        states = trans_matrix.states
        state_to_idx = trans_matrix.state_to_idx

        if channel not in state_to_idx:
            return self._calculate_conversion_probability(trans_matrix)

        ch_idx = state_to_idx[channel]
        null_idx = state_to_idx[self.NULL_STATE]

        # Redirect all transitions TO this channel to null
        for i in range(len(states)):
            if P_mod[i, ch_idx] > 0:
                P_mod[i, null_idx] += P_mod[i, ch_idx]
                P_mod[i, ch_idx] = 0

        # Create temporary transition matrix
        temp_matrix = TransitionMatrix(
            matrix=P_mod,
            states=states,
            state_to_idx=state_to_idx,
        )

        return self._absorption_probability(
            temp_matrix,
            self.START_STATE,
            self.CONVERSION_STATE,
        )

    def _channel_conversion_rate(
        self,
        df: pd.DataFrame,
        channel: str,
        channel_col: str,
        converted_col: str,
        journey_id_col: str,
    ) -> float:
        """Calculate conversion rate for journeys containing channel."""
        channel_journeys = df[df[channel_col] == channel][journey_id_col].unique()
        if len(channel_journeys) == 0:
            return 0.0

        journey_conv = df.drop_duplicates(journey_id_col).set_index(journey_id_col)
        n_converted = journey_conv.loc[channel_journeys, converted_col].sum()

        return n_converted / len(channel_journeys)

    def get_path_probabilities(
        self,
        trans_matrix: TransitionMatrix,
        max_path_length: int = 5,
        min_probability: float = 0.01,
    ) -> list[dict]:
        """
        Get most probable conversion paths.

        Args:
            trans_matrix: Transition matrix
            max_path_length: Maximum path length to consider
            min_probability: Minimum probability to include path

        Returns:
            List of paths with probabilities
        """
        paths = []
        self._enumerate_paths(
            trans_matrix,
            [self.START_STATE],
            1.0,
            max_path_length,
            min_probability,
            paths,
        )

        # Sort by probability
        paths.sort(key=lambda x: x["probability"], reverse=True)
        return paths

    def _enumerate_paths(
        self,
        trans_matrix: TransitionMatrix,
        current_path: list[str],
        current_prob: float,
        max_length: int,
        min_prob: float,
        paths: list[dict],
    ):
        """Recursively enumerate paths."""
        if current_prob < min_prob:
            return

        current_state = current_path[-1]

        if current_state == self.CONVERSION_STATE:
            paths.append({
                "path": current_path.copy(),
                "probability": current_prob,
            })
            return

        if current_state == self.NULL_STATE:
            return

        if len(current_path) >= max_length:
            return

        # Explore next states
        P = trans_matrix.matrix
        state_to_idx = trans_matrix.state_to_idx
        states = trans_matrix.states

        i = state_to_idx[current_state]
        for j, next_state in enumerate(states):
            prob = P[i, j]
            if prob > 0:
                current_path.append(next_state)
                self._enumerate_paths(
                    trans_matrix,
                    current_path,
                    current_prob * prob,
                    max_length,
                    min_prob,
                    paths,
                )
                current_path.pop()
