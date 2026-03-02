"""Tests for budget optimization."""

import numpy as np
import pytest

from app.ml.optimization.optimizer import (
    BudgetOptimizer,
    OptimizationConfig,
    ChannelConstraint,
)
from app.ml.optimization.roi_analysis import (
    ROIAnalyzer,
    calculate_marginal_roi,
    calculate_channel_roi,
)


class TestBudgetOptimizer:
    """Tests for budget optimizer."""

    @pytest.fixture
    def basic_config(self):
        """Basic optimization configuration."""
        return OptimizationConfig(
            total_budget=1000000.0,
            objective="maximize_revenue",
            solver="ECOS",
        )

    @pytest.fixture
    def channel_constraints(self):
        """Sample channel constraints."""
        return [
            ChannelConstraint(
                name="tv",
                min_spend=50000,
                max_spend=500000,
                baseline_spend=200000,
            ),
            ChannelConstraint(
                name="digital",
                min_spend=100000,
                max_spend=400000,
                baseline_spend=250000,
            ),
            ChannelConstraint(
                name="radio",
                min_spend=25000,
                max_spend=200000,
                baseline_spend=100000,
            ),
        ]

    @pytest.fixture
    def response_curves(self):
        """Mock response curves (simple linear for testing)."""
        return {
            "tv": lambda x: 2.0 * x,  # $2 revenue per $1 spent
            "digital": lambda x: 2.5 * x,  # $2.5 revenue per $1 spent
            "radio": lambda x: 1.5 * x,  # $1.5 revenue per $1 spent
        }

    def test_optimizer_respects_total_budget(
        self, basic_config, channel_constraints, response_curves
    ):
        """Test that optimizer respects total budget constraint."""
        optimizer = BudgetOptimizer(
            config=basic_config,
            constraints=channel_constraints,
            response_curves=response_curves,
        )
        result = optimizer.optimize()

        total_allocated = sum(result["allocation"].values())
        assert total_allocated <= basic_config.total_budget + 1  # Allow small tolerance

    def test_optimizer_respects_channel_bounds(
        self, basic_config, channel_constraints, response_curves
    ):
        """Test that optimizer respects min/max constraints."""
        optimizer = BudgetOptimizer(
            config=basic_config,
            constraints=channel_constraints,
            response_curves=response_curves,
        )
        result = optimizer.optimize()

        for constraint in channel_constraints:
            allocated = result["allocation"][constraint.name]
            assert allocated >= constraint.min_spend - 1
            assert allocated <= constraint.max_spend + 1

    def test_optimizer_returns_expected_fields(
        self, basic_config, channel_constraints, response_curves
    ):
        """Test that optimizer returns all expected fields."""
        optimizer = BudgetOptimizer(
            config=basic_config,
            constraints=channel_constraints,
            response_curves=response_curves,
        )
        result = optimizer.optimize()

        assert "allocation" in result
        assert "total_revenue" in result
        assert "status" in result
        assert result["status"] == "optimal"


class TestROIAnalyzer:
    """Tests for ROI analysis."""

    def test_calculate_channel_roi(self):
        """Test basic ROI calculation."""
        spend = 100000
        revenue = 250000

        roi = calculate_channel_roi(spend, revenue)

        assert roi == pytest.approx(1.5, rel=0.01)  # (250k - 100k) / 100k

    def test_calculate_channel_roi_zero_spend(self):
        """Test ROI calculation with zero spend."""
        roi = calculate_channel_roi(0, 0)
        assert roi == 0.0

    def test_calculate_marginal_roi(self):
        """Test marginal ROI calculation."""
        # Simple response curve: revenue = 2 * sqrt(spend)
        response_curve = lambda x: 2 * np.sqrt(x)

        current_spend = 10000
        increment = 1000

        marginal_roi = calculate_marginal_roi(
            response_curve, current_spend, increment
        )

        # Derivative of 2*sqrt(x) at x=10000 is 1/sqrt(10000) = 0.01
        # marginal_roi = (f(11000) - f(10000)) / 1000
        expected = (response_curve(11000) - response_curve(10000)) / 1000
        assert marginal_roi == pytest.approx(expected, rel=0.01)

    def test_marginal_roi_diminishing_returns(self):
        """Test that marginal ROI shows diminishing returns."""
        # Response curve with diminishing returns
        response_curve = lambda x: 1000 * np.log1p(x / 1000)

        low_spend_mroi = calculate_marginal_roi(response_curve, 10000, 1000)
        high_spend_mroi = calculate_marginal_roi(response_curve, 100000, 1000)

        # Marginal ROI should be lower at higher spend levels
        assert high_spend_mroi < low_spend_mroi


class TestROIAnalyzerClass:
    """Tests for ROIAnalyzer class."""

    @pytest.fixture
    def analyzer(self):
        """Create ROI analyzer with sample data."""
        response_curves = {
            "tv": lambda x: 2.0 * np.sqrt(x * 1000),
            "digital": lambda x: 2.5 * np.sqrt(x * 1000),
            "radio": lambda x: 1.5 * np.sqrt(x * 1000),
        }
        current_allocation = {
            "tv": 200000,
            "digital": 300000,
            "radio": 100000,
        }
        return ROIAnalyzer(response_curves, current_allocation)

    def test_analyzer_calculate_all_rois(self, analyzer):
        """Test calculating ROI for all channels."""
        rois = analyzer.calculate_all_channel_rois()

        assert "tv" in rois
        assert "digital" in rois
        assert "radio" in rois
        assert all(roi >= 0 for roi in rois.values())

    def test_analyzer_marginal_rois(self, analyzer):
        """Test calculating marginal ROI for all channels."""
        marginal_rois = analyzer.calculate_marginal_rois(increment=10000)

        assert len(marginal_rois) == 3
        assert all(mroi >= 0 for mroi in marginal_rois.values())

    def test_analyzer_rank_channels(self, analyzer):
        """Test ranking channels by marginal ROI."""
        ranked = analyzer.rank_channels_by_marginal_roi()

        assert len(ranked) == 3
        # Should be sorted by marginal ROI (descending)
        for i in range(len(ranked) - 1):
            assert ranked[i]["marginal_roi"] >= ranked[i + 1]["marginal_roi"]
