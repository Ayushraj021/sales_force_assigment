"""
Unified Measurement Framework

Integrates multiple measurement signals to provide holistic
channel effectiveness estimates with calibration and reconciliation.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Literal
from enum import Enum
import numpy as np
import pandas as pd


class SignalType(str, Enum):
    """Types of measurement signals."""
    MMM = "mmm"
    MTA = "mta"
    GEO_EXPERIMENT = "geo_experiment"
    INCREMENTALITY_TEST = "incrementality_test"
    CAUSAL_DISCOVERY = "causal_discovery"
    SURVEY = "survey"


@dataclass
class MeasurementSignal:
    """
    Individual measurement signal from a methodology.

    Represents the output from one measurement approach that
    contributes to the unified view.
    """

    signal_type: SignalType
    channel: str

    # Effect estimate
    effect: float  # Normalized effect (e.g., ROAS, lift %)
    effect_lower: Optional[float] = None
    effect_upper: Optional[float] = None

    # Statistical quality
    confidence: float = 0.95
    sample_size: Optional[int] = None
    p_value: Optional[float] = None

    # Temporal coverage
    start_date: Optional[str] = None
    end_date: Optional[str] = None

    # Additional metadata
    methodology_details: Dict = field(default_factory=dict)
    quality_score: float = 1.0  # 0-1 quality weight


@dataclass
class SignalWeight:
    """
    Weight assigned to a measurement signal.

    Weights are used for reconciliation based on:
    - Statistical reliability
    - Temporal relevance
    - Methodology appropriateness
    """

    signal_type: SignalType
    weight: float  # 0-1
    reason: str


@dataclass
class UnifiedResult:
    """
    Unified measurement result for a channel.

    Combines multiple signals into calibrated estimates.
    """

    channel: str

    # Unified estimates
    unified_effect: float
    unified_effect_lower: float
    unified_effect_upper: float

    # Component contributions
    signal_contributions: Dict[SignalType, float]
    weights_used: List[SignalWeight]

    # Confidence and quality
    unified_confidence: float
    reconciliation_quality: float  # How well signals agreed

    # Recommendations
    recommendations: List[str] = field(default_factory=list)


class UnifiedMeasurementFramework:
    """
    Unified Measurement Framework for Marketing Analytics.

    Integrates signals from:
    - Marketing Mix Modeling (long-term, aggregate)
    - Multi-Touch Attribution (short-term, user-level)
    - Geo-Lift Experiments (causal, randomized)
    - Incrementality Tests (A/B, holdout)
    - Causal Discovery (structural relationships)

    Uses Bayesian updating and signal quality weighting for
    calibrated channel effectiveness estimates.

    Example:
        framework = UnifiedMeasurementFramework()

        # Add signals from different methodologies
        framework.add_signal(mmm_signal)
        framework.add_signal(mta_signal)
        framework.add_signal(geo_experiment_signal)

        # Get unified view
        results = framework.compute_unified()
    """

    def __init__(
        self,
        default_weights: Optional[Dict[SignalType, float]] = None,
        calibration_priority: Optional[List[SignalType]] = None,
    ):
        """
        Initialize the framework.

        Args:
            default_weights: Default weights for each signal type
            calibration_priority: Order of priority for calibration
                                  (experiments > MMM > MTA by default)
        """
        self.signals: Dict[str, List[MeasurementSignal]] = {}  # channel -> signals

        self.default_weights = default_weights or {
            SignalType.GEO_EXPERIMENT: 0.4,
            SignalType.INCREMENTALITY_TEST: 0.35,
            SignalType.MMM: 0.15,
            SignalType.MTA: 0.08,
            SignalType.CAUSAL_DISCOVERY: 0.02,
        }

        self.calibration_priority = calibration_priority or [
            SignalType.GEO_EXPERIMENT,
            SignalType.INCREMENTALITY_TEST,
            SignalType.MMM,
            SignalType.MTA,
            SignalType.CAUSAL_DISCOVERY,
        ]

    def add_signal(self, signal: MeasurementSignal) -> None:
        """Add a measurement signal."""
        if signal.channel not in self.signals:
            self.signals[signal.channel] = []
        self.signals[signal.channel].append(signal)

    def add_mmm_results(
        self,
        channel_effects: Dict[str, float],
        channel_ci: Optional[Dict[str, tuple]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> None:
        """
        Add MMM results as signals.

        Args:
            channel_effects: Dict of channel -> effect (e.g., ROAS)
            channel_ci: Dict of channel -> (lower, upper) confidence interval
            start_date: MMM training data start
            end_date: MMM training data end
        """
        for channel, effect in channel_effects.items():
            ci = channel_ci.get(channel) if channel_ci else None
            self.add_signal(MeasurementSignal(
                signal_type=SignalType.MMM,
                channel=channel,
                effect=effect,
                effect_lower=ci[0] if ci else None,
                effect_upper=ci[1] if ci else None,
                start_date=start_date,
                end_date=end_date,
                methodology_details={"model": "mmm"},
            ))

    def add_mta_results(
        self,
        channel_attribution: Dict[str, float],
        model_type: str = "markov",
    ) -> None:
        """
        Add MTA results as signals.

        Args:
            channel_attribution: Dict of channel -> attribution share
            model_type: Attribution model type
        """
        for channel, attribution in channel_attribution.items():
            self.add_signal(MeasurementSignal(
                signal_type=SignalType.MTA,
                channel=channel,
                effect=attribution,
                methodology_details={"model": model_type},
                quality_score=0.7,  # MTA generally lower quality
            ))

    def add_experiment_result(
        self,
        channel: str,
        lift: float,
        lift_ci: Optional[tuple] = None,
        p_value: Optional[float] = None,
        experiment_type: str = "geo_lift",
    ) -> None:
        """
        Add experiment result as signal.

        Args:
            channel: Channel tested
            lift: Measured lift
            lift_ci: Confidence interval (lower, upper)
            p_value: Statistical significance
            experiment_type: Type of experiment
        """
        signal_type = (
            SignalType.GEO_EXPERIMENT
            if experiment_type == "geo_lift"
            else SignalType.INCREMENTALITY_TEST
        )

        self.add_signal(MeasurementSignal(
            signal_type=signal_type,
            channel=channel,
            effect=lift,
            effect_lower=lift_ci[0] if lift_ci else None,
            effect_upper=lift_ci[1] if lift_ci else None,
            p_value=p_value,
            methodology_details={"type": experiment_type},
            quality_score=1.0 if p_value and p_value < 0.05 else 0.8,
        ))

    def _compute_signal_weights(
        self, signals: List[MeasurementSignal]
    ) -> List[SignalWeight]:
        """Compute weights for each signal based on quality and type."""
        weights = []

        for signal in signals:
            # Start with default weight for signal type
            base_weight = self.default_weights.get(signal.signal_type, 0.1)

            # Adjust for quality score
            adjusted_weight = base_weight * signal.quality_score

            # Adjust for statistical significance
            if signal.p_value is not None:
                if signal.p_value < 0.01:
                    adjusted_weight *= 1.2
                elif signal.p_value < 0.05:
                    adjusted_weight *= 1.0
                else:
                    adjusted_weight *= 0.6

            # Adjust for confidence interval width
            if signal.effect_lower is not None and signal.effect_upper is not None:
                ci_width = signal.effect_upper - signal.effect_lower
                relative_width = ci_width / (abs(signal.effect) + 1e-6)
                if relative_width < 0.2:
                    adjusted_weight *= 1.1
                elif relative_width > 0.5:
                    adjusted_weight *= 0.8

            weights.append(SignalWeight(
                signal_type=signal.signal_type,
                weight=adjusted_weight,
                reason=f"Base: {base_weight:.2f}, Quality: {signal.quality_score:.2f}",
            ))

        # Normalize weights
        total = sum(w.weight for w in weights)
        if total > 0:
            for w in weights:
                w.weight /= total

        return weights

    def _weighted_average(
        self,
        signals: List[MeasurementSignal],
        weights: List[SignalWeight],
    ) -> tuple:
        """Compute weighted average effect and confidence interval."""
        effects = np.array([s.effect for s in signals])
        weight_values = np.array([w.weight for w in weights])

        # Weighted mean
        unified_effect = np.average(effects, weights=weight_values)

        # Weighted standard error
        if len(signals) > 1:
            # Bootstrap-like uncertainty propagation
            lowers = np.array([
                s.effect_lower if s.effect_lower is not None else s.effect * 0.8
                for s in signals
            ])
            uppers = np.array([
                s.effect_upper if s.effect_upper is not None else s.effect * 1.2
                for s in signals
            ])

            unified_lower = np.average(lowers, weights=weight_values)
            unified_upper = np.average(uppers, weights=weight_values)
        else:
            unified_lower = signals[0].effect_lower or unified_effect * 0.8
            unified_upper = signals[0].effect_upper or unified_effect * 1.2

        return unified_effect, unified_lower, unified_upper

    def _calibrate_to_experiments(
        self,
        signals: List[MeasurementSignal],
        unified_effect: float,
    ) -> float:
        """
        Calibrate unified estimate using experimental results.

        Experiments are treated as ground truth for calibration.
        """
        experiment_signals = [
            s for s in signals
            if s.signal_type in (SignalType.GEO_EXPERIMENT, SignalType.INCREMENTALITY_TEST)
        ]

        if not experiment_signals:
            return unified_effect

        # Average experimental effect
        exp_effect = np.mean([s.effect for s in experiment_signals])

        # Calibration factor
        if abs(unified_effect) > 1e-6:
            calibration_factor = exp_effect / unified_effect
            # Limit calibration to reasonable range
            calibration_factor = np.clip(calibration_factor, 0.5, 2.0)
        else:
            calibration_factor = 1.0

        return unified_effect * calibration_factor

    def _assess_signal_agreement(
        self, signals: List[MeasurementSignal]
    ) -> float:
        """
        Assess how well signals agree with each other.

        Returns quality score (0-1) based on signal consistency.
        """
        if len(signals) <= 1:
            return 1.0

        effects = np.array([s.effect for s in signals])
        mean_effect = np.mean(effects)

        if abs(mean_effect) < 1e-6:
            return 0.5

        # Coefficient of variation (normalized std)
        cv = np.std(effects) / abs(mean_effect)

        # Convert to 0-1 quality score
        # CV < 0.1 => high agreement, CV > 0.5 => low agreement
        quality = 1.0 - np.clip(cv / 0.5, 0, 1)

        return quality

    def _generate_recommendations(
        self,
        channel: str,
        signals: List[MeasurementSignal],
        agreement_quality: float,
    ) -> List[str]:
        """Generate recommendations based on signal analysis."""
        recommendations = []

        signal_types = set(s.signal_type for s in signals)

        # Missing signal types
        if SignalType.GEO_EXPERIMENT not in signal_types:
            recommendations.append(
                f"Consider running a geo-lift experiment for {channel} to validate effects"
            )

        if SignalType.MMM not in signal_types:
            recommendations.append(
                f"Include {channel} in MMM analysis for long-term effect estimation"
            )

        # Low agreement warning
        if agreement_quality < 0.5:
            recommendations.append(
                f"Signals for {channel} show low agreement - investigate methodology differences"
            )

        # Single source warning
        if len(signals) == 1:
            recommendations.append(
                f"Only one measurement source for {channel} - add additional signals for robustness"
            )

        return recommendations

    def compute_unified(
        self,
        calibrate: bool = True,
    ) -> Dict[str, UnifiedResult]:
        """
        Compute unified measurement results for all channels.

        Args:
            calibrate: Whether to calibrate using experiments

        Returns:
            Dict of channel -> UnifiedResult
        """
        results = {}

        for channel, signals in self.signals.items():
            if not signals:
                continue

            # Compute weights
            weights = self._compute_signal_weights(signals)

            # Weighted average
            unified_effect, unified_lower, unified_upper = self._weighted_average(
                signals, weights
            )

            # Optional calibration
            if calibrate:
                calibrated_effect = self._calibrate_to_experiments(
                    signals, unified_effect
                )
                # Adjust CI proportionally
                ratio = calibrated_effect / unified_effect if abs(unified_effect) > 1e-6 else 1.0
                unified_effect = calibrated_effect
                unified_lower *= ratio
                unified_upper *= ratio

            # Signal contributions
            contributions = {}
            for signal, weight in zip(signals, weights):
                if signal.signal_type not in contributions:
                    contributions[signal.signal_type] = 0
                contributions[signal.signal_type] += weight.weight * signal.effect

            # Agreement quality
            agreement_quality = self._assess_signal_agreement(signals)

            # Recommendations
            recommendations = self._generate_recommendations(
                channel, signals, agreement_quality
            )

            results[channel] = UnifiedResult(
                channel=channel,
                unified_effect=unified_effect,
                unified_effect_lower=unified_lower,
                unified_effect_upper=unified_upper,
                signal_contributions=contributions,
                weights_used=weights,
                unified_confidence=0.95,
                reconciliation_quality=agreement_quality,
                recommendations=recommendations,
            )

        return results

    def to_dataframe(self, results: Dict[str, UnifiedResult]) -> pd.DataFrame:
        """Convert results to DataFrame for reporting."""
        data = []
        for channel, result in results.items():
            data.append({
                "channel": channel,
                "effect": result.unified_effect,
                "effect_lower": result.unified_effect_lower,
                "effect_upper": result.unified_effect_upper,
                "quality": result.reconciliation_quality,
                "n_signals": len([w for w in result.weights_used]),
                "signal_types": ", ".join(
                    str(st.value) for st in result.signal_contributions.keys()
                ),
            })
        return pd.DataFrame(data)

    def get_channel_summary(self, channel: str) -> Optional[Dict]:
        """Get detailed summary for a single channel."""
        if channel not in self.signals:
            return None

        signals = self.signals[channel]
        results = self.compute_unified()
        result = results.get(channel)

        if not result:
            return None

        return {
            "channel": channel,
            "unified_effect": result.unified_effect,
            "confidence_interval": (
                result.unified_effect_lower,
                result.unified_effect_upper,
            ),
            "quality_score": result.reconciliation_quality,
            "signals": [
                {
                    "type": s.signal_type.value,
                    "effect": s.effect,
                    "quality": s.quality_score,
                }
                for s in signals
            ],
            "weights": [
                {
                    "type": w.signal_type.value,
                    "weight": w.weight,
                    "reason": w.reason,
                }
                for w in result.weights_used
            ],
            "recommendations": result.recommendations,
        }
