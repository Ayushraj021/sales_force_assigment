"""
Differential Privacy Implementation

Privacy-preserving data analysis with mathematically proven guarantees.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union
from enum import Enum
import numpy as np
import logging

logger = logging.getLogger(__name__)


class NoiseType(str, Enum):
    """Types of noise for differential privacy."""
    LAPLACE = "laplace"
    GAUSSIAN = "gaussian"


@dataclass
class DPConfig:
    """Configuration for differential privacy."""
    epsilon: float = 1.0  # Privacy budget
    delta: float = 1e-5  # Failure probability (for Gaussian)
    noise_type: NoiseType = NoiseType.LAPLACE
    sensitivity: Optional[float] = None  # Query sensitivity
    clip_min: Optional[float] = None
    clip_max: Optional[float] = None


@dataclass
class DPResult:
    """Result of a differentially private query."""
    value: Union[float, np.ndarray]
    noise_added: float
    epsilon_used: float
    privacy_budget_remaining: float
    confidence_interval: Optional[tuple] = None


class DifferentialPrivacy:
    """
    Differential Privacy for Marketing Analytics.

    Features:
    - Laplace and Gaussian mechanism
    - Privacy budget tracking
    - Support for aggregate queries
    - Configurable sensitivity

    Example:
        dp = DifferentialPrivacy(epsilon=1.0)

        # Private mean
        private_mean = dp.mean(sales_data)

        # Private histogram
        private_hist = dp.histogram(data, bins=10)
    """

    def __init__(self, config: Optional[DPConfig] = None):
        self.config = config or DPConfig()
        self._total_epsilon_used = 0.0
        self._query_count = 0

    @property
    def privacy_budget_remaining(self) -> float:
        """Remaining privacy budget."""
        return max(0, self.config.epsilon - self._total_epsilon_used)

    def mean(
        self,
        data: np.ndarray,
        epsilon: Optional[float] = None,
    ) -> DPResult:
        """
        Compute differentially private mean.

        Args:
            data: Input data
            epsilon: Privacy budget for this query

        Returns:
            DPResult with private mean
        """
        data = np.asarray(data).flatten()
        epsilon = epsilon or self.config.epsilon * 0.1  # Default: 10% of budget

        # Clip data if bounds specified
        if self.config.clip_min is not None and self.config.clip_max is not None:
            data = np.clip(data, self.config.clip_min, self.config.clip_max)
            sensitivity = (self.config.clip_max - self.config.clip_min) / len(data)
        else:
            sensitivity = self.config.sensitivity or (data.max() - data.min()) / len(data)

        true_mean = np.mean(data)
        noise = self._add_noise(sensitivity, epsilon)

        private_mean = true_mean + noise

        self._total_epsilon_used += epsilon
        self._query_count += 1

        # Confidence interval
        ci = self._confidence_interval(sensitivity, epsilon)

        return DPResult(
            value=float(private_mean),
            noise_added=float(noise),
            epsilon_used=epsilon,
            privacy_budget_remaining=self.privacy_budget_remaining,
            confidence_interval=(private_mean - ci, private_mean + ci),
        )

    def sum(
        self,
        data: np.ndarray,
        epsilon: Optional[float] = None,
    ) -> DPResult:
        """Compute differentially private sum."""
        data = np.asarray(data).flatten()
        epsilon = epsilon or self.config.epsilon * 0.1

        if self.config.clip_min is not None and self.config.clip_max is not None:
            data = np.clip(data, self.config.clip_min, self.config.clip_max)
            sensitivity = self.config.clip_max - self.config.clip_min
        else:
            sensitivity = self.config.sensitivity or (data.max() - data.min())

        true_sum = np.sum(data)
        noise = self._add_noise(sensitivity, epsilon)

        private_sum = true_sum + noise

        self._total_epsilon_used += epsilon
        self._query_count += 1

        ci = self._confidence_interval(sensitivity, epsilon)

        return DPResult(
            value=float(private_sum),
            noise_added=float(noise),
            epsilon_used=epsilon,
            privacy_budget_remaining=self.privacy_budget_remaining,
            confidence_interval=(private_sum - ci, private_sum + ci),
        )

    def count(
        self,
        data: np.ndarray,
        condition: Optional[callable] = None,
        epsilon: Optional[float] = None,
    ) -> DPResult:
        """Compute differentially private count."""
        data = np.asarray(data).flatten()
        epsilon = epsilon or self.config.epsilon * 0.1

        if condition:
            true_count = np.sum(condition(data))
        else:
            true_count = len(data)

        sensitivity = 1.0  # Adding/removing one record changes count by 1
        noise = self._add_noise(sensitivity, epsilon)

        private_count = max(0, true_count + noise)

        self._total_epsilon_used += epsilon
        self._query_count += 1

        ci = self._confidence_interval(sensitivity, epsilon)

        return DPResult(
            value=int(round(private_count)),
            noise_added=float(noise),
            epsilon_used=epsilon,
            privacy_budget_remaining=self.privacy_budget_remaining,
            confidence_interval=(max(0, private_count - ci), private_count + ci),
        )

    def histogram(
        self,
        data: np.ndarray,
        bins: int = 10,
        epsilon: Optional[float] = None,
    ) -> DPResult:
        """
        Compute differentially private histogram.

        Args:
            data: Input data
            bins: Number of bins
            epsilon: Privacy budget

        Returns:
            DPResult with private histogram counts
        """
        data = np.asarray(data).flatten()
        epsilon = epsilon or self.config.epsilon * 0.1

        # Compute true histogram
        hist, bin_edges = np.histogram(data, bins=bins)

        # Add noise to each bin
        sensitivity = 2.0  # Each record can affect 2 bins
        epsilon_per_bin = epsilon / bins

        noisy_hist = []
        total_noise = 0.0

        for count in hist:
            noise = self._add_noise(sensitivity, epsilon_per_bin)
            noisy_hist.append(max(0, count + noise))
            total_noise += abs(noise)

        self._total_epsilon_used += epsilon
        self._query_count += 1

        return DPResult(
            value=np.array(noisy_hist),
            noise_added=total_noise,
            epsilon_used=epsilon,
            privacy_budget_remaining=self.privacy_budget_remaining,
        )

    def percentile(
        self,
        data: np.ndarray,
        q: float,
        epsilon: Optional[float] = None,
    ) -> DPResult:
        """Compute differentially private percentile using exponential mechanism."""
        data = np.asarray(data).flatten()
        epsilon = epsilon or self.config.epsilon * 0.1

        # Use exponential mechanism
        sorted_data = np.sort(data)

        # Score function: distance to true percentile position
        target_idx = int(q / 100 * len(sorted_data))
        scores = -np.abs(np.arange(len(sorted_data)) - target_idx)

        # Exponential mechanism probabilities
        sensitivity = 1.0
        probs = np.exp(epsilon * scores / (2 * sensitivity))
        probs /= probs.sum()

        # Sample
        selected_idx = np.random.choice(len(sorted_data), p=probs)
        private_percentile = sorted_data[selected_idx]

        self._total_epsilon_used += epsilon
        self._query_count += 1

        return DPResult(
            value=float(private_percentile),
            noise_added=0.0,  # Exponential mechanism, no additive noise
            epsilon_used=epsilon,
            privacy_budget_remaining=self.privacy_budget_remaining,
        )

    def _add_noise(
        self,
        sensitivity: float,
        epsilon: float,
    ) -> float:
        """Add calibrated noise based on mechanism type."""
        if self.config.noise_type == NoiseType.LAPLACE:
            scale = sensitivity / epsilon
            return float(np.random.laplace(0, scale))

        else:  # Gaussian
            sigma = sensitivity * np.sqrt(2 * np.log(1.25 / self.config.delta)) / epsilon
            return float(np.random.normal(0, sigma))

    def _confidence_interval(
        self,
        sensitivity: float,
        epsilon: float,
        confidence: float = 0.95,
    ) -> float:
        """Calculate confidence interval half-width."""
        if self.config.noise_type == NoiseType.LAPLACE:
            scale = sensitivity / epsilon
            return scale * np.log(1 / (1 - confidence))
        else:
            sigma = sensitivity * np.sqrt(2 * np.log(1.25 / self.config.delta)) / epsilon
            from scipy import stats
            return stats.norm.ppf((1 + confidence) / 2) * sigma

    def reset_budget(self) -> None:
        """Reset privacy budget."""
        self._total_epsilon_used = 0.0
        self._query_count = 0


class PrivateAggregator:
    """
    Aggregator for multiple private queries with budget management.
    """

    def __init__(self, total_epsilon: float = 1.0, delta: float = 1e-5):
        self.total_epsilon = total_epsilon
        self.delta = delta
        self._used_epsilon = 0.0
        self._queries: List[Dict] = []

    def query(
        self,
        query_type: str,
        data: np.ndarray,
        epsilon_fraction: float = 0.1,
        **kwargs,
    ) -> DPResult:
        """
        Execute a private query.

        Args:
            query_type: Type of query (mean, sum, count, histogram)
            data: Input data
            epsilon_fraction: Fraction of remaining budget to use
            **kwargs: Additional query parameters

        Returns:
            DPResult
        """
        epsilon = self.remaining_budget * epsilon_fraction

        if epsilon <= 0:
            raise ValueError("Privacy budget exhausted")

        dp = DifferentialPrivacy(DPConfig(epsilon=epsilon, delta=self.delta))

        if query_type == "mean":
            result = dp.mean(data, epsilon=epsilon)
        elif query_type == "sum":
            result = dp.sum(data, epsilon=epsilon)
        elif query_type == "count":
            result = dp.count(data, epsilon=epsilon, **kwargs)
        elif query_type == "histogram":
            result = dp.histogram(data, epsilon=epsilon, **kwargs)
        else:
            raise ValueError(f"Unknown query type: {query_type}")

        self._used_epsilon += epsilon
        self._queries.append({
            "type": query_type,
            "epsilon": epsilon,
            "timestamp": np.datetime64('now'),
        })

        return result

    @property
    def remaining_budget(self) -> float:
        return max(0, self.total_epsilon - self._used_epsilon)

    def get_query_history(self) -> List[Dict]:
        return self._queries.copy()
