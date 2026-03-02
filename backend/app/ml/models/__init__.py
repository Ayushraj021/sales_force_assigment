"""ML Models for MMM and forecasting."""

from app.ml.models.pymc_mmm import PyMCMarketingMixModel
from app.ml.models.prophet_forecast import ProphetForecaster
from app.ml.models.custom_mmm import CustomMMMModel
from app.ml.models.arima_forecast import ARIMAForecaster
from app.ml.models.ensemble_forecast import EnsembleForecaster

# Neural models (optional dependencies)
try:
    from app.ml.models.neural_mmm import (
        NeuralMMMModel,
        NeuralMMMTrainer,
        NeuralMMMConfig,
        DifferentiableAdstock,
        DifferentiableSaturation,
    )
    NEURAL_MMM_AVAILABLE = True
except ImportError:
    NEURAL_MMM_AVAILABLE = False

try:
    from app.ml.models.nbeats_forecast import (
        NBeatsForecaster,
        NBeatsConfig,
        NBeatsForecast,
    )
    NBEATS_AVAILABLE = True
except ImportError:
    NBEATS_AVAILABLE = False

try:
    from app.ml.models.tft_forecast import (
        TFTForecaster,
        TFTConfig,
        TFTForecast,
    )
    TFT_AVAILABLE = True
except ImportError:
    TFT_AVAILABLE = False

try:
    from app.ml.models.deepar_forecast import (
        DeepARForecaster,
        DeepARConfig,
        DeepARForecast,
    )
    DEEPAR_AVAILABLE = True
except ImportError:
    DEEPAR_AVAILABLE = False


__all__ = [
    # Core models
    "PyMCMarketingMixModel",
    "ProphetForecaster",
    "CustomMMMModel",
    "ARIMAForecaster",
    "EnsembleForecaster",
    # Availability flags
    "NEURAL_MMM_AVAILABLE",
    "NBEATS_AVAILABLE",
    "TFT_AVAILABLE",
    "DEEPAR_AVAILABLE",
]

# Conditionally export neural models
if NEURAL_MMM_AVAILABLE:
    __all__.extend([
        "NeuralMMMModel",
        "NeuralMMMTrainer",
        "NeuralMMMConfig",
        "DifferentiableAdstock",
        "DifferentiableSaturation",
    ])

if NBEATS_AVAILABLE:
    __all__.extend([
        "NBeatsForecaster",
        "NBeatsConfig",
        "NBeatsForecast",
    ])

if TFT_AVAILABLE:
    __all__.extend([
        "TFTForecaster",
        "TFTConfig",
        "TFTForecast",
    ])

if DEEPAR_AVAILABLE:
    __all__.extend([
        "DeepARForecaster",
        "DeepARConfig",
        "DeepARForecast",
    ])
