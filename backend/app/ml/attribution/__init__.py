"""
Multi-Touch Attribution Module

This module provides various attribution models for measuring
marketing channel effectiveness:
- Position-based attribution (first-touch, last-touch, U-shaped)
- Shapley value attribution
- Markov chain attribution
"""

from .mta import (
    MultiTouchAttribution,
    AttributionModel,
    AttributionResult,
    TouchpointData,
)
from .shapley import ShapleyAttribution
from .markov import MarkovAttribution, TransitionMatrix

__all__ = [
    "MultiTouchAttribution",
    "AttributionModel",
    "AttributionResult",
    "TouchpointData",
    "ShapleyAttribution",
    "MarkovAttribution",
    "TransitionMatrix",
]
