"""
MCP Formatters Module.

Transforms raw analytics data into LLM-digestible insights.
"""

from app.mcp.formatters.insight_formatter import (
    InsightFormatter,
    format_model_performance,
    format_data_quality,
    format_forecast_results,
    format_optimization_results,
)
from app.mcp.formatters.narrative_generator import (
    NarrativeGenerator,
    generate_executive_summary,
)

__all__ = [
    "InsightFormatter",
    "format_model_performance",
    "format_data_quality",
    "format_forecast_results",
    "format_optimization_results",
    "NarrativeGenerator",
    "generate_executive_summary",
]
