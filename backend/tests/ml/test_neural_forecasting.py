"""
Test Cases for Neural Forecasting Models

Tests for N-BEATS, TFT, DeepAR, and Neural MMM with REAL marketing data.
Uses actual marketing/sales datasets from the fixtures directory.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# Skip tests if PyTorch not available
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

# Fixtures directory
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


# ============================================================================
# Real Data Loading Utilities
# ============================================================================

def load_real_mmm_data() -> pd.DataFrame:
    """Load real marketing mix modeling data."""
    csv_path = FIXTURES_DIR / "real_mmm_data.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path, parse_dates=["date"])
        return df
    # Fallback to sample data
    csv_path = FIXTURES_DIR / "sample_mmm_data.csv"
    df = pd.read_csv(csv_path, parse_dates=["date"])
    return df


def load_real_daily_sales() -> pd.DataFrame:
    """Load real daily sales time series data."""
    csv_path = FIXTURES_DIR / "real_daily_sales.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path, parse_dates=["date"])
        return df
    return None


def prepare_time_series_from_mmm(df: pd.DataFrame) -> np.ndarray:
    """Extract time series from MMM data for forecasting."""
    sales = df["sales"].values.astype(np.float32)
    return sales


def prepare_time_series_from_daily(df: pd.DataFrame) -> np.ndarray:
    """Extract time series from daily sales data."""
    if df is None:
        return None
    sales = df["daily_sales"].values.astype(np.float32)
    return sales


def prepare_mmm_features(df: pd.DataFrame) -> tuple:
    """Prepare features and target for MMM modeling."""
    # Feature columns
    spend_cols = [col for col in df.columns if "spend" in col.lower()]

    X = df[spend_cols].values.astype(np.float32)
    y = df["sales"].values.astype(np.float32)

    return X, y, spend_cols


# ============================================================================
# N-BEATS Tests with Real Data
# ============================================================================

@pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
class TestNBEATSRealData:
    """Test cases for N-BEATS forecasting model with real data."""

    @pytest.fixture
    def real_sales_data(self):
        """Load real sales time series data."""
        df = load_real_mmm_data()
        return prepare_time_series_from_mmm(df)

    @pytest.fixture
    def real_daily_data(self):
        """Load real daily sales data if available."""
        df = load_real_daily_sales()
        return prepare_time_series_from_daily(df)

    def test_nbeats_config_defaults(self):
        """Test default configuration."""
        from app.ml.models.nbeats_forecast import NBeatsConfig

        config = NBeatsConfig()
        assert config.lookback_length == 52
        assert config.horizon == 12
        assert config.num_blocks_per_stack == 3
        assert "trend" in config.stack_types

    def test_nbeats_initialization(self):
        """Test model initialization."""
        from app.ml.models.nbeats_forecast import NBeatsForecaster, NBeatsConfig

        config = NBeatsConfig(
            lookback_length=24,
            horizon=6,
            epochs=2,
        )
        forecaster = NBeatsForecaster(config)

        assert forecaster.model is None
        assert forecaster.config.horizon == 6

    def test_nbeats_fit_predict_real_weekly(self, real_sales_data):
        """Test N-BEATS on real weekly sales data."""
        from app.ml.models.nbeats_forecast import NBeatsForecaster, NBeatsConfig

        data = real_sales_data
        assert len(data) >= 40, "Need at least 40 weeks of data"

        # Split data
        train_size = len(data) - 8
        train = data[:train_size]

        config = NBeatsConfig(
            lookback_length=min(20, train_size - 5),
            horizon=4,
            epochs=10,
            layer_width=32,
            num_layers=2,
        )

        forecaster = NBeatsForecaster(config)
        forecaster.fit(train, verbose=False)

        # Predict
        forecast = forecaster.predict(train)

        assert forecast.forecast.shape == (4,)
        assert not np.isnan(forecast.forecast).any()
        # Forecast should be in reasonable range for sales data
        assert np.all(forecast.forecast > 0)

    def test_nbeats_fit_predict_real_daily(self, real_daily_data):
        """Test N-BEATS on real daily sales data."""
        from app.ml.models.nbeats_forecast import NBeatsForecaster, NBeatsConfig

        if real_daily_data is None:
            pytest.skip("Daily sales data not available")

        data = real_daily_data
        assert len(data) >= 60, "Need at least 60 days of data"

        train_size = len(data) - 14
        train = data[:train_size]

        config = NBeatsConfig(
            lookback_length=28,  # 4 weeks lookback
            horizon=7,           # 1 week forecast
            epochs=15,
            layer_width=64,
            num_layers=2,
            stack_types=["trend", "seasonality"],
        )

        forecaster = NBeatsForecaster(config)
        forecaster.fit(train, verbose=False)

        forecast = forecaster.predict(train, return_components=True)

        assert forecast.forecast.shape == (7,)
        assert not np.isnan(forecast.forecast).any()
        # Daily sales should be positive
        assert np.all(forecast.forecast > 0)

    def test_nbeats_interpretable_components_real_data(self, real_sales_data):
        """Test interpretable decomposition on real data."""
        from app.ml.models.nbeats_forecast import NBeatsForecaster, NBeatsConfig

        data = real_sales_data
        train = data[:-8]

        config = NBeatsConfig(
            lookback_length=16,
            horizon=4,
            stack_types=["trend", "seasonality"],
            epochs=10,
        )

        forecaster = NBeatsForecaster(config)
        forecaster.fit(train, verbose=False)

        forecast = forecaster.predict(train, return_components=True)

        assert forecast.forecast is not None
        # Components should capture trend and seasonality in real data
        assert forecast.trend_component is not None or forecast.seasonal_component is not None

    def test_nbeats_prediction_intervals_real_data(self, real_sales_data):
        """Test prediction intervals on real data."""
        from app.ml.models.nbeats_forecast import NBeatsForecaster, NBeatsConfig

        data = real_sales_data
        train = data[:-8]

        config = NBeatsConfig(
            lookback_length=16,
            horizon=4,
            epochs=10,
            dropout=0.1,
        )

        forecaster = NBeatsForecaster(config)
        forecaster.fit(train, verbose=False)

        point, lower, upper = forecaster.predict_intervals(
            train, n_samples=20, confidence=0.9
        )

        assert point.shape == (4,)
        assert lower.shape == (4,)
        assert upper.shape == (4,)
        # Intervals should be properly ordered
        assert np.all(lower <= point + 1)  # Small tolerance
        assert np.all(point <= upper + 1)


# ============================================================================
# TFT Tests with Real Data
# ============================================================================

@pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
class TestTFTRealData:
    """Test cases for Temporal Fusion Transformer with real data."""

    @pytest.fixture
    def real_mmm_df(self):
        """Load real MMM dataframe."""
        return load_real_mmm_data()

    def test_tft_config_defaults(self):
        """Test default configuration."""
        from app.ml.models.tft_forecast import TFTConfig

        config = TFTConfig()
        assert config.hidden_size == 64
        assert config.num_heads == 4
        assert len(config.quantiles) == 3

    def test_tft_fit_predict_real_data(self, real_mmm_df):
        """Test TFT on real marketing data."""
        from app.ml.models.tft_forecast import TFTForecaster, TFTConfig

        df = real_mmm_df
        data = df["sales"].values.astype(np.float32)

        train_size = len(data) - 8
        train = data[:train_size]

        config = TFTConfig(
            lookback_length=16,
            horizon=4,
            epochs=10,
            hidden_size=32,
        )

        forecaster = TFTForecaster(config)
        forecaster.fit(train, verbose=False)

        forecast = forecaster.predict(train)

        assert forecast.point_forecast.shape == (4,)
        assert len(forecast.quantile_forecasts) == 3
        # Forecast should be positive for sales data
        assert np.all(forecast.point_forecast > 0)

    def test_tft_quantile_outputs_real_data(self, real_mmm_df):
        """Test quantile predictions on real data."""
        from app.ml.models.tft_forecast import TFTForecaster, TFTConfig

        df = real_mmm_df
        data = df["sales"].values.astype(np.float32)
        train = data[:-8]

        config = TFTConfig(
            lookback_length=16,
            horizon=4,
            quantiles=[0.1, 0.5, 0.9],
            epochs=10,
        )

        forecaster = TFTForecaster(config)
        forecaster.fit(train, verbose=False)

        forecast = forecaster.predict(train)

        q10 = forecast.quantile_forecasts[0.1]
        q50 = forecast.quantile_forecasts[0.5]
        q90 = forecast.quantile_forecasts[0.9]

        # Quantiles should be generally ordered
        assert np.mean(q10 <= q50) > 0.5
        assert np.mean(q50 <= q90) > 0.5


# ============================================================================
# DeepAR Tests with Real Data
# ============================================================================

@pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
class TestDeepARRealData:
    """Test cases for DeepAR with real data."""

    @pytest.fixture
    def real_sales(self):
        """Load real sales data."""
        df = load_real_mmm_data()
        return df["sales"].values.astype(np.float32)

    def test_deepar_config_defaults(self):
        """Test default configuration."""
        from app.ml.models.deepar_forecast import DeepARConfig

        config = DeepARConfig()
        assert config.hidden_size == 64
        assert config.distribution == "normal"

    def test_deepar_fit_predict_real_data(self, real_sales):
        """Test DeepAR on real sales data."""
        from app.ml.models.deepar_forecast import DeepARForecaster, DeepARConfig

        data = real_sales
        train = data[:-8]

        config = DeepARConfig(
            lookback_length=16,
            horizon=4,
            epochs=10,
            hidden_size=32,
        )

        forecaster = DeepARForecaster(config)
        forecaster.fit(train, verbose=False)

        forecast = forecaster.predict(train, n_samples=50)

        assert forecast.mean.shape == (4,)
        assert forecast.std.shape == (4,)
        assert forecast.samples.shape == (50, 4)
        # Mean forecast should be positive
        assert np.all(forecast.mean > 0)

    def test_deepar_prediction_intervals_real_data(self, real_sales):
        """Test prediction intervals on real data."""
        from app.ml.models.deepar_forecast import DeepARForecaster, DeepARConfig

        data = real_sales
        train = data[:-8]

        config = DeepARConfig(
            lookback_length=16,
            horizon=4,
            epochs=10,
        )

        forecaster = DeepARForecaster(config)
        forecaster.fit(train, verbose=False)

        forecast = forecaster.predict(train, n_samples=100)

        assert forecast.lower_50 is not None
        assert forecast.upper_50 is not None
        assert forecast.lower_90 is not None
        assert forecast.upper_90 is not None

        # 90% interval should be wider than 50%
        width_50 = forecast.upper_50 - forecast.lower_50
        width_90 = forecast.upper_90 - forecast.lower_90
        assert np.all(width_90 >= width_50 - 1)  # Small tolerance

    def test_deepar_student_t_distribution(self, real_sales):
        """Test Student-t distribution for heavy tails."""
        from app.ml.models.deepar_forecast import DeepARForecaster, DeepARConfig

        data = real_sales
        train = data[:-8]

        config = DeepARConfig(
            lookback_length=16,
            horizon=4,
            epochs=8,
            distribution="student_t",
        )

        forecaster = DeepARForecaster(config)
        forecaster.fit(train, verbose=False)

        forecast = forecaster.predict(train, n_samples=50)
        assert forecast.mean.shape == (4,)


# ============================================================================
# Neural MMM Tests with Real Data
# ============================================================================

@pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
class TestNeuralMMMRealData:
    """Test cases for Neural Marketing Mix Model with real data."""

    @pytest.fixture
    def real_mmm_features(self):
        """Load real MMM features and target."""
        df = load_real_mmm_data()
        return prepare_mmm_features(df)

    def test_neural_mmm_config(self):
        """Test configuration."""
        from app.ml.models.neural_mmm import NeuralMMMConfig

        config = NeuralMMMConfig(
            n_channels=6,
            hidden_dims=[64, 32],
        )
        assert config.n_channels == 6

    def test_adstock_layer_with_real_scale(self, real_mmm_features):
        """Test adstock with real data scale."""
        from app.ml.models.neural_mmm import DifferentiableAdstock

        X, y, channels = real_mmm_features
        n_channels = X.shape[1]

        adstock = DifferentiableAdstock(
            n_channels=n_channels,
            max_lag=4,
            adstock_type="geometric",
        )

        # Convert to tensor with batch dimension
        x = torch.tensor(X).unsqueeze(0)  # (1, time, channels)
        output = adstock(x)

        assert output.shape == x.shape
        assert not torch.isnan(output).any()

    def test_saturation_layer_with_real_scale(self, real_mmm_features):
        """Test saturation with real spend values."""
        from app.ml.models.neural_mmm import DifferentiableSaturation

        X, y, channels = real_mmm_features
        n_channels = X.shape[1]

        saturation = DifferentiableSaturation(
            n_channels=n_channels,
            saturation_type="hill",
        )

        x = torch.tensor(X).unsqueeze(0)
        output = saturation(x)

        assert output.shape == x.shape
        assert (output >= 0).all()

    def test_neural_mmm_full_model_real_data(self, real_mmm_features):
        """Test full Neural MMM on real data."""
        from app.ml.models.neural_mmm import NeuralMMMModel, NeuralMMMConfig

        X, y, channels = real_mmm_features
        n_channels = X.shape[1]

        config = NeuralMMMConfig(
            n_channels=n_channels,
            hidden_dims=[32, 16],
            adstock_type="geometric",
            saturation_type="hill",
        )

        model = NeuralMMMModel(config)

        # Forward pass
        x = torch.tensor(X).unsqueeze(0)
        y_pred, components = model(x)

        assert y_pred.shape[1] == X.shape[0]
        assert "channel_contributions" in components
        assert "adstock_output" in components

    def test_neural_mmm_training_real_data(self, real_mmm_features):
        """Test Neural MMM training convergence on real data."""
        from app.ml.models.neural_mmm import (
            NeuralMMMModel,
            NeuralMMMTrainer,
            NeuralMMMConfig,
        )

        X, y, channels = real_mmm_features
        n_channels = X.shape[1]

        # Normalize for training stability
        X_norm = X / X.max(axis=0, keepdims=True)
        y_norm = y / y.max()

        config = NeuralMMMConfig(
            n_channels=n_channels,
            hidden_dims=[32, 16],
        )

        model = NeuralMMMModel(config)
        trainer = NeuralMMMTrainer(model, learning_rate=0.01)

        history = trainer.train(
            X=X_norm.astype(np.float32),
            y=y_norm.astype(np.float32),
            epochs=20,
            batch_size=16,
            verbose=False,
        )

        assert len(history["train_loss"]) == 20
        # Loss should decrease
        assert history["train_loss"][-1] < history["train_loss"][0]

    def test_neural_mmm_channel_contributions(self, real_mmm_features):
        """Test extracting channel contributions from trained model."""
        from app.ml.models.neural_mmm import (
            NeuralMMMModel,
            NeuralMMMTrainer,
            NeuralMMMConfig,
        )

        X, y, channels = real_mmm_features
        n_channels = X.shape[1]

        config = NeuralMMMConfig(
            n_channels=n_channels,
            hidden_dims=[32],
        )

        model = NeuralMMMModel(config)
        trainer = NeuralMMMTrainer(model, learning_rate=0.01)

        # Quick training
        trainer.train(
            X=X.astype(np.float32),
            y=y.astype(np.float32),
            epochs=5,
            batch_size=16,
            verbose=False,
        )

        # Get contributions
        model.eval()
        with torch.no_grad():
            x = torch.tensor(X.astype(np.float32)).unsqueeze(0)
            _, components = model(x)

        contributions = components["channel_contributions"]
        assert contributions.shape[2] == n_channels

        # Contributions should be non-negative after saturation
        contrib_np = contributions.squeeze(0).numpy()
        assert np.all(contrib_np >= 0)


# ============================================================================
# Model Comparison on Real Data
# ============================================================================

@pytest.mark.skipif(not TORCH_AVAILABLE, reason="PyTorch not available")
class TestModelComparisonRealData:
    """Compare different forecasting models on same real data."""

    def test_forecast_comparison_real_data(self):
        """Compare N-BEATS and DeepAR on real sales data."""
        from app.ml.models.nbeats_forecast import NBeatsForecaster, NBeatsConfig
        from app.ml.models.deepar_forecast import DeepARForecaster, DeepARConfig

        # Load real data
        df = load_real_mmm_data()
        data = df["sales"].values.astype(np.float32)

        train = data[:-8]
        test = data[-8:-4]  # 4-week test period

        # Train N-BEATS
        nbeats_config = NBeatsConfig(
            lookback_length=16,
            horizon=4,
            epochs=15,
        )
        nbeats = NBeatsForecaster(nbeats_config)
        nbeats.fit(train, verbose=False)
        nbeats_forecast = nbeats.predict(train)

        # Train DeepAR
        deepar_config = DeepARConfig(
            lookback_length=16,
            horizon=4,
            epochs=15,
        )
        deepar = DeepARForecaster(deepar_config)
        deepar.fit(train, verbose=False)
        deepar_forecast = deepar.predict(train, n_samples=100)

        # Both should produce reasonable forecasts
        assert nbeats_forecast.forecast.shape == (4,)
        assert deepar_forecast.mean.shape == (4,)

        # Forecasts should be positive for sales
        assert np.all(nbeats_forecast.forecast > 0)
        assert np.all(deepar_forecast.mean > 0)

        # Calculate MAE against test set
        nbeats_mae = np.mean(np.abs(nbeats_forecast.forecast - test))
        deepar_mae = np.mean(np.abs(deepar_forecast.mean - test))

        # Both MAEs should be finite
        assert np.isfinite(nbeats_mae)
        assert np.isfinite(deepar_mae)

    def test_multi_horizon_evaluation(self):
        """Evaluate models on multiple forecast horizons."""
        from app.ml.models.nbeats_forecast import NBeatsForecaster, NBeatsConfig

        df = load_real_mmm_data()
        data = df["sales"].values.astype(np.float32)

        horizons = [2, 4, 8]
        results = {}

        for horizon in horizons:
            train = data[:-horizon]

            config = NBeatsConfig(
                lookback_length=16,
                horizon=horizon,
                epochs=10,
            )
            forecaster = NBeatsForecaster(config)
            forecaster.fit(train, verbose=False)

            forecast = forecaster.predict(train)
            test = data[-horizon:]

            mae = np.mean(np.abs(forecast.forecast - test))
            results[horizon] = mae

        # All horizons should produce finite MAE
        for h, mae in results.items():
            assert np.isfinite(mae), f"Non-finite MAE for horizon {h}"


# ============================================================================
# Data Quality Tests
# ============================================================================

class TestRealDataQuality:
    """Verify real data quality before model testing."""

    def test_mmm_data_structure(self):
        """Verify MMM data has expected structure."""
        df = load_real_mmm_data()

        # Required columns
        assert "date" in df.columns
        assert "sales" in df.columns

        # Should have spend columns
        spend_cols = [c for c in df.columns if "spend" in c.lower()]
        assert len(spend_cols) >= 3, "Need at least 3 spend channels"

        # Data quality checks
        assert len(df) >= 26, "Need at least 26 weeks of data"
        assert df["sales"].min() > 0, "Sales should be positive"
        assert not df["sales"].isna().any(), "No missing sales values"

    def test_daily_data_structure(self):
        """Verify daily sales data structure."""
        df = load_real_daily_sales()

        if df is None:
            pytest.skip("Daily data not available")

        assert "date" in df.columns
        assert "daily_sales" in df.columns

        # Data quality
        assert len(df) >= 30, "Need at least 30 days of data"
        assert df["daily_sales"].min() > 0, "Sales should be positive"

    def test_data_time_ordering(self):
        """Verify data is properly time-ordered."""
        df = load_real_mmm_data()

        dates = pd.to_datetime(df["date"])
        assert dates.is_monotonic_increasing, "Data should be sorted by date"


# ============================================================================
# Example Usage / Demo with Real Data
# ============================================================================

def demo_neural_forecasting_real_data():
    """Demo script showing neural forecasting on real data."""
    print("=" * 60)
    print("Neural Forecasting Models Demo - Real Data")
    print("=" * 60)

    if not TORCH_AVAILABLE:
        print("PyTorch not available. Install with: pip install torch")
        return

    # Load real data
    print("\n1. Loading real marketing data...")
    df = load_real_mmm_data()
    data = df["sales"].values.astype(np.float32)

    print(f"   Dataset: {len(df)} weeks of sales data")
    print(f"   Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"   Sales range: ${data.min():,.0f} - ${data.max():,.0f}")

    # Split data
    train_size = len(data) - 8
    train = data[:train_size]
    test = data[train_size:]

    print(f"   Training: {train_size} weeks")
    print(f"   Testing: {len(test)} weeks")

    from app.ml.models.nbeats_forecast import NBeatsForecaster, NBeatsConfig
    from app.ml.models.deepar_forecast import DeepARForecaster, DeepARConfig

    # N-BEATS
    print("\n2. Training N-BEATS model...")
    nbeats_config = NBeatsConfig(
        lookback_length=20,
        horizon=8,
        epochs=30,
        stack_types=["trend", "seasonality"],
    )
    nbeats = NBeatsForecaster(nbeats_config)
    nbeats.fit(train, verbose=True)

    forecast = nbeats.predict(train)
    nbeats_mae = np.mean(np.abs(forecast.forecast - test))
    print(f"   N-BEATS MAE: ${nbeats_mae:,.0f}")

    # DeepAR
    print("\n3. Training DeepAR model...")
    deepar_config = DeepARConfig(
        lookback_length=20,
        horizon=8,
        epochs=30,
    )
    deepar = DeepARForecaster(deepar_config)
    deepar.fit(train, verbose=True)

    prob_forecast = deepar.predict(train, n_samples=200)
    deepar_mae = np.mean(np.abs(prob_forecast.mean - test))
    print(f"   DeepAR MAE: ${deepar_mae:,.0f}")
    print(f"   90% interval avg width: ${(prob_forecast.upper_90 - prob_forecast.lower_90).mean():,.0f}")

    print("\n" + "=" * 60)
    print("Demo completed!")


if __name__ == "__main__":
    demo_neural_forecasting_real_data()
