"""
Causal Inference Module

This module provides causal inference and experimentation tools including:
- GeoLift testing (Meta methodology)
- Synthetic control methods
- Experiment design and power analysis
- DAG-based causal discovery
"""

from .geo_lift import GeoLiftAnalyzer, GeoLiftResult
from .synthetic_control import SyntheticControlAnalyzer, SyntheticControlResult
from .experiment_design import ExperimentDesigner, PowerAnalysisResult
from .notears import NOTEARSDiscovery
from .dag_discovery import DAGDiscovery, CausalGraph

__all__ = [
    "GeoLiftAnalyzer",
    "GeoLiftResult",
    "SyntheticControlAnalyzer",
    "SyntheticControlResult",
    "ExperimentDesigner",
    "PowerAnalysisResult",
    "NOTEARSDiscovery",
    "DAGDiscovery",
    "CausalGraph",
]
