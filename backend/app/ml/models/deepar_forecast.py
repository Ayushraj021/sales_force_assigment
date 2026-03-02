"""
DeepAR Probabilistic Forecasting Model

Implements the DeepAR architecture from Salinas et al. (2017) for
probabilistic time series forecasting using autoregressive RNN.
"""

from dataclasses import dataclass, field
from typing import Optional, Tuple, Literal
import numpy as np

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torch.utils.data import DataLoader, TensorDataset
    from torch.distributions import Normal, NegativeBinomial, StudentT
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


@dataclass
class DeepARConfig:
    """Configuration for DeepAR model."""

    # Architecture
    hidden_size: int = 64
    num_layers: int = 2
    dropout: float = 0.1
    cell_type: Literal["LSTM", "GRU"] = "LSTM"

    # Distribution
    distribution: Literal["normal", "negative_binomial", "student_t"] = "normal"

    # Input dimensions
    num_time_features: int = 4  # e.g., day_of_week, month, etc.
    num_static_features: int = 0
    embedding_dim: int = 16

    # Time dimensions
    lookback_length: int = 52
    horizon: int = 12

    # Training
    learning_rate: float = 1e-3
    batch_size: int = 32
    epochs: int = 100
    early_stopping_patience: int = 10
    teacher_forcing_ratio: float = 0.5

    # Scaling
    use_scaling: bool = True


@dataclass
class DeepARForecast:
    """DeepAR forecast result with uncertainty."""

    # Point forecasts
    mean: np.ndarray
    median: np.ndarray

    # Uncertainty
    std: np.ndarray
    samples: Optional[np.ndarray] = None  # Monte Carlo samples

    # Prediction intervals
    lower_50: Optional[np.ndarray] = None
    upper_50: Optional[np.ndarray] = None
    lower_90: Optional[np.ndarray] = None
    upper_90: Optional[np.ndarray] = None


if TORCH_AVAILABLE:

    class GaussianOutput(nn.Module):
        """Gaussian distribution output layer."""

        def __init__(self, hidden_size: int):
            super().__init__()
            self.mu_layer = nn.Linear(hidden_size, 1)
            self.sigma_layer = nn.Linear(hidden_size, 1)

        def forward(self, hidden: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
            mu = self.mu_layer(hidden)
            # Ensure positive sigma with softplus
            sigma = F.softplus(self.sigma_layer(hidden)) + 1e-6
            return mu.squeeze(-1), sigma.squeeze(-1)

        def distribution(self, mu: torch.Tensor, sigma: torch.Tensor):
            return Normal(mu, sigma)


    class NegativeBinomialOutput(nn.Module):
        """Negative binomial distribution for count data."""

        def __init__(self, hidden_size: int):
            super().__init__()
            self.mu_layer = nn.Linear(hidden_size, 1)
            self.alpha_layer = nn.Linear(hidden_size, 1)

        def forward(self, hidden: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
            # Mean (positive)
            mu = F.softplus(self.mu_layer(hidden)) + 1e-6
            # Dispersion parameter (positive)
            alpha = F.softplus(self.alpha_layer(hidden)) + 1e-6
            return mu.squeeze(-1), alpha.squeeze(-1)

        def distribution(self, mu: torch.Tensor, alpha: torch.Tensor):
            # Convert to PyTorch NegativeBinomial parameterization
            # total_count = 1/alpha, probs = 1/(1 + alpha*mu)
            total_count = 1.0 / alpha
            probs = 1.0 / (1.0 + alpha * mu)
            return NegativeBinomial(total_count, probs)


    class StudentTOutput(nn.Module):
        """Student-t distribution for heavy tails."""

        def __init__(self, hidden_size: int):
            super().__init__()
            self.mu_layer = nn.Linear(hidden_size, 1)
            self.sigma_layer = nn.Linear(hidden_size, 1)
            self.df_layer = nn.Linear(hidden_size, 1)

        def forward(self, hidden: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
            mu = self.mu_layer(hidden)
            sigma = F.softplus(self.sigma_layer(hidden)) + 1e-6
            # Degrees of freedom > 2 for finite variance
            df = F.softplus(self.df_layer(hidden)) + 2.0
            return mu.squeeze(-1), sigma.squeeze(-1), df.squeeze(-1)

        def distribution(self, mu: torch.Tensor, sigma: torch.Tensor, df: torch.Tensor):
            return StudentT(df, mu, sigma)


    class DeepARModel(nn.Module):
        """
        DeepAR: Probabilistic Forecasting with Autoregressive RNNs.

        Paper: https://arxiv.org/abs/1704.04110
        """

        def __init__(self, config: DeepARConfig):
            super().__init__()
            self.config = config

            # Input embedding
            input_size = 1 + config.num_time_features  # target + time features
            if config.num_static_features > 0:
                input_size += config.embedding_dim

            # Static embeddings
            if config.num_static_features > 0:
                self.static_embedding = nn.Linear(
                    config.num_static_features, config.embedding_dim
                )

            # RNN
            if config.cell_type == "LSTM":
                self.rnn = nn.LSTM(
                    input_size=input_size,
                    hidden_size=config.hidden_size,
                    num_layers=config.num_layers,
                    dropout=config.dropout if config.num_layers > 1 else 0,
                    batch_first=True,
                )
            else:
                self.rnn = nn.GRU(
                    input_size=input_size,
                    hidden_size=config.hidden_size,
                    num_layers=config.num_layers,
                    dropout=config.dropout if config.num_layers > 1 else 0,
                    batch_first=True,
                )

            # Output distribution
            if config.distribution == "normal":
                self.output_layer = GaussianOutput(config.hidden_size)
            elif config.distribution == "negative_binomial":
                self.output_layer = NegativeBinomialOutput(config.hidden_size)
            else:  # student_t
                self.output_layer = StudentTOutput(config.hidden_size)

            self.dropout = nn.Dropout(config.dropout)

        def forward(
            self,
            past_target: torch.Tensor,  # (batch, lookback)
            past_time_features: torch.Tensor,  # (batch, lookback, num_time_features)
            future_time_features: torch.Tensor,  # (batch, horizon, num_time_features)
            static_features: Optional[torch.Tensor] = None,  # (batch, num_static_features)
            future_target: Optional[torch.Tensor] = None,  # For teacher forcing
            scale: Optional[torch.Tensor] = None,  # (batch,) scaling factors
        ) -> Tuple[torch.Tensor, ...]:
            batch_size = past_target.size(0)

            # Handle scaling
            if scale is None:
                scale = torch.ones(batch_size, device=past_target.device)

            # Static embedding
            if static_features is not None and hasattr(self, 'static_embedding'):
                static_embed = self.static_embedding(static_features)
            else:
                static_embed = None

            # Encode past
            past_scaled = past_target / scale.unsqueeze(1)

            # Build encoder input
            encoder_input = torch.cat([
                past_scaled.unsqueeze(-1),
                past_time_features,
            ], dim=-1)

            if static_embed is not None:
                static_expanded = static_embed.unsqueeze(1).expand(
                    -1, self.config.lookback_length, -1
                )
                encoder_input = torch.cat([encoder_input, static_expanded], dim=-1)

            # Encode
            encoder_output, hidden = self.rnn(encoder_input)

            # Decode autoregressively
            all_params = []
            current_input = past_scaled[:, -1:]

            for t in range(self.config.horizon):
                # Build decoder input
                time_feat = future_time_features[:, t:t+1, :]
                decoder_input = torch.cat([current_input.unsqueeze(-1), time_feat], dim=-1)

                if static_embed is not None:
                    decoder_input = torch.cat([
                        decoder_input,
                        static_embed.unsqueeze(1)
                    ], dim=-1)

                # RNN step
                output, hidden = self.rnn(decoder_input, hidden)
                output = self.dropout(output)

                # Get distribution parameters
                params = self.output_layer(output.squeeze(1))
                all_params.append(params)

                # Next input (teacher forcing or sampling)
                if future_target is not None and np.random.random() < self.config.teacher_forcing_ratio:
                    current_input = future_target[:, t:t+1] / scale.unsqueeze(1)
                else:
                    # Sample from predicted distribution
                    if isinstance(params, tuple) and len(params) == 2:
                        mu, sigma = params
                        dist = self.output_layer.distribution(mu, sigma)
                    else:
                        dist = self.output_layer.distribution(*params)
                    current_input = dist.sample().unsqueeze(1)

            # Stack parameters for all time steps
            if self.config.distribution == "student_t":
                mu = torch.stack([p[0] for p in all_params], dim=1)
                sigma = torch.stack([p[1] for p in all_params], dim=1)
                df = torch.stack([p[2] for p in all_params], dim=1)
                return mu * scale.unsqueeze(1), sigma * scale.unsqueeze(1), df
            else:
                mu = torch.stack([p[0] for p in all_params], dim=1)
                sigma = torch.stack([p[1] for p in all_params], dim=1)
                return mu * scale.unsqueeze(1), sigma * scale.unsqueeze(1)


class DeepARForecaster:
    """
    DeepAR Time Series Forecaster.

    Provides probabilistic forecasting with:
    - Multiple distribution options
    - Uncertainty quantification via sampling
    - Automatic scaling

    Example:
        config = DeepARConfig(horizon=12, lookback_length=52)
        forecaster = DeepARForecaster(config)
        forecaster.fit(train_data)
        forecast = forecaster.predict(test_data, n_samples=100)
    """

    def __init__(self, config: Optional[DeepARConfig] = None):
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch is required for DeepAR. Install with: pip install torch")

        self.config = config or DeepARConfig()
        self.model: Optional[DeepARModel] = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.training_loss_history: list[float] = []

    def _create_time_features(self, length: int, start_idx: int = 0) -> np.ndarray:
        """Create time features (normalized cyclical encodings)."""
        features = np.zeros((length, self.config.num_time_features))

        for i in range(length):
            idx = start_idx + i
            # Day of week (0-6)
            features[i, 0] = np.sin(2 * np.pi * (idx % 7) / 7)
            features[i, 1] = np.cos(2 * np.pi * (idx % 7) / 7)
            # Week of year (0-52)
            if self.config.num_time_features >= 4:
                features[i, 2] = np.sin(2 * np.pi * (idx % 52) / 52)
                features[i, 3] = np.cos(2 * np.pi * (idx % 52) / 52)

        return features

    def _compute_scale(self, data: np.ndarray) -> float:
        """Compute scaling factor (mean absolute value)."""
        if self.config.use_scaling:
            return np.abs(data).mean() + 1e-8
        return 1.0

    def _create_windows(
        self, data: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Create training windows with features."""
        lookback = self.config.lookback_length
        horizon = self.config.horizon
        n_windows = len(data) - lookback - horizon + 1

        X = np.zeros((n_windows, lookback))
        y = np.zeros((n_windows, horizon))
        past_features = np.zeros((n_windows, lookback, self.config.num_time_features))
        future_features = np.zeros((n_windows, horizon, self.config.num_time_features))
        scales = np.zeros(n_windows)

        for i in range(n_windows):
            X[i] = data[i:i + lookback]
            y[i] = data[i + lookback:i + lookback + horizon]
            past_features[i] = self._create_time_features(lookback, i)
            future_features[i] = self._create_time_features(horizon, i + lookback)
            scales[i] = self._compute_scale(data[i:i + lookback])

        return X, y, past_features, future_features, scales

    def fit(
        self,
        train_data: np.ndarray,
        validation_data: Optional[np.ndarray] = None,
        verbose: bool = True,
    ) -> "DeepARForecaster":
        """Fit the DeepAR model."""
        # Create windows
        X, y, past_feat, future_feat, scales = self._create_windows(train_data)

        # Convert to tensors
        X_t = torch.FloatTensor(X).to(self.device)
        y_t = torch.FloatTensor(y).to(self.device)
        past_feat_t = torch.FloatTensor(past_feat).to(self.device)
        future_feat_t = torch.FloatTensor(future_feat).to(self.device)
        scales_t = torch.FloatTensor(scales).to(self.device)

        # Dataloader
        dataset = TensorDataset(X_t, y_t, past_feat_t, future_feat_t, scales_t)
        loader = DataLoader(dataset, batch_size=self.config.batch_size, shuffle=True)

        # Initialize model
        self.model = DeepARModel(self.config).to(self.device)

        optimizer = torch.optim.Adam(
            self.model.parameters(),
            lr=self.config.learning_rate,
        )

        # Training loop
        for epoch in range(self.config.epochs):
            self.model.train()
            epoch_loss = 0.0

            for batch in loader:
                X_b, y_b, past_f, future_f, scale_b = batch

                optimizer.zero_grad()

                # Forward pass
                params = self.model(
                    past_target=X_b,
                    past_time_features=past_f,
                    future_time_features=future_f,
                    future_target=y_b,
                    scale=scale_b,
                )

                # Negative log likelihood loss
                if self.config.distribution == "student_t":
                    mu, sigma, df = params
                    dist = StudentT(df, mu, sigma)
                else:
                    mu, sigma = params
                    dist = Normal(mu, sigma)

                loss = -dist.log_prob(y_b).mean()
                loss.backward()
                optimizer.step()

                epoch_loss += loss.item()

            epoch_loss /= len(loader)
            self.training_loss_history.append(epoch_loss)

            if verbose and (epoch + 1) % 10 == 0:
                print(f"Epoch {epoch + 1}: loss={epoch_loss:.6f}")

        return self

    def predict(
        self,
        history: np.ndarray,
        n_samples: int = 100,
    ) -> DeepARForecast:
        """
        Generate probabilistic forecasts.

        Args:
            history: Historical data
            n_samples: Number of Monte Carlo samples

        Returns:
            DeepARForecast with mean, uncertainty, and samples
        """
        if self.model is None:
            raise ValueError("Model not trained. Call fit() first.")

        self.model.eval()

        # Prepare input
        x = history[-self.config.lookback_length:]
        scale = self._compute_scale(x)
        past_feat = self._create_time_features(self.config.lookback_length)
        future_feat = self._create_time_features(
            self.config.horizon, self.config.lookback_length
        )

        x_t = torch.FloatTensor(x).unsqueeze(0).to(self.device)
        past_feat_t = torch.FloatTensor(past_feat).unsqueeze(0).to(self.device)
        future_feat_t = torch.FloatTensor(future_feat).unsqueeze(0).to(self.device)
        scale_t = torch.FloatTensor([scale]).to(self.device)

        # Generate samples
        samples = np.zeros((n_samples, self.config.horizon))

        with torch.no_grad():
            for i in range(n_samples):
                params = self.model(
                    past_target=x_t,
                    past_time_features=past_feat_t,
                    future_time_features=future_feat_t,
                    scale=scale_t,
                )

                if self.config.distribution == "student_t":
                    mu, sigma, df = params
                    dist = StudentT(df, mu, sigma)
                else:
                    mu, sigma = params
                    dist = Normal(mu, sigma)

                samples[i] = dist.sample().cpu().numpy()[0]

        # Compute statistics
        mean = samples.mean(axis=0)
        median = np.median(samples, axis=0)
        std = samples.std(axis=0)

        return DeepARForecast(
            mean=mean,
            median=median,
            std=std,
            samples=samples,
            lower_50=np.percentile(samples, 25, axis=0),
            upper_50=np.percentile(samples, 75, axis=0),
            lower_90=np.percentile(samples, 5, axis=0),
            upper_90=np.percentile(samples, 95, axis=0),
        )
