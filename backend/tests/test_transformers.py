"""Tests for ML transformers (adstock, saturation)."""

import numpy as np
import pytest

from app.ml.transformers.adstock import (
    AdstockConfig,
    GeometricAdstock,
    WeibullAdstock,
    DelayedAdstock,
)
from app.ml.transformers.saturation import (
    SaturationConfig,
    HillSaturation,
    LogisticSaturation,
    MichaelisMentenSaturation,
)


class TestGeometricAdstock:
    """Tests for geometric adstock transformation."""

    def test_geometric_adstock_basic(self):
        """Test basic geometric adstock transformation."""
        config = AdstockConfig(max_lag=4, decay_rate=0.5)
        transformer = GeometricAdstock(config)

        x = np.array([100, 0, 0, 0, 0])
        result = transformer.transform(x)

        # First value should remain 100
        assert result[0] == 100
        # Second value should be 50 (carryover from first)
        assert result[1] == pytest.approx(50, rel=0.01)
        # Third value should be 25
        assert result[2] == pytest.approx(25, rel=0.01)

    def test_geometric_adstock_weights(self):
        """Test that weights sum correctly."""
        config = AdstockConfig(max_lag=10, decay_rate=0.7)
        transformer = GeometricAdstock(config)
        weights = transformer.get_weights()

        # Weights should decay exponentially
        assert weights[0] == 1.0
        assert weights[1] == pytest.approx(0.7, rel=0.01)
        assert weights[2] == pytest.approx(0.49, rel=0.01)

    def test_geometric_adstock_zero_decay(self):
        """Test with zero decay (no carryover)."""
        config = AdstockConfig(max_lag=4, decay_rate=0.0)
        transformer = GeometricAdstock(config)

        x = np.array([100, 50, 25, 0, 0])
        result = transformer.transform(x)

        # With zero decay, output should equal input
        np.testing.assert_array_equal(result, x)


class TestWeibullAdstock:
    """Tests for Weibull adstock transformation."""

    def test_weibull_adstock_basic(self):
        """Test basic Weibull adstock transformation."""
        config = AdstockConfig(max_lag=8, shape=2.0, scale=3.0)
        transformer = WeibullAdstock(config)

        x = np.array([100, 0, 0, 0, 0, 0, 0, 0, 0])
        result = transformer.transform(x)

        # Result should be non-negative
        assert np.all(result >= 0)
        # First value should be modified by Weibull weights
        assert result[0] > 0

    def test_weibull_weights_shape(self):
        """Test Weibull weight shapes."""
        config = AdstockConfig(max_lag=10, shape=2.0, scale=5.0)
        transformer = WeibullAdstock(config)
        weights = transformer.get_weights()

        # Weights should be non-negative
        assert np.all(weights >= 0)
        # Should have correct length
        assert len(weights) == 11


class TestDelayedAdstock:
    """Tests for delayed adstock transformation."""

    def test_delayed_adstock_basic(self):
        """Test basic delayed adstock transformation."""
        config = AdstockConfig(max_lag=4, delay=2, decay_rate=0.5)
        transformer = DelayedAdstock(config)

        x = np.array([100, 0, 0, 0, 0, 0])
        result = transformer.transform(x)

        # Effect should be delayed
        assert result[0] < 100  # Some portion delayed
        assert result[2] > 0  # Delayed effect appears

    def test_delayed_adstock_preserves_total(self):
        """Test that delayed adstock roughly preserves total impact."""
        config = AdstockConfig(max_lag=8, delay=2, decay_rate=0.8)
        transformer = DelayedAdstock(config)

        x = np.array([100.0])
        x_padded = np.concatenate([x, np.zeros(10)])
        result = transformer.transform(x_padded)

        # Total effect should be similar (accounting for decay)
        assert result.sum() > 50  # At least half preserved


class TestHillSaturation:
    """Tests for Hill saturation transformation."""

    def test_hill_saturation_basic(self):
        """Test basic Hill saturation."""
        config = SaturationConfig(half_saturation=100.0, slope=1.0)
        transformer = HillSaturation(config)

        x = np.array([0, 50, 100, 200, 1000])
        result = transformer.transform(x)

        # At half saturation, result should be ~0.5
        assert result[2] == pytest.approx(0.5, rel=0.01)
        # Should be monotonically increasing
        assert np.all(np.diff(result) >= 0)
        # Should be bounded
        assert np.all(result <= 1.0)
        assert np.all(result >= 0.0)

    def test_hill_saturation_steep_slope(self):
        """Test Hill saturation with steep slope."""
        config = SaturationConfig(half_saturation=100.0, slope=3.0)
        transformer = HillSaturation(config)

        x = np.array([50, 100, 150])
        result = transformer.transform(x)

        # Steep slope means faster transition
        assert result[0] < 0.2  # Below half-sat should be low
        assert result[2] > 0.8  # Above half-sat should be high


class TestLogisticSaturation:
    """Tests for logistic saturation transformation."""

    def test_logistic_saturation_basic(self):
        """Test basic logistic saturation."""
        config = SaturationConfig(L=1.0, k=0.1, x0=50.0)
        transformer = LogisticSaturation(config)

        x = np.array([0, 25, 50, 75, 100])
        result = transformer.transform(x)

        # At midpoint x0, should be ~0.5
        assert result[2] == pytest.approx(0.5, rel=0.01)
        # Should be monotonically increasing
        assert np.all(np.diff(result) >= 0)

    def test_logistic_saturation_bounds(self):
        """Test logistic saturation is bounded."""
        config = SaturationConfig(L=1.0, k=0.05, x0=100.0)
        transformer = LogisticSaturation(config)

        x = np.array([0, 1000, 10000])
        result = transformer.transform(x)

        assert np.all(result >= 0)
        assert np.all(result <= 1.0)


class TestMichaelisMentenSaturation:
    """Tests for Michaelis-Menten saturation transformation."""

    def test_michaelis_menten_basic(self):
        """Test basic Michaelis-Menten saturation."""
        config = SaturationConfig(Vmax=1.0, Km=100.0)
        transformer = MichaelisMentenSaturation(config)

        x = np.array([0, 50, 100, 200, 500])
        result = transformer.transform(x)

        # At Km, should be ~0.5
        assert result[2] == pytest.approx(0.5, rel=0.01)
        # Should be monotonically increasing
        assert np.all(np.diff(result) >= 0)
        # Should approach Vmax
        assert result[4] > 0.8

    def test_michaelis_menten_zero_input(self):
        """Test Michaelis-Menten with zero input."""
        config = SaturationConfig(Vmax=1.0, Km=100.0)
        transformer = MichaelisMentenSaturation(config)

        result = transformer.transform(np.array([0.0]))
        assert result[0] == 0.0
