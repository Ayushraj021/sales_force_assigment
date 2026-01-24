"""
Temporal Fusion Transformer (TFT) for Time Series Forecasting

Implements the TFT architecture from Lim et al. (2019) for
interpretable multi-horizon time series forecasting.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple
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
class TFTConfig:
    """Configuration for Temporal Fusion Transformer."""

    # Architecture
    hidden_size: int = 64
    num_heads: int = 4
    dropout: float = 0.1
    num_lstm_layers: int = 2

    # Quantile outputs
    quantiles: list[float] = field(default_factory=lambda: [0.1, 0.5, 0.9])

    # Input dimensions
    static_categorical_sizes: list[int] = field(default_factory=list)
    static_continuous_size: int = 0
    known_categorical_sizes: list[int] = field(default_factory=list)
    known_continuous_size: int = 0
    observed_continuous_size: int = 1  # Target variable

    # Time dimensions
    lookback_length: int = 52
    horizon: int = 12

    # Training
    learning_rate: float = 1e-3
    batch_size: int = 32
    epochs: int = 100
    early_stopping_patience: int = 10

    # Feature dimensions
    embedding_dim: int = 16


@dataclass
class TFTForecast:
    """TFT forecast result with interpretability outputs."""

    # Forecasts
    point_forecast: np.ndarray  # Median forecast
    quantile_forecasts: Dict[float, np.ndarray]  # Quantile forecasts

    # Attention weights for interpretability
    temporal_attention: Optional[np.ndarray] = None
    variable_importance: Optional[Dict[str, float]] = None
    static_attention: Optional[np.ndarray] = None


if TORCH_AVAILABLE:

    class GatedLinearUnit(nn.Module):
        """GLU activation for gating mechanisms."""

        def __init__(self, input_size: int, hidden_size: int, dropout: float = 0.1):
            super().__init__()
            self.fc = nn.Linear(input_size, hidden_size)
            self.gate_fc = nn.Linear(input_size, hidden_size)
            self.dropout = nn.Dropout(dropout)
            self.layer_norm = nn.LayerNorm(hidden_size)

        def forward(self, x: torch.Tensor, skip: Optional[torch.Tensor] = None):
            output = self.fc(x)
            gate = torch.sigmoid(self.gate_fc(x))
            gated_output = self.dropout(output * gate)

            if skip is not None:
                gated_output = gated_output + skip

            return self.layer_norm(gated_output)


    class GatedResidualNetwork(nn.Module):
        """
        GRN for processing inputs with optional context.

        Applies ELU activation and gating for controlled information flow.
        """

        def __init__(
            self,
            input_size: int,
            hidden_size: int,
            output_size: int,
            dropout: float = 0.1,
            context_size: Optional[int] = None,
        ):
            super().__init__()
            self.input_size = input_size
            self.output_size = output_size
            self.context_size = context_size

            # Primary layers
            self.fc1 = nn.Linear(input_size, hidden_size)
            if context_size is not None:
                self.context_fc = nn.Linear(context_size, hidden_size, bias=False)
            self.fc2 = nn.Linear(hidden_size, hidden_size)

            # Gating
            self.glu = GatedLinearUnit(hidden_size, output_size, dropout)

            # Skip connection
            if input_size != output_size:
                self.skip_layer = nn.Linear(input_size, output_size)
            else:
                self.skip_layer = None

        def forward(
            self, x: torch.Tensor, context: Optional[torch.Tensor] = None
        ) -> torch.Tensor:
            # Primary path
            hidden = self.fc1(x)
            if self.context_size is not None and context is not None:
                hidden = hidden + self.context_fc(context)
            hidden = F.elu(hidden)
            hidden = self.fc2(hidden)

            # Skip connection
            skip = self.skip_layer(x) if self.skip_layer else x

            # Gated output
            return self.glu(hidden, skip)


    class VariableSelectionNetwork(nn.Module):
        """
        Variable Selection Network for feature importance.

        Learns which input features are most relevant for prediction.
        """

        def __init__(
            self,
            input_size: int,
            num_inputs: int,
            hidden_size: int,
            dropout: float = 0.1,
            context_size: Optional[int] = None,
        ):
            super().__init__()
            self.num_inputs = num_inputs
            self.hidden_size = hidden_size

            # Flatten input for weight computation
            self.flattened_grn = GatedResidualNetwork(
                input_size=input_size * num_inputs,
                hidden_size=hidden_size,
                output_size=num_inputs,
                dropout=dropout,
                context_size=context_size,
            )

            # Individual variable GRNs
            self.var_grns = nn.ModuleList([
                GatedResidualNetwork(
                    input_size=input_size,
                    hidden_size=hidden_size,
                    output_size=hidden_size,
                    dropout=dropout,
                )
                for _ in range(num_inputs)
            ])

        def forward(
            self, x: torch.Tensor, context: Optional[torch.Tensor] = None
        ) -> Tuple[torch.Tensor, torch.Tensor]:
            # x shape: (batch, time, num_inputs, input_size) or (batch, num_inputs, input_size)
            is_temporal = len(x.shape) == 4

            if is_temporal:
                batch, time, num_inputs, input_size = x.shape
                # Flatten for weight computation
                flattened = x.reshape(batch * time, -1)
                if context is not None:
                    context_expanded = context.unsqueeze(1).expand(-1, time, -1)
                    context_flat = context_expanded.reshape(batch * time, -1)
                else:
                    context_flat = None
            else:
                batch, num_inputs, input_size = x.shape
                flattened = x.reshape(batch, -1)
                context_flat = context

            # Compute variable selection weights
            weights = self.flattened_grn(flattened, context_flat)
            weights = F.softmax(weights, dim=-1)

            if is_temporal:
                weights = weights.reshape(batch, time, num_inputs)
            else:
                weights = weights.reshape(batch, num_inputs)

            # Process each variable
            var_outputs = []
            for i, grn in enumerate(self.var_grns):
                if is_temporal:
                    var_input = x[:, :, i, :]
                    var_output = grn(var_input.reshape(-1, input_size))
                    var_output = var_output.reshape(batch, time, -1)
                else:
                    var_output = grn(x[:, i, :])
                var_outputs.append(var_output)

            var_outputs = torch.stack(var_outputs, dim=-2)

            # Weighted combination
            if is_temporal:
                weights_expanded = weights.unsqueeze(-1)
            else:
                weights_expanded = weights.unsqueeze(-1)

            combined = (var_outputs * weights_expanded).sum(dim=-2)

            return combined, weights


    class InterpretableMultiHeadAttention(nn.Module):
        """
        Multi-head attention with interpretable attention weights.
        """

        def __init__(
            self,
            hidden_size: int,
            num_heads: int,
            dropout: float = 0.1,
        ):
            super().__init__()
            self.num_heads = num_heads
            self.hidden_size = hidden_size
            self.head_size = hidden_size // num_heads

            assert hidden_size % num_heads == 0

            self.query = nn.Linear(hidden_size, hidden_size)
            self.key = nn.Linear(hidden_size, hidden_size)
            self.value = nn.Linear(hidden_size, hidden_size)

            self.dropout = nn.Dropout(dropout)
            self.output = nn.Linear(hidden_size, hidden_size)

        def forward(
            self, query: torch.Tensor, key: torch.Tensor, value: torch.Tensor,
            mask: Optional[torch.Tensor] = None
        ) -> Tuple[torch.Tensor, torch.Tensor]:
            batch_size = query.size(0)

            # Linear projections
            Q = self.query(query)
            K = self.key(key)
            V = self.value(value)

            # Reshape for multi-head attention
            Q = Q.view(batch_size, -1, self.num_heads, self.head_size).transpose(1, 2)
            K = K.view(batch_size, -1, self.num_heads, self.head_size).transpose(1, 2)
            V = V.view(batch_size, -1, self.num_heads, self.head_size).transpose(1, 2)

            # Scaled dot-product attention
            scores = torch.matmul(Q, K.transpose(-2, -1)) / np.sqrt(self.head_size)

            if mask is not None:
                scores = scores.masked_fill(mask == 0, -1e9)

            attention_weights = F.softmax(scores, dim=-1)
            attention_weights = self.dropout(attention_weights)

            # Apply attention to values
            attended = torch.matmul(attention_weights, V)

            # Reshape back
            attended = attended.transpose(1, 2).contiguous()
            attended = attended.view(batch_size, -1, self.hidden_size)

            output = self.output(attended)

            # Average attention across heads for interpretability
            avg_attention = attention_weights.mean(dim=1)

            return output, avg_attention


    class TemporalFusionTransformer(nn.Module):
        """
        Temporal Fusion Transformer for multi-horizon forecasting.

        Paper: https://arxiv.org/abs/1912.09363
        """

        def __init__(self, config: TFTConfig):
            super().__init__()
            self.config = config

            # Input processing
            self.observed_embedding = nn.Linear(
                config.observed_continuous_size, config.hidden_size
            )

            if config.known_continuous_size > 0:
                self.known_embedding = nn.Linear(
                    config.known_continuous_size, config.hidden_size
                )

            # Static variable selection (if static features exist)
            total_static = len(config.static_categorical_sizes) + config.static_continuous_size
            if total_static > 0:
                self.static_vsn = VariableSelectionNetwork(
                    input_size=config.embedding_dim,
                    num_inputs=total_static,
                    hidden_size=config.hidden_size,
                    dropout=config.dropout,
                )
                self.static_context_grn = GatedResidualNetwork(
                    input_size=config.hidden_size,
                    hidden_size=config.hidden_size,
                    output_size=config.hidden_size,
                    dropout=config.dropout,
                )

            # LSTM encoder
            self.lstm_encoder = nn.LSTM(
                input_size=config.hidden_size,
                hidden_size=config.hidden_size,
                num_layers=config.num_lstm_layers,
                dropout=config.dropout if config.num_lstm_layers > 1 else 0,
                batch_first=True,
            )

            # LSTM decoder
            self.lstm_decoder = nn.LSTM(
                input_size=config.hidden_size,
                hidden_size=config.hidden_size,
                num_layers=config.num_lstm_layers,
                dropout=config.dropout if config.num_lstm_layers > 1 else 0,
                batch_first=True,
            )

            # Static enrichment
            self.static_enrichment_grn = GatedResidualNetwork(
                input_size=config.hidden_size,
                hidden_size=config.hidden_size,
                output_size=config.hidden_size,
                dropout=config.dropout,
                context_size=config.hidden_size,
            )

            # Temporal self-attention
            self.temporal_attention = InterpretableMultiHeadAttention(
                hidden_size=config.hidden_size,
                num_heads=config.num_heads,
                dropout=config.dropout,
            )

            self.attention_glu = GatedLinearUnit(
                config.hidden_size, config.hidden_size, config.dropout
            )

            # Position-wise feedforward
            self.position_grn = GatedResidualNetwork(
                input_size=config.hidden_size,
                hidden_size=config.hidden_size,
                output_size=config.hidden_size,
                dropout=config.dropout,
            )

            # Output layer (quantile outputs)
            self.output_layer = nn.Linear(
                config.hidden_size, len(config.quantiles)
            )

        def forward(
            self,
            observed: torch.Tensor,  # (batch, lookback, observed_size)
            known_future: Optional[torch.Tensor] = None,  # (batch, horizon, known_size)
            static: Optional[torch.Tensor] = None,  # (batch, static_size)
        ) -> Tuple[torch.Tensor, Dict]:
            batch_size = observed.size(0)

            # Embed observed inputs
            encoder_input = self.observed_embedding(observed)

            # Process static context if available
            if static is not None and hasattr(self, 'static_vsn'):
                static_context, static_weights = self.static_vsn(static)
                static_context = self.static_context_grn(static_context)
            else:
                static_context = torch.zeros(
                    batch_size, self.config.hidden_size, device=observed.device
                )
                static_weights = None

            # LSTM encoder
            encoder_output, (h_n, c_n) = self.lstm_encoder(encoder_input)

            # Prepare decoder input
            if known_future is not None and hasattr(self, 'known_embedding'):
                decoder_input = self.known_embedding(known_future)
            else:
                # Use last encoder output as decoder input
                decoder_input = encoder_output[:, -1:, :].expand(-1, self.config.horizon, -1)

            # LSTM decoder
            decoder_output, _ = self.lstm_decoder(decoder_input, (h_n, c_n))

            # Combine encoder and decoder outputs
            temporal_features = torch.cat([encoder_output, decoder_output], dim=1)

            # Static enrichment
            static_expanded = static_context.unsqueeze(1).expand(-1, temporal_features.size(1), -1)
            enriched = self.static_enrichment_grn(temporal_features, static_expanded)

            # Self-attention (decoder can only attend to past + itself)
            total_len = self.config.lookback_length + self.config.horizon
            mask = torch.triu(
                torch.ones(total_len, total_len, device=observed.device),
                diagonal=1
            ).bool()
            mask = ~mask  # Convert to attention mask

            attended, attention_weights = self.temporal_attention(
                enriched, enriched, enriched, mask=mask.unsqueeze(0).unsqueeze(0)
            )

            # Gated skip connection
            gated = self.attention_glu(attended, enriched)

            # Position-wise feedforward
            output = self.position_grn(gated)

            # Extract future outputs only
            future_output = output[:, -self.config.horizon:, :]

            # Quantile predictions
            quantile_output = self.output_layer(future_output)

            # Collect interpretability outputs
            interpretability = {
                "attention_weights": attention_weights[:, -self.config.horizon:, :],
                "static_weights": static_weights,
            }

            return quantile_output, interpretability


class TFTForecaster:
    """
    Temporal Fusion Transformer Forecaster.

    Provides interpretable multi-horizon forecasting with:
    - Variable importance scores
    - Temporal attention patterns
    - Quantile predictions

    Example:
        config = TFTConfig(horizon=12, lookback_length=52)
        forecaster = TFTForecaster(config)
        forecaster.fit(train_data)
        forecast = forecaster.predict(test_data)
    """

    def __init__(self, config: Optional[TFTConfig] = None):
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch is required for TFT. Install with: pip install torch")

        self.config = config or TFTConfig()
        self.model: Optional[TemporalFusionTransformer] = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.training_loss_history: list[float] = []

    def _quantile_loss(
        self, predictions: torch.Tensor, targets: torch.Tensor
    ) -> torch.Tensor:
        """Compute quantile loss."""
        losses = []
        for i, q in enumerate(self.config.quantiles):
            errors = targets - predictions[:, :, i]
            losses.append(
                torch.max((q - 1) * errors, q * errors).mean()
            )
        return sum(losses) / len(losses)

    def _create_windows(self, data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Create sliding windows."""
        lookback = self.config.lookback_length
        horizon = self.config.horizon
        n_windows = len(data) - lookback - horizon + 1

        X = np.zeros((n_windows, lookback, 1))
        y = np.zeros((n_windows, horizon))

        for i in range(n_windows):
            X[i, :, 0] = data[i:i + lookback]
            y[i] = data[i + lookback:i + lookback + horizon]

        return X, y

    def fit(
        self,
        train_data: np.ndarray,
        validation_data: Optional[np.ndarray] = None,
        verbose: bool = True,
    ) -> "TFTForecaster":
        """Fit the TFT model."""
        # Normalize
        self.train_mean = train_data.mean()
        self.train_std = train_data.std() + 1e-8
        normalized = (train_data - self.train_mean) / self.train_std

        # Create windows
        X_train, y_train = self._create_windows(normalized)

        # Convert to tensors
        X_t = torch.FloatTensor(X_train).to(self.device)
        y_t = torch.FloatTensor(y_train).to(self.device)

        # Dataloader
        dataset = TensorDataset(X_t, y_t)
        loader = DataLoader(dataset, batch_size=self.config.batch_size, shuffle=True)

        # Initialize model
        self.model = TemporalFusionTransformer(self.config).to(self.device)

        optimizer = torch.optim.Adam(
            self.model.parameters(),
            lr=self.config.learning_rate,
        )

        # Training loop
        for epoch in range(self.config.epochs):
            self.model.train()
            epoch_loss = 0.0

            for X_batch, y_batch in loader:
                optimizer.zero_grad()
                predictions, _ = self.model(X_batch)
                loss = self._quantile_loss(predictions, y_batch.unsqueeze(-1).expand(-1, -1, len(self.config.quantiles)))
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item()

            epoch_loss /= len(loader)
            self.training_loss_history.append(epoch_loss)

            if verbose and (epoch + 1) % 10 == 0:
                print(f"Epoch {epoch + 1}: loss={epoch_loss:.6f}")

        return self

    def predict(self, history: np.ndarray) -> TFTForecast:
        """Generate forecasts."""
        if self.model is None:
            raise ValueError("Model not trained. Call fit() first.")

        self.model.eval()

        # Normalize
        normalized = (history - self.train_mean) / self.train_std
        x = normalized[-self.config.lookback_length:]
        x_tensor = torch.FloatTensor(x).unsqueeze(0).unsqueeze(-1).to(self.device)

        with torch.no_grad():
            predictions, interpretability = self.model(x_tensor)

        # Denormalize
        predictions_np = predictions.cpu().numpy()[0] * self.train_std + self.train_mean

        # Build result
        quantile_forecasts = {
            q: predictions_np[:, i] for i, q in enumerate(self.config.quantiles)
        }

        return TFTForecast(
            point_forecast=quantile_forecasts.get(0.5, predictions_np.mean(axis=1)),
            quantile_forecasts=quantile_forecasts,
            temporal_attention=interpretability["attention_weights"].cpu().numpy()[0],
        )
