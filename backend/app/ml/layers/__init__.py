"""
Neural Network Layers Module

Custom PyTorch layers for marketing analytics:
- Differentiable adstock transformations
- Differentiable saturation curves
"""

try:
    from ..models.neural_mmm import (
        DifferentiableAdstock,
        DifferentiableSaturation,
        AdstockFunction,
        SaturationFunction,
    )

    __all__ = [
        "DifferentiableAdstock",
        "DifferentiableSaturation",
        "AdstockFunction",
        "SaturationFunction",
    ]
except ImportError:
    # PyTorch not available
    __all__ = []
