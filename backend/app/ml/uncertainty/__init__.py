"""
Uncertainty Quantification Module

Provides tools for uncertainty estimation and calibration:
- Conformal Prediction: Distribution-free prediction intervals
- Probability Calibration: Ensuring well-calibrated probabilities
- Ensemble Uncertainty: Using model ensembles for uncertainty
"""

from .conformal import (
    ConformalPredictor,
    ConformalConfig,
    ConformalPrediction,
    ConformityScore,
)
from .calibration import (
    ProbabilityCalibrator,
    CalibrationConfig,
    CalibrationResult,
    CalibrationMetrics,
)

__all__ = [
    # Conformal Prediction
    "ConformalPredictor",
    "ConformalConfig",
    "ConformalPrediction",
    "ConformityScore",
    # Calibration
    "ProbabilityCalibrator",
    "CalibrationConfig",
    "CalibrationResult",
    "CalibrationMetrics",
]
