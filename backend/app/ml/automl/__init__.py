"""
AutoML Module

Automated machine learning for model selection and hyperparameter tuning.
"""

from .model_selector import (
    AutoMLSelector,
    AutoMLConfig,
    ModelCandidate,
    AutoMLResult,
)
from .hyperopt_tuner import (
    HyperparameterTuner,
    TunerConfig,
    TrialResult,
    OptimizationHistory,
)

__all__ = [
    "AutoMLSelector",
    "AutoMLConfig",
    "ModelCandidate",
    "AutoMLResult",
    "HyperparameterTuner",
    "TunerConfig",
    "TrialResult",
    "OptimizationHistory",
]
