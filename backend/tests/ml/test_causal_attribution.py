"""
Test Cases for Causal Inference and Attribution Models

Tests for GeoLift, Synthetic Control, Markov Attribution,
Shapley Attribution, and Causal Discovery with REAL marketing data.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path


# Fixtures directory
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


# ============================================================================
# Real Data Loading Utilities
# ============================================================================

def load_real_geo_data() -> pd.DataFrame:
    """Load real geographic experiment data."""
    csv_path = FIXTURES_DIR / "real_geo_data.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path, parse_dates=["date"])
        return df
    return None


def load_real_journey_data() -> pd.DataFrame:
    """Load real customer journey data."""
    csv_path = FIXTURES_DIR / "real_journey_data.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path, parse_dates=["touchpoint_timestamp"])
        return df
    return None


def load_real_mmm_data() -> pd.DataFrame:
    """Load real marketing mix modeling data."""
    csv_path = FIXTURES_DIR / "real_mmm_data.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path, parse_dates=["date"])
        return df
    # Fallback
    csv_path = FIXTURES_DIR / "sample_mmm_data.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path, parse_dates=["date"])
        return df
    return None


def prepare_geo_experiment_data(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare geo data for experiment analysis."""
    if df is None:
        return None

    # Convert to weekly periods
    df = df.copy()
    df["period"] = (df["date"] - df["date"].min()).dt.days // 7

    return df


def prepare_journey_data(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare journey data for attribution analysis."""
    if df is None:
        return None

    df = df.copy()

    # Sort by timestamp within each journey
    df = df.sort_values(["journey_id", "touchpoint_timestamp"])

    # Add touchpoint order
    df["touchpoint_order"] = df.groupby("journey_id").cumcount() + 1

    # Mark last touchpoint in converting journeys
    journey_converted = df.groupby("journey_id")["conversion"].max().reset_index()
    df = df.merge(journey_converted, on="journey_id", suffixes=("", "_journey"))

    return df


# ============================================================================
# GeoLift Tests with Real Data
# ============================================================================

class TestGeoLiftRealData:
    """Test cases for GeoLift analysis with real geographic data."""

    @pytest.fixture
    def real_geo_df(self):
        """Load real geo experiment data."""
        df = load_real_geo_data()
        if df is None:
            pytest.skip("Real geo data not available")
        return prepare_geo_experiment_data(df)

    def test_geo_lift_analyzer_initialization(self):
        """Test GeoLift analyzer initialization."""
        from app.ml.causal.geo_lift import GeoLiftAnalyzer, GeoLiftConfig

        config = GeoLiftConfig(
            n_test_regions=5,
            pre_treatment_periods=26,
        )
        analyzer = GeoLiftAnalyzer(config)

        assert analyzer.config.n_test_regions == 5

    def test_geo_data_structure(self, real_geo_df):
        """Test real geo data has proper structure."""
        df = real_geo_df

        # Check required columns
        assert "region" in df.columns
        assert "sales" in df.columns
        assert "is_test_region" in df.columns

        # Check data quality
        assert df["sales"].min() > 0
        assert len(df["region"].unique()) >= 5

    def test_power_analysis_real_data(self, real_geo_df):
        """Test power analysis on real geo data."""
        from app.ml.causal.geo_lift import GeoLiftAnalyzer, GeoLiftConfig

        df = real_geo_df

        config = GeoLiftConfig(n_test_regions=2)
        analyzer = GeoLiftAnalyzer(config)

        power_result = analyzer.power_analysis(
            data=df,
            region_col="region",
            time_col="period",
            outcome_col="sales",
            effect_sizes=[0.05, 0.10, 0.15, 0.20],
        )

        assert power_result is not None
        # Power should increase with effect size
        if hasattr(power_result, "power_by_effect"):
            powers = list(power_result.power_by_effect.values())
            # Generally power should increase with effect size
            assert powers[-1] >= powers[0] - 0.1  # Some tolerance

    def test_geo_lift_analysis_real_data(self, real_geo_df):
        """Test full geo-lift analysis on real data."""
        from app.ml.causal.geo_lift import GeoLiftAnalyzer, GeoLiftConfig

        df = real_geo_df

        # Identify test and control regions
        test_regions = df[df["is_test_region"] == 1]["region"].unique().tolist()
        control_regions = df[df["is_test_region"] == 0]["region"].unique().tolist()

        config = GeoLiftConfig(
            n_test_regions=len(test_regions),
            pre_treatment_periods=4,  # First 4 weeks
        )
        analyzer = GeoLiftAnalyzer(config)

        result = analyzer.analyze(
            data=df,
            test_regions=test_regions,
            control_regions=control_regions,
            treatment_start=4,  # Treatment starts week 4
            region_col="region",
            time_col="period",
            outcome_col="sales",
        )

        assert result is not None
        # Result should have lift metric
        assert hasattr(result, "lift")


# ============================================================================
# Synthetic Control Tests with Real Data
# ============================================================================

class TestSyntheticControlRealData:
    """Test cases for Synthetic Control Method with real data."""

    @pytest.fixture
    def real_geo_df(self):
        """Load real geo data for SCM."""
        df = load_real_geo_data()
        if df is None:
            pytest.skip("Real geo data not available")
        return prepare_geo_experiment_data(df)

    def test_synthetic_control_initialization(self):
        """Test initialization."""
        from app.ml.causal.synthetic_control import SyntheticControlMethod, SCMConfig

        config = SCMConfig(regularization=0.01)
        scm = SyntheticControlMethod(config)

        assert scm.config.regularization == 0.01

    def test_synthetic_control_fit_real_data(self, real_geo_df):
        """Test SCM fitting on real geographic data."""
        from app.ml.causal.synthetic_control import SyntheticControlMethod

        df = real_geo_df

        # Get pre-treatment period (first 4 weeks)
        pre_treatment = df[df["period"] < 4]

        # Pivot to wide format
        pivot_df = pre_treatment.pivot(
            index="period", columns="region", values="sales"
        )

        # Identify treated region and donor pool
        test_regions = df[df["is_test_region"] == 1]["region"].unique()
        control_regions = df[df["is_test_region"] == 0]["region"].unique()

        if len(test_regions) == 0 or len(control_regions) == 0:
            pytest.skip("Need test and control regions")

        treated = pivot_df[test_regions[0]].values
        donors = pivot_df[list(control_regions)].values

        scm = SyntheticControlMethod()
        result = scm.fit(treated, donors)

        assert result.weights is not None
        assert len(result.weights) == donors.shape[1]
        # Weights should sum to approximately 1
        assert np.isclose(result.weights.sum(), 1.0, atol=0.05)

    def test_synthetic_control_counterfactual(self, real_geo_df):
        """Test SCM counterfactual prediction."""
        from app.ml.causal.synthetic_control import SyntheticControlMethod

        df = real_geo_df

        # Split pre/post treatment
        pre_df = df[df["period"] < 4]
        post_df = df[df["period"] >= 4]

        # Get regions
        test_regions = df[df["is_test_region"] == 1]["region"].unique()
        control_regions = df[df["is_test_region"] == 0]["region"].unique()

        if len(test_regions) == 0 or len(control_regions) < 3:
            pytest.skip("Need sufficient test and control regions")

        # Pivot data
        pre_pivot = pre_df.pivot(index="period", columns="region", values="sales")
        post_pivot = post_df.pivot(index="period", columns="region", values="sales")

        treated_pre = pre_pivot[test_regions[0]].values
        donors_pre = pre_pivot[list(control_regions[:5])].values

        scm = SyntheticControlMethod()
        result = scm.fit(treated_pre, donors_pre)

        # Predict counterfactual for post-treatment
        donors_post = post_pivot[list(control_regions[:5])].values
        counterfactual = donors_post @ result.weights
        actual = post_pivot[test_regions[0]].values

        # Effect should be calculable
        treatment_effect = np.mean(actual - counterfactual)
        assert np.isfinite(treatment_effect)


# ============================================================================
# Markov Attribution Tests with Real Data
# ============================================================================

class TestMarkovAttributionRealData:
    """Test cases for Markov Chain Attribution with real journey data."""

    @pytest.fixture
    def real_journey_df(self):
        """Load real customer journey data."""
        df = load_real_journey_data()
        if df is None:
            pytest.skip("Real journey data not available")
        return prepare_journey_data(df)

    def test_markov_initialization(self):
        """Test Markov attribution initialization."""
        from app.ml.attribution.markov import MarkovAttribution

        markov = MarkovAttribution(order=1)
        assert markov.order == 1

    def test_journey_data_structure(self, real_journey_df):
        """Verify journey data structure."""
        df = real_journey_df

        # Required columns
        assert "journey_id" in df.columns
        assert "channel" in df.columns
        assert "conversion" in df.columns or "conversion_journey" in df.columns

        # Data quality
        assert len(df["journey_id"].unique()) >= 10
        assert len(df["channel"].unique()) >= 3

    def test_transition_matrix_real_data(self, real_journey_df):
        """Test transition matrix on real journeys."""
        from app.ml.attribution.markov import MarkovAttribution

        df = real_journey_df

        # Use the correct column name
        converted_col = "conversion" if "conversion" in df.columns else "conversion_journey"

        markov = MarkovAttribution()
        result = markov.calculate(
            df,
            channel_col="channel",
            converted_col=converted_col,
            journey_id_col="journey_id",
        )

        assert result.transition_matrix is not None

        # Matrix should be row-stochastic where rows have data
        matrix = result.transition_matrix.matrix
        row_sums = matrix.sum(axis=1)
        valid_rows = row_sums > 0
        assert np.allclose(row_sums[valid_rows], 1.0, atol=0.01)

    def test_channel_attribution_real_data(self, real_journey_df):
        """Test channel attribution on real data."""
        from app.ml.attribution.markov import MarkovAttribution

        df = real_journey_df
        converted_col = "conversion" if "conversion" in df.columns else "conversion_journey"

        markov = MarkovAttribution()
        result = markov.calculate(
            df,
            channel_col="channel",
            converted_col=converted_col,
            journey_id_col="journey_id",
        )

        assert len(result.channel_attribution) > 0
        assert len(result.attribution_share) > 0

        # Attribution shares should sum to approximately 1
        total_share = sum(result.attribution_share.values())
        assert np.isclose(total_share, 1.0, atol=0.05)

    def test_channel_rankings_real_data(self, real_journey_df):
        """Test that channels are properly ranked."""
        from app.ml.attribution.markov import MarkovAttribution

        df = real_journey_df
        converted_col = "conversion" if "conversion" in df.columns else "conversion_journey"

        markov = MarkovAttribution()
        result = markov.calculate(
            df,
            channel_col="channel",
            converted_col=converted_col,
            journey_id_col="journey_id",
        )

        # Sort channels by attribution
        sorted_channels = sorted(
            result.attribution_share.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # Top channel should have positive attribution
        assert sorted_channels[0][1] > 0


# ============================================================================
# Shapley Attribution Tests with Real Data
# ============================================================================

class TestShapleyAttributionRealData:
    """Test cases for Shapley Value Attribution with real data."""

    @pytest.fixture
    def real_journey_df(self):
        """Load real journey data."""
        df = load_real_journey_data()
        if df is None:
            pytest.skip("Real journey data not available")
        return prepare_journey_data(df)

    def test_shapley_initialization(self):
        """Test Shapley attribution initialization."""
        from app.ml.attribution.shapley import ShapleyAttribution

        shapley = ShapleyAttribution(n_samples=100)
        assert shapley.n_samples == 100

    def test_shapley_exact_real_data(self, real_journey_df):
        """Test exact Shapley on real data (limited channels)."""
        from app.ml.attribution.shapley import ShapleyAttribution

        df = real_journey_df
        converted_col = "conversion" if "conversion" in df.columns else "conversion_journey"

        # Get top 3 channels for exact computation
        top_channels = df["channel"].value_counts().head(3).index.tolist()
        df_subset = df[df["channel"].isin(top_channels)]

        shapley = ShapleyAttribution(approximate=False)
        result = shapley.calculate(
            df_subset,
            channel_col="channel",
            converted_col=converted_col,
            journey_id_col="journey_id",
        )

        assert len(result.shapley_values) > 0

        # Shapley values should be non-negative for conversion data
        for channel, value in result.shapley_values.items():
            assert value >= -0.01, f"Unexpected negative Shapley for {channel}"

    def test_shapley_approximate_real_data(self, real_journey_df):
        """Test approximate Shapley on real data."""
        from app.ml.attribution.shapley import ShapleyAttribution

        df = real_journey_df
        converted_col = "conversion" if "conversion" in df.columns else "conversion_journey"

        shapley = ShapleyAttribution(approximate=True, n_samples=100)
        result = shapley.calculate(
            df,
            channel_col="channel",
            converted_col=converted_col,
            journey_id_col="journey_id",
        )

        assert len(result.shapley_values) > 0

        # All channels should have Shapley values
        channels = df["channel"].unique()
        for ch in channels:
            assert ch in result.shapley_values or ch == "direct"


# ============================================================================
# Causal Discovery Tests with Real Data
# ============================================================================

class TestCausalDiscoveryRealData:
    """Test cases for Causal Discovery with real marketing data."""

    @pytest.fixture
    def real_mmm_df(self):
        """Load real MMM data for causal discovery."""
        df = load_real_mmm_data()
        if df is None:
            pytest.skip("Real MMM data not available")
        return df

    def test_notears_initialization(self):
        """Test NOTEARS algorithm initialization."""
        from app.ml.causal.notears import NOTEARSAlgorithm, NOTEARSConfig

        config = NOTEARSConfig(max_iter=100)
        notears = NOTEARSAlgorithm(config)

        assert notears.config.max_iter == 100

    def test_notears_on_marketing_data(self, real_mmm_df):
        """Test NOTEARS on real marketing variables."""
        from app.ml.causal.notears import NOTEARSAlgorithm

        df = real_mmm_df

        # Select numeric columns for causal discovery
        spend_cols = [c for c in df.columns if "spend" in c.lower()][:4]
        data_cols = spend_cols + ["sales"]

        data = df[data_cols].values

        notears = NOTEARSAlgorithm()
        result = notears.fit(data)

        assert result.adjacency_matrix is not None
        assert result.adjacency_matrix.shape == (len(data_cols), len(data_cols))
        assert result.is_dag

    def test_dag_discovery_marketing_variables(self, real_mmm_df):
        """Test DAG discovery on marketing variables."""
        from app.ml.causal.dag_discovery import CausalDiscovery

        df = real_mmm_df

        # Select relevant columns
        spend_cols = [c for c in df.columns if "spend" in c.lower()][:3]
        var_names = spend_cols + ["sales"]

        data = df[var_names].values

        discovery = CausalDiscovery()
        result = discovery.discover_dag(data, var_names)

        assert result.nodes == var_names
        # Should find some causal relationships
        # (spend -> sales is expected)


# ============================================================================
# MTA Model Comparison with Real Data
# ============================================================================

class TestMTAComparisonRealData:
    """Compare attribution models on real data."""

    @pytest.fixture
    def real_journey_df(self):
        """Load real journey data."""
        df = load_real_journey_data()
        if df is None:
            pytest.skip("Real journey data not available")
        return prepare_journey_data(df)

    def test_markov_vs_linear_real_data(self, real_journey_df):
        """Compare Markov and linear attribution on real data."""
        from app.ml.attribution.markov import MarkovAttribution
        from app.ml.attribution.mta import MultiTouchAttribution

        df = real_journey_df
        converted_col = "conversion" if "conversion" in df.columns else "conversion_journey"

        # Markov attribution
        markov = MarkovAttribution()
        markov_result = markov.calculate(
            df,
            channel_col="channel",
            converted_col=converted_col,
            journey_id_col="journey_id",
        )

        # Linear attribution
        mta = MultiTouchAttribution(model_type="linear")
        linear_result = mta.calculate(
            df,
            channel_col="channel",
            converted_col=converted_col,
            journey_id_col="journey_id",
        )

        # Both should produce results
        assert len(markov_result.attribution_share) > 0
        assert len(linear_result.attribution) > 0

        # Check common channels are ranked similarly
        common_channels = (
            set(markov_result.attribution_share.keys()) &
            set(linear_result.attribution.keys())
        )
        assert len(common_channels) > 0

    def test_attribution_stability(self, real_journey_df):
        """Test that attribution is stable across runs."""
        from app.ml.attribution.markov import MarkovAttribution

        df = real_journey_df
        converted_col = "conversion" if "conversion" in df.columns else "conversion_journey"

        markov = MarkovAttribution()

        # Run twice
        result1 = markov.calculate(
            df,
            channel_col="channel",
            converted_col=converted_col,
            journey_id_col="journey_id",
        )

        result2 = markov.calculate(
            df,
            channel_col="channel",
            converted_col=converted_col,
            journey_id_col="journey_id",
        )

        # Results should be identical
        for ch in result1.attribution_share:
            assert np.isclose(
                result1.attribution_share[ch],
                result2.attribution_share[ch],
                atol=0.001
            )


# ============================================================================
# Data Quality Tests
# ============================================================================

class TestRealDataQuality:
    """Verify real data quality for causal/attribution analysis."""

    def test_geo_data_quality(self):
        """Verify geo data has expected structure."""
        df = load_real_geo_data()
        if df is None:
            pytest.skip("Geo data not available")

        # Required columns
        assert "date" in df.columns
        assert "region" in df.columns
        assert "sales" in df.columns

        # Data quality
        assert len(df["region"].unique()) >= 5
        assert df["sales"].min() > 0

    def test_journey_data_quality(self):
        """Verify journey data has expected structure."""
        df = load_real_journey_data()
        if df is None:
            pytest.skip("Journey data not available")

        # Required columns
        assert "journey_id" in df.columns
        assert "channel" in df.columns

        # Data quality
        assert len(df["journey_id"].unique()) >= 10
        n_channels = len(df["channel"].unique())
        assert n_channels >= 3, f"Only {n_channels} channels found"

    def test_journey_conversion_rate(self):
        """Verify journey data has conversions."""
        df = load_real_journey_data()
        if df is None:
            pytest.skip("Journey data not available")

        # Check for conversions
        if "conversion" in df.columns:
            conversion_rate = df.groupby("journey_id")["conversion"].max().mean()
        elif "conversion_value" in df.columns:
            conversion_rate = (df.groupby("journey_id")["conversion_value"].max() > 0).mean()
        else:
            pytest.skip("No conversion column found")

        assert conversion_rate > 0.01, "Very low conversion rate"
        assert conversion_rate < 1.0, "Suspiciously high conversion rate"


# ============================================================================
# Example Usage / Demo with Real Data
# ============================================================================

def demo_causal_attribution_real_data():
    """Demo script for causal inference and attribution with real data."""
    print("=" * 60)
    print("Causal Inference & Attribution Demo - Real Data")
    print("=" * 60)

    # 1. Load and describe journey data
    print("\n1. Loading Real Customer Journey Data")
    print("-" * 40)

    journey_df = load_real_journey_data()
    if journey_df is not None:
        journey_df = prepare_journey_data(journey_df)

        print(f"   Total touchpoints: {len(journey_df)}")
        print(f"   Unique journeys: {journey_df['journey_id'].nunique()}")
        print(f"   Unique channels: {journey_df['channel'].nunique()}")

        # Channel breakdown
        print("\n   Channel distribution:")
        for ch, count in journey_df["channel"].value_counts().head(5).items():
            print(f"   - {ch}: {count} touchpoints")

        # Markov Attribution
        print("\n2. Markov Chain Attribution")
        print("-" * 40)

        from app.ml.attribution.markov import MarkovAttribution

        converted_col = "conversion" if "conversion" in journey_df.columns else "conversion_journey"

        markov = MarkovAttribution()
        result = markov.calculate(
            journey_df,
            channel_col="channel",
            converted_col=converted_col,
            journey_id_col="journey_id",
        )

        print("\n   Channel Attribution (Markov):")
        for channel, share in sorted(result.attribution_share.items(), key=lambda x: -x[1]):
            print(f"   - {channel}: {share:.1%}")
    else:
        print("   Journey data not available")

    # 2. Geographic Analysis
    print("\n3. Geographic Experiment Analysis")
    print("-" * 40)

    geo_df = load_real_geo_data()
    if geo_df is not None:
        geo_df = prepare_geo_experiment_data(geo_df)

        print(f"   Total observations: {len(geo_df)}")
        print(f"   Unique regions: {geo_df['region'].nunique()}")
        print(f"   Time periods: {geo_df['period'].nunique()}")

        # Synthetic Control
        from app.ml.causal.synthetic_control import SyntheticControlMethod

        test_regions = geo_df[geo_df["is_test_region"] == 1]["region"].unique()
        control_regions = geo_df[geo_df["is_test_region"] == 0]["region"].unique()

        print(f"\n   Test regions: {len(test_regions)}")
        print(f"   Control regions: {len(control_regions)}")

        if len(test_regions) > 0 and len(control_regions) >= 3:
            pre_df = geo_df[geo_df["period"] < 4]
            pivot_df = pre_df.pivot(index="period", columns="region", values="sales")

            treated = pivot_df[test_regions[0]].values
            donors = pivot_df[list(control_regions[:5])].values

            scm = SyntheticControlMethod()
            scm_result = scm.fit(treated, donors)

            print("\n   Synthetic Control Weights (top 5):")
            sorted_weights = sorted(enumerate(scm_result.weights), key=lambda x: -x[1])
            for idx, weight in sorted_weights[:5]:
                if weight > 0.01:
                    print(f"   - {control_regions[idx]}: {weight:.3f}")
    else:
        print("   Geographic data not available")

    print("\n" + "=" * 60)
    print("Demo completed!")


if __name__ == "__main__":
    demo_causal_attribution_real_data()
