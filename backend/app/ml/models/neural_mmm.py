"""
Neural Marketing Mix Model

PyTorch implementation of a neural network-based Marketing Mix Model
with differentiable adstock and saturation transformations.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Union

import numpy as np
import pandas as pd

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader, TensorDataset
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


class SaturationFunction(str, Enum):
    """Available saturation functions."""

    HILL = "hill"
    LOGISTIC = "logistic"
    TANH = "tanh"


class AdstockFunction(str, Enum):
    """Available adstock functions."""

    GEOMETRIC = "geometric"
    WEIBULL = "weibull"


@dataclass
class NeuralMMMConfig:
    """Configuration for Neural MMM."""

    # Model architecture
    hidden_dims: list[int] = field(default_factory=lambda: [64, 32])
    dropout: float = 0.1
    use_batch_norm: bool = True

    # Transformations
    saturation_function: SaturationFunction = SaturationFunction.HILL
    adstock_function: AdstockFunction = AdstockFunction.GEOMETRIC
    max_adstock_lag: int = 8

    # Training
    learning_rate: float = 0.001
    batch_size: int = 32
    epochs: int = 100
    early_stopping_patience: int = 10
    weight_decay: float = 0.01

    # Regularization
    channel_reg_strength: float = 0.1


@dataclass
class NeuralMMMResult:
    """Result from Neural MMM training."""

    # Learned parameters
    adstock_params: dict[str, float]
    saturation_params: dict[str, dict[str, float]]

    # Channel contributions
    channel_contributions: dict[str, np.ndarray]
    channel_roi: dict[str, float]
    channel_importance: dict[str, float]

    # Model performance
    train_loss: float
    val_loss: float
    r_squared: float
    mape: float

    # Training history
    loss_history: list[float]

    # Baseline contribution
    baseline: float


if TORCH_AVAILABLE:

    class DifferentiableAdstock(nn.Module):
        """Differentiable adstock transformation layer."""

        def __init__(
            self,
            n_channels: int,
            max_lag: int = 8,
            function: AdstockFunction = AdstockFunction.GEOMETRIC,
        ):
            super().__init__()
            self.n_channels = n_channels
            self.max_lag = max_lag
            self.function = function

            # Learnable decay rate per channel (sigmoid constrained to 0-1)
            self.decay_logits = nn.Parameter(torch.zeros(n_channels))

            if function == AdstockFunction.WEIBULL:
                # Weibull shape parameter
                self.shape_params = nn.Parameter(torch.ones(n_channels))

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            """
            Apply adstock transformation.

            Args:
                x: Input tensor of shape (batch, time, channels)

            Returns:
                Adstocked tensor of same shape
            """
            batch_size, seq_len, n_channels = x.shape

            # Get decay rates (constrained to 0-1)
            decay = torch.sigmoid(self.decay_logits)

            # Build convolution weights
            weights = self._build_weights(decay, seq_len)

            # Apply convolution per channel
            output = torch.zeros_like(x)
            for c in range(n_channels):
                # Causal convolution using cumsum trick for efficiency
                for t in range(seq_len):
                    for lag in range(min(t + 1, self.max_lag)):
                        output[:, t, c] += x[:, t - lag, c] * weights[c, lag]

            return output

        def _build_weights(self, decay: torch.Tensor, seq_len: int) -> torch.Tensor:
            """Build adstock weights."""
            if self.function == AdstockFunction.GEOMETRIC:
                # Geometric decay: w_k = decay^k
                lags = torch.arange(self.max_lag, device=decay.device, dtype=decay.dtype)
                weights = decay.unsqueeze(1) ** lags.unsqueeze(0)

            elif self.function == AdstockFunction.WEIBULL:
                # Weibull decay
                lags = torch.arange(self.max_lag, device=decay.device, dtype=decay.dtype)
                shape = torch.softplus(self.shape_params).unsqueeze(1)
                scale = -torch.log(decay + 1e-8).unsqueeze(1)
                weights = torch.exp(-scale * (lags.unsqueeze(0) ** shape))

            # Normalize weights
            weights = weights / (weights.sum(dim=1, keepdim=True) + 1e-8)

            return weights


    class DifferentiableSaturation(nn.Module):
        """Differentiable saturation transformation layer."""

        def __init__(
            self,
            n_channels: int,
            function: SaturationFunction = SaturationFunction.HILL,
        ):
            super().__init__()
            self.n_channels = n_channels
            self.function = function

            # Hill function parameters
            if function == SaturationFunction.HILL:
                # Half-saturation point (K)
                self.log_k = nn.Parameter(torch.zeros(n_channels))
                # Hill coefficient (n)
                self.log_n = nn.Parameter(torch.zeros(n_channels))

            elif function == SaturationFunction.LOGISTIC:
                # Logistic parameters
                self.scale = nn.Parameter(torch.ones(n_channels))
                self.shift = nn.Parameter(torch.zeros(n_channels))

            elif function == SaturationFunction.TANH:
                self.scale = nn.Parameter(torch.ones(n_channels))

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            """
            Apply saturation transformation.

            Args:
                x: Input tensor of shape (batch, time, channels)

            Returns:
                Saturated tensor of same shape
            """
            if self.function == SaturationFunction.HILL:
                k = torch.exp(self.log_k) + 1e-8
                n = torch.exp(self.log_n) + 0.1

                # Hill function: x^n / (K^n + x^n)
                x_n = torch.pow(x + 1e-8, n)
                k_n = torch.pow(k, n)
                output = x_n / (k_n + x_n)

            elif self.function == SaturationFunction.LOGISTIC:
                output = 1 / (1 + torch.exp(-self.scale * (x - self.shift)))

            elif self.function == SaturationFunction.TANH:
                output = torch.tanh(self.scale * x)

            return output


    class NeuralMMMModel(nn.Module):
        """Neural Marketing Mix Model."""

        def __init__(
            self,
            n_channels: int,
            n_controls: int = 0,
            config: Optional[NeuralMMMConfig] = None,
        ):
            super().__init__()
            self.config = config or NeuralMMMConfig()
            self.n_channels = n_channels
            self.n_controls = n_controls

            # Adstock layer
            self.adstock = DifferentiableAdstock(
                n_channels=n_channels,
                max_lag=self.config.max_adstock_lag,
                function=self.config.adstock_function,
            )

            # Saturation layer
            self.saturation = DifferentiableSaturation(
                n_channels=n_channels,
                function=self.config.saturation_function,
            )

            # Channel coefficients
            self.channel_weights = nn.Parameter(torch.ones(n_channels))

            # Control coefficients
            if n_controls > 0:
                self.control_weights = nn.Parameter(torch.zeros(n_controls))

            # Baseline (intercept)
            self.baseline = nn.Parameter(torch.zeros(1))

            # Optional MLP head for complex interactions
            if self.config.hidden_dims:
                layers = []
                input_dim = n_channels + n_controls

                for hidden_dim in self.config.hidden_dims:
                    layers.append(nn.Linear(input_dim, hidden_dim))
                    if self.config.use_batch_norm:
                        layers.append(nn.BatchNorm1d(hidden_dim))
                    layers.append(nn.ReLU())
                    if self.config.dropout > 0:
                        layers.append(nn.Dropout(self.config.dropout))
                    input_dim = hidden_dim

                layers.append(nn.Linear(input_dim, 1))
                self.mlp = nn.Sequential(*layers)
                self.use_mlp = True
            else:
                self.use_mlp = False

        def forward(
            self,
            media: torch.Tensor,
            controls: Optional[torch.Tensor] = None,
        ) -> torch.Tensor:
            """
            Forward pass.

            Args:
                media: Media spend tensor (batch, time, channels)
                controls: Control variables (batch, time, n_controls)

            Returns:
                Predicted outcome (batch, time)
            """
            # Apply transformations
            adstocked = self.adstock(media)
            saturated = self.saturation(adstocked)

            # Linear combination of channels
            channel_contrib = (saturated * self.channel_weights).sum(dim=-1)

            if self.use_mlp:
                # Use MLP for complex interactions
                batch, time, _ = saturated.shape
                features = saturated.view(batch * time, -1)

                if controls is not None:
                    ctrl_flat = controls.view(batch * time, -1)
                    features = torch.cat([features, ctrl_flat], dim=-1)

                mlp_out = self.mlp(features).view(batch, time)
                output = mlp_out + self.baseline
            else:
                # Simple linear model
                output = channel_contrib + self.baseline

                if controls is not None and self.n_controls > 0:
                    ctrl_contrib = (controls * self.control_weights).sum(dim=-1)
                    output = output + ctrl_contrib

            return output

        def get_channel_contributions(
            self, media: torch.Tensor
        ) -> dict[int, torch.Tensor]:
            """Get individual channel contributions."""
            adstocked = self.adstock(media)
            saturated = self.saturation(adstocked)

            contributions = {}
            for c in range(self.n_channels):
                contributions[c] = (
                    saturated[:, :, c] * self.channel_weights[c]
                ).detach()

            return contributions


    class NeuralMMMTrainer:
        """Trainer for Neural MMM."""

        def __init__(self, config: Optional[NeuralMMMConfig] = None):
            self.config = config or NeuralMMMConfig()
            self.model: Optional[NeuralMMMModel] = None
            self.channel_names: list[str] = []
            self.control_names: list[str] = []
            self.scaler_y: Optional[tuple] = None

        def fit(
            self,
            data: pd.DataFrame,
            target_col: str,
            channel_cols: list[str],
            control_cols: Optional[list[str]] = None,
            date_col: str = "date",
            val_split: float = 0.2,
        ) -> NeuralMMMResult:
            """
            Train Neural MMM.

            Args:
                data: DataFrame with time series data
                target_col: Target variable column
                channel_cols: List of media channel columns
                control_cols: List of control variable columns
                date_col: Date column name
                val_split: Validation split ratio

            Returns:
                NeuralMMMResult with trained model parameters
            """
            control_cols = control_cols or []
            self.channel_names = channel_cols
            self.control_names = control_cols

            # Prepare data
            X_media = data[channel_cols].values
            y = data[target_col].values

            if control_cols:
                X_controls = data[control_cols].values
            else:
                X_controls = None

            # Normalize
            self.scaler_y = (y.mean(), y.std())
            y_norm = (y - self.scaler_y[0]) / (self.scaler_y[1] + 1e-8)

            # Split train/val
            split_idx = int(len(y) * (1 - val_split))
            X_train, X_val = X_media[:split_idx], X_media[split_idx:]
            y_train, y_val = y_norm[:split_idx], y_norm[split_idx:]

            if X_controls is not None:
                ctrl_train, ctrl_val = X_controls[:split_idx], X_controls[split_idx:]
            else:
                ctrl_train, ctrl_val = None, None

            # Convert to tensors
            X_train_t = torch.FloatTensor(X_train).unsqueeze(0)
            y_train_t = torch.FloatTensor(y_train).unsqueeze(0)
            X_val_t = torch.FloatTensor(X_val).unsqueeze(0)
            y_val_t = torch.FloatTensor(y_val).unsqueeze(0)

            if ctrl_train is not None:
                ctrl_train_t = torch.FloatTensor(ctrl_train).unsqueeze(0)
                ctrl_val_t = torch.FloatTensor(ctrl_val).unsqueeze(0)
            else:
                ctrl_train_t, ctrl_val_t = None, None

            # Initialize model
            self.model = NeuralMMMModel(
                n_channels=len(channel_cols),
                n_controls=len(control_cols),
                config=self.config,
            )

            # Optimizer
            optimizer = optim.AdamW(
                self.model.parameters(),
                lr=self.config.learning_rate,
                weight_decay=self.config.weight_decay,
            )

            # Training loop
            loss_history = []
            best_val_loss = float("inf")
            patience_counter = 0

            for epoch in range(self.config.epochs):
                # Training
                self.model.train()
                optimizer.zero_grad()

                y_pred = self.model(X_train_t, ctrl_train_t)
                loss = nn.MSELoss()(y_pred.squeeze(), y_train_t.squeeze())

                # Channel regularization
                reg_loss = self.config.channel_reg_strength * torch.sum(
                    torch.abs(self.model.channel_weights)
                )
                total_loss = loss + reg_loss

                total_loss.backward()
                optimizer.step()

                # Validation
                self.model.eval()
                with torch.no_grad():
                    y_val_pred = self.model(X_val_t, ctrl_val_t)
                    val_loss = nn.MSELoss()(y_val_pred.squeeze(), y_val_t.squeeze())

                loss_history.append(val_loss.item())

                # Early stopping
                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    patience_counter = 0
                else:
                    patience_counter += 1
                    if patience_counter >= self.config.early_stopping_patience:
                        break

            # Extract results
            return self._extract_results(
                X_media, y, X_controls, loss_history, float(best_val_loss)
            )

        def _extract_results(
            self,
            X_media: np.ndarray,
            y: np.ndarray,
            X_controls: Optional[np.ndarray],
            loss_history: list[float],
            val_loss: float,
        ) -> NeuralMMMResult:
            """Extract results from trained model."""
            self.model.eval()

            with torch.no_grad():
                X_t = torch.FloatTensor(X_media).unsqueeze(0)
                ctrl_t = (
                    torch.FloatTensor(X_controls).unsqueeze(0)
                    if X_controls is not None else None
                )

                # Get predictions
                y_pred = self.model(X_t, ctrl_t).squeeze().numpy()
                y_pred = y_pred * self.scaler_y[1] + self.scaler_y[0]

                # Get channel contributions
                contrib_dict = self.model.get_channel_contributions(X_t)

                channel_contributions = {}
                channel_roi = {}
                channel_importance = {}

                total_spend = {}
                for i, name in enumerate(self.channel_names):
                    contrib = contrib_dict[i].squeeze().numpy()
                    contrib = contrib * self.scaler_y[1]
                    channel_contributions[name] = contrib

                    spend = X_media[:, i].sum()
                    total_spend[name] = spend
                    channel_roi[name] = contrib.sum() / spend if spend > 0 else 0

                # Importance based on contribution
                total_contrib = sum(c.sum() for c in channel_contributions.values())
                for name, contrib in channel_contributions.items():
                    channel_importance[name] = (
                        contrib.sum() / total_contrib if total_contrib > 0 else 0
                    )

                # Adstock parameters
                decay_rates = torch.sigmoid(self.model.adstock.decay_logits).numpy()
                adstock_params = {
                    name: float(decay_rates[i])
                    for i, name in enumerate(self.channel_names)
                }

                # Saturation parameters
                saturation_params = {}
                if hasattr(self.model.saturation, "log_k"):
                    k_vals = torch.exp(self.model.saturation.log_k).numpy()
                    n_vals = torch.exp(self.model.saturation.log_n).numpy()
                    for i, name in enumerate(self.channel_names):
                        saturation_params[name] = {
                            "half_saturation": float(k_vals[i]),
                            "shape": float(n_vals[i]),
                        }

                # Metrics
                r_squared = 1 - np.sum((y - y_pred) ** 2) / np.sum((y - y.mean()) ** 2)
                mape = np.mean(np.abs((y - y_pred) / (y + 1e-8))) * 100

                baseline = float(
                    self.model.baseline.item() * self.scaler_y[1] + self.scaler_y[0]
                )

            return NeuralMMMResult(
                adstock_params=adstock_params,
                saturation_params=saturation_params,
                channel_contributions=channel_contributions,
                channel_roi=channel_roi,
                channel_importance=channel_importance,
                train_loss=loss_history[-1] if loss_history else 0,
                val_loss=val_loss,
                r_squared=float(r_squared),
                mape=float(mape),
                loss_history=loss_history,
                baseline=baseline,
            )

        def predict(
            self,
            data: pd.DataFrame,
        ) -> np.ndarray:
            """Generate predictions for new data."""
            if self.model is None:
                raise ValueError("Model not trained. Call fit() first.")

            self.model.eval()
            X_media = data[self.channel_names].values

            if self.control_names:
                X_controls = data[self.control_names].values
            else:
                X_controls = None

            with torch.no_grad():
                X_t = torch.FloatTensor(X_media).unsqueeze(0)
                ctrl_t = (
                    torch.FloatTensor(X_controls).unsqueeze(0)
                    if X_controls is not None else None
                )

                y_pred = self.model(X_t, ctrl_t).squeeze().numpy()
                y_pred = y_pred * self.scaler_y[1] + self.scaler_y[0]

            return y_pred

else:
    # Fallback when PyTorch is not available
    class NeuralMMMTrainer:
        """Placeholder when PyTorch is not available."""

        def __init__(self, *args, **kwargs):
            raise ImportError(
                "PyTorch is required for Neural MMM. "
                "Install with: pip install torch"
            )
