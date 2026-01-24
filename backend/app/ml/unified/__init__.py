"""
Unified Measurement Framework

Combines signals from multiple measurement methodologies:
- Marketing Mix Modeling (MMM)
- Multi-Touch Attribution (MTA)
- Geo-Lift Experiments
- Causal Discovery

Provides calibrated, reconciled channel effectiveness estimates.
"""

from .measurement_framework import (
    UnifiedMeasurementFramework,
    MeasurementSignal,
    UnifiedResult,
    SignalWeight,
)
from .reconciliation import (
    SignalReconciler,
    ReconciliationConfig,
    ReconciliationResult,
)

__all__ = [
    "UnifiedMeasurementFramework",
    "MeasurementSignal",
    "UnifiedResult",
    "SignalWeight",
    "SignalReconciler",
    "ReconciliationConfig",
    "ReconciliationResult",
]
