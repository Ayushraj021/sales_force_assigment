"""
N-BEATS Forecasting Model

Neural Basis Expansion Analysis for Time Series forecasting.
Implements the N-BEATS architecture from Oreshkin et al. (2019).
"""

from dataclasses import dataclass, field
from typing import Optional, Literal
import numpy as np

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torch.utils.data import DataLoader, TensorDataset
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


@dataclass
class NBeatsConfig:
    """Configuration for N-BEATS model."""

    # Architecture
    stack_types: list[Literal["trend", "seasonality", "generic"]] = field(
        default_factory=lambda: ["trend", "seasonality", "generic"]
    )
    num_blocks_per_stack: int = 3
    num_layers: int = 4
    layer_width: int = 256

    # Basis expansion
    trend_degree: int = 3
    seasonality_harmonics: int = 10

    # Input/Output
    lookback_length: int = 52  # Input window size
    horizon: int = 12  # Forecast horizon

    # Training
    learning_rate: float = 1e-3
    batch_size: int = 32
    epochs: int = 100
    early_stopping_patience: int = 10

    # Regularization
    dropout: float = 0.1
    weight_decay: float = 1e-5


@dataclass
class NBeatsForecast:
    """N-BEATS forecast result."""

    forecast: np.ndarray  # Point forecasts
    backcast: np.ndarray  # Backcast (fitted values)
    trend_component: Optional[np.ndarray] = None
    seasonal_component: Optional[np.ndarray] = None
    residual_component: Optional[np.ndarray] = None
    block_outputs: Optional[list[np.ndarray]] = None


if TORCH_AVAILABLE:

    class TrendBasis(nn.Module):
        """Trend basis functions using polynomial expansion."""

        def __init__(self, degree: int, lookback: int, horizon: int):
            super().__init__()
            self.degree = degree
            self.lookback = lookback
            self.horizon = horizon

            # Create polynomial basis matrices
            backcast_time = torch.arange(lookback).float() / lookback
            forecast_time = torch.arange(horizon).float() / horizon

            # Polynomial basis: [1, t, t^2, ..., t^degree]
            self.register_buffer(
                "backcast_basis",
                torch.stack([backcast_time**i for i in range(degree + 1)], dim=0)
            )
            self.register_buffer(
                "forecast_basis",
                torch.stack([forecast_time**i for i in range(degree + 1)], dim=0)
            )

        def forward(self, theta: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
            # theta: (batch, degree + 1)
            backcast = torch.einsum("bd,dl->bl", theta, self.backcast_basis)
            forecast = torch.einsum("bd,dl->bl", theta, self.forecast_basis)
            return backcast, forecast


    class SeasonalityBasis(nn.Module):
        """Seasonality basis functions using Fourier harmonics."""

        def __init__(self, harmonics: int, lookback: int, horizon: int):
            super().__init__()
            self.harmonics = harmonics
            self.lookback = lookback
            self.horizon = horizon
            self.num_terms = 2 * harmonics

            # Create Fourier basis
            backcast_time = 2 * np.pi * torch.arange(lookback).float() / lookback
            forecast_time = 2 * np.pi * torch.arange(horizon).float() / horizon

            backcast_basis = []
            forecast_basis = []

            for h in range(1, harmonics + 1):
                backcast_basis.extend([
                    torch.cos(h * backcast_time),
                    torch.sin(h * backcast_time)
                ])
                forecast_basis.extend([
                    torch.cos(h * forecast_time),
                    torch.sin(h * forecast_time)
                ])

            self.register_buffer("backcast_basis", torch.stack(backcast_basis, dim=0))
            self.register_buffer("forecast_basis", torch.stack(forecast_basis, dim=0))

        def forward(self, theta: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
            backcast = torch.einsum("bd,dl->bl", theta, self.backcast_basis)
            forecast = torch.einsum("bd,dl->bl", theta, self.forecast_basis)
            return backcast, forecast


    class GenericBasis(nn.Module):
        """Generic learnable basis functions."""

        def __init__(self, lookback: int, horizon: int, expansion_dim: int):
            super().__init__()
            self.backcast_linear = nn.Linear(expansion_dim, lookback)
            self.forecast_linear = nn.Linear(expansion_dim, horizon)

        def forward(self, theta: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
            backcast = self.backcast_linear(theta)
            forecast = self.forecast_linear(theta)
            return backcast, forecast


    class NBeatsBlock(nn.Module):
        """Single N-BEATS block with FC layers and basis expansion."""

        def __init__(
            self,
            input_size: int,
            theta_size: int,
            basis: nn.Module,
            num_layers: int = 4,
            layer_width: int = 256,
            dropout: float = 0.1,
        ):
            super().__init__()

            # FC stack
            layers = []
            layers.append(nn.Linear(input_size, layer_width))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(dropout))

            for _ in range(num_layers - 1):
                layers.append(nn.Linear(layer_width, layer_width))
                layers.append(nn.ReLU())
                layers.append(nn.Dropout(dropout))

            self.fc_stack = nn.Sequential(*layers)
            self.theta_layer = nn.Linear(layer_width, theta_size)
            self.basis = basis

        def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
            # FC processing
            features = self.fc_stack(x)
            theta = self.theta_layer(features)

            # Basis expansion
            backcast, forecast = self.basis(theta)

            return backcast, forecast


    class NBeatsStack(nn.Module):
        """Stack of N-BEATS blocks sharing the same basis type."""

        def __init__(
            self,
            stack_type: Literal["trend", "seasonality", "generic"],
            num_blocks: int,
            lookback: int,
            horizon: int,
            num_layers: int = 4,
            layer_width: int = 256,
            dropout: float = 0.1,
            trend_degree: int = 3,
            seasonality_harmonics: int = 10,
        ):
            super().__init__()
            self.stack_type = stack_type

            # Create basis and determine theta size
            if stack_type == "trend":
                theta_size = trend_degree + 1
                basis_fn = lambda: TrendBasis(trend_degree, lookback, horizon)
            elif stack_type == "seasonality":
                theta_size = 2 * seasonality_harmonics
                basis_fn = lambda: SeasonalityBasis(seasonality_harmonics, lookback, horizon)
            else:  # generic
                theta_size = lookback + horizon
                basis_fn = lambda: GenericBasis(lookback, horizon, theta_size)

            # Create blocks
            self.blocks = nn.ModuleList([
                NBeatsBlock(
                    input_size=lookback,
                    theta_size=theta_size,
                    basis=basis_fn(),
                    num_layers=num_layers,
                    layer_width=layer_width,
                    dropout=dropout,
                )
                for _ in range(num_blocks)
            ])

        def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, list]:
            residual = x
            total_forecast = torch.zeros(x.size(0), self.blocks[0].basis.forecast_linear.out_features if hasattr(self.blocks[0].basis, 'forecast_linear') else x.size(1), device=x.device)
            block_outputs = []

            for block in self.blocks:
                backcast, forecast = block(residual)
                residual = residual - backcast
                total_forecast = total_forecast + forecast
                block_outputs.append({
                    "backcast": backcast.detach(),
                    "forecast": forecast.detach(),
                })

            return residual, total_forecast, block_outputs


    class NBeatsModel(nn.Module):
        """
        N-BEATS: Neural Basis Expansion Analysis for Time Series.

        Paper: https://arxiv.org/abs/1905.10437
        """

        def __init__(self, config: NBeatsConfig):
            super().__init__()
            self.config = config

            # Create stacks
            self.stacks = nn.ModuleList([
                NBeatsStack(
                    stack_type=stack_type,
                    num_blocks=config.num_blocks_per_stack,
                    lookback=config.lookback_length,
                    horizon=config.horizon,
                    num_layers=config.num_layers,
                    layer_width=config.layer_width,
                    dropout=config.dropout,
                    trend_degree=config.trend_degree,
                    seasonality_harmonics=config.seasonality_harmonics,
                )
                for stack_type in config.stack_types
            ])

        def forward(
            self, x: torch.Tensor
        ) -> tuple[torch.Tensor, torch.Tensor, dict]:
            residual = x
            total_forecast = torch.zeros(
                x.size(0), self.config.horizon, device=x.device
            )
            stack_outputs = {}

            for i, stack in enumerate(self.stacks):
                residual, forecast, block_outputs = stack(residual)
                total_forecast = total_forecast + forecast
                stack_outputs[self.config.stack_types[i]] = {
                    "forecast": forecast.detach(),
                    "blocks": block_outputs,
                }

            return total_forecast, residual, stack_outputs


class NBeatsForecaster:
    """
    N-BEATS Time Series Forecaster.

    Implements training, prediction, and interpretable decomposition.

    Example:
        config = NBeatsConfig(horizon=12, lookback_length=52)
        forecaster = NBeatsForecaster(config)
        forecaster.fit(train_data)
        forecast = forecaster.predict(test_data)
    """

    def __init__(self, config: Optional[NBeatsConfig] = None):
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch is required for N-BEATS. Install with: pip install torch")

        self.config = config or NBeatsConfig()
        self.model: Optional[NBeatsModel] = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.training_loss_history: list[float] = []
        self.validation_loss_history: list[float] = []

    def _create_windows(
        self, data: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """Create sliding windows for training."""
        lookback = self.config.lookback_length
        horizon = self.config.horizon
        n_windows = len(data) - lookback - horizon + 1

        X = np.zeros((n_windows, lookback))
        y = np.zeros((n_windows, horizon))

        for i in range(n_windows):
            X[i] = data[i:i + lookback]
            y[i] = data[i + lookback:i + lookback + horizon]

        return X, y

    def fit(
        self,
        train_data: np.ndarray,
        validation_data: Optional[np.ndarray] = None,
        verbose: bool = True,
    ) -> "NBeatsForecaster":
        """
        Fit the N-BEATS model.

        Args:
            train_data: Training time series (1D array)
            validation_data: Optional validation series
            verbose: Print training progress

        Returns:
            Self for chaining
        """
        # Normalize data
        self.train_mean = train_data.mean()
        self.train_std = train_data.std() + 1e-8
        normalized_train = (train_data - self.train_mean) / self.train_std

        # Create windows
        X_train, y_train = self._create_windows(normalized_train)

        # Convert to tensors
        X_train_t = torch.FloatTensor(X_train).to(self.device)
        y_train_t = torch.FloatTensor(y_train).to(self.device)

        # Create dataloader
        train_dataset = TensorDataset(X_train_t, y_train_t)
        train_loader = DataLoader(
            train_dataset,
            batch_size=self.config.batch_size,
            shuffle=True,
        )

        # Validation loader
        val_loader = None
        if validation_data is not None:
            normalized_val = (validation_data - self.train_mean) / self.train_std
            X_val, y_val = self._create_windows(normalized_val)
            val_dataset = TensorDataset(
                torch.FloatTensor(X_val).to(self.device),
                torch.FloatTensor(y_val).to(self.device),
            )
            val_loader = DataLoader(val_dataset, batch_size=self.config.batch_size)

        # Initialize model
        self.model = NBeatsModel(self.config).to(self.device)

        # Optimizer
        optimizer = torch.optim.Adam(
            self.model.parameters(),
            lr=self.config.learning_rate,
            weight_decay=self.config.weight_decay,
        )

        # Training loop
        best_val_loss = float("inf")
        patience_counter = 0

        for epoch in range(self.config.epochs):
            # Training
            self.model.train()
            train_loss = 0.0

            for X_batch, y_batch in train_loader:
                optimizer.zero_grad()
                forecast, _, _ = self.model(X_batch)
                loss = F.mse_loss(forecast, y_batch)
                loss.backward()
                optimizer.step()
                train_loss += loss.item()

            train_loss /= len(train_loader)
            self.training_loss_history.append(train_loss)

            # Validation
            if val_loader:
                self.model.eval()
                val_loss = 0.0
                with torch.no_grad():
                    for X_batch, y_batch in val_loader:
                        forecast, _, _ = self.model(X_batch)
                        val_loss += F.mse_loss(forecast, y_batch).item()
                val_loss /= len(val_loader)
                self.validation_loss_history.append(val_loss)

                # Early stopping
                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    patience_counter = 0
                else:
                    patience_counter += 1

                if patience_counter >= self.config.early_stopping_patience:
                    if verbose:
                        print(f"Early stopping at epoch {epoch + 1}")
                    break

                if verbose and (epoch + 1) % 10 == 0:
                    print(f"Epoch {epoch + 1}: train_loss={train_loss:.6f}, val_loss={val_loss:.6f}")
            else:
                if verbose and (epoch + 1) % 10 == 0:
                    print(f"Epoch {epoch + 1}: train_loss={train_loss:.6f}")

        return self

    def predict(
        self,
        history: np.ndarray,
        return_components: bool = False,
    ) -> NBeatsForecast:
        """
        Generate forecasts.

        Args:
            history: Historical data (at least lookback_length)
            return_components: Include decomposition

        Returns:
            NBeatsForecast with predictions
        """
        if self.model is None:
            raise ValueError("Model not trained. Call fit() first.")

        self.model.eval()

        # Normalize
        normalized = (history - self.train_mean) / self.train_std

        # Get last lookback window
        if len(normalized) < self.config.lookback_length:
            raise ValueError(
                f"Need at least {self.config.lookback_length} observations"
            )

        x = normalized[-self.config.lookback_length:]
        x_tensor = torch.FloatTensor(x).unsqueeze(0).to(self.device)

        with torch.no_grad():
            forecast, backcast, stack_outputs = self.model(x_tensor)

        # Denormalize
        forecast_np = forecast.cpu().numpy()[0] * self.train_std + self.train_mean
        backcast_np = backcast.cpu().numpy()[0] * self.train_std + self.train_mean

        result = NBeatsForecast(
            forecast=forecast_np,
            backcast=backcast_np,
        )

        if return_components:
            # Extract interpretable components
            if "trend" in stack_outputs:
                result.trend_component = (
                    stack_outputs["trend"]["forecast"].cpu().numpy()[0]
                    * self.train_std
                    + self.train_mean
                )
            if "seasonality" in stack_outputs:
                result.seasonal_component = (
                    stack_outputs["seasonality"]["forecast"].cpu().numpy()[0]
                    * self.train_std
                )
            if "generic" in stack_outputs:
                result.residual_component = (
                    stack_outputs["generic"]["forecast"].cpu().numpy()[0]
                    * self.train_std
                )

        return result

    def predict_intervals(
        self,
        history: np.ndarray,
        n_samples: int = 100,
        confidence: float = 0.95,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Generate prediction intervals using dropout sampling.

        Args:
            history: Historical data
            n_samples: Number of MC samples
            confidence: Confidence level

        Returns:
            Tuple of (point_forecast, lower_bound, upper_bound)
        """
        if self.model is None:
            raise ValueError("Model not trained. Call fit() first.")

        # Enable dropout for uncertainty
        self.model.train()

        normalized = (history - self.train_mean) / self.train_std
        x = normalized[-self.config.lookback_length:]
        x_tensor = torch.FloatTensor(x).unsqueeze(0).to(self.device)

        forecasts = []
        with torch.no_grad():
            for _ in range(n_samples):
                forecast, _, _ = self.model(x_tensor)
                forecasts.append(forecast.cpu().numpy()[0])

        self.model.eval()

        forecasts = np.array(forecasts)
        forecasts = forecasts * self.train_std + self.train_mean

        point_forecast = forecasts.mean(axis=0)
        alpha = 1 - confidence
        lower = np.percentile(forecasts, alpha / 2 * 100, axis=0)
        upper = np.percentile(forecasts, (1 - alpha / 2) * 100, axis=0)

        return point_forecast, lower, upper
