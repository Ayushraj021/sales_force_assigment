"""
Narrative Generator Module.

Generates natural language narratives from analytics data.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class NarrativeSection:
    """A section of a narrative."""

    title: str
    content: str
    priority: int = 1  # 1 = high, 2 = medium, 3 = low
    data: Optional[Dict[str, Any]] = None


class NarrativeGenerator:
    """
    Generates natural language narratives from analytics data.

    Used to create executive summaries and insights that LLMs
    can easily process and present to users.

    Example:
        generator = NarrativeGenerator()
        narrative = generator.generate_performance_narrative(model_metrics)
    """

    def generate_performance_narrative(
        self,
        metrics: Dict[str, Any],
        model_name: str = "Model",
    ) -> str:
        """
        Generate narrative for model performance.

        Args:
            metrics: Model performance metrics
            model_name: Name of the model

        Returns:
            Natural language narrative
        """
        mape = metrics.get("mape", 0)
        r2 = metrics.get("r2", 0)

        # Determine overall assessment
        if mape < 0.08 and r2 > 0.90:
            assessment = "excellent"
            recommendation = "ready for production deployment"
        elif mape < 0.12 and r2 > 0.80:
            assessment = "good"
            recommendation = "suitable for production with monitoring"
        elif mape < 0.20 and r2 > 0.70:
            assessment = "acceptable"
            recommendation = "consider optimization before production"
        else:
            assessment = "needs improvement"
            recommendation = "requires retraining or feature engineering"

        narrative = f"""## {model_name} Performance Summary

**Overall Assessment: {assessment.title()}**

{model_name} achieves a {mape*100:.1f}% mean absolute percentage error (MAPE), meaning predictions are typically within {mape*100:.1f}% of actual values. The model explains {r2*100:.0f}% of the variance in sales (R² = {r2:.3f}).

### Key Findings
- Prediction accuracy: {self._describe_accuracy(mape)}
- Model fit: {self._describe_fit(r2)}
- Reliability: {self._describe_reliability(metrics)}

### Recommendation
{model_name} is **{recommendation}**.
"""
        return narrative

    def generate_optimization_narrative(
        self,
        optimization: Dict[str, Any],
    ) -> str:
        """
        Generate narrative for budget optimization results.

        Args:
            optimization: Optimization results

        Returns:
            Natural language narrative
        """
        budget = optimization.get("total_budget", 0)
        expected_return = optimization.get("expected_return", 0)
        roi = optimization.get("roi", 0)
        allocation = optimization.get("allocation", {})

        # Get top channels
        sorted_channels = sorted(
            allocation.items(),
            key=lambda x: x[1].get("amount", 0),
            reverse=True,
        )

        top_3 = sorted_channels[:3]

        narrative = f"""## Budget Optimization Results

**Optimized Budget: ${budget:,.0f}**
**Expected Return: ${expected_return:,.0f} ({roi*100:.1f}% ROI)**

### Recommended Allocation

"""
        for channel, details in top_3:
            amount = details.get("amount", 0)
            pct = (amount / budget * 100) if budget else 0
            narrative += f"- **{channel.replace('_', ' ').title()}**: ${amount:,.0f} ({pct:.0f}%)\n"

        if len(sorted_channels) > 3:
            other_amount = sum(
                ch[1].get("amount", 0) for ch in sorted_channels[3:]
            )
            narrative += f"- Other channels: ${other_amount:,.0f}\n"

        narrative += f"""
### Key Insights

1. Focus investment on {top_3[0][0].replace('_', ' ')} for highest returns
2. Total expected return of ${expected_return:,.0f} from ${budget:,.0f} investment
3. Projected ROI of {roi*100:.1f}% exceeds typical marketing benchmarks
"""
        return narrative

    def generate_data_quality_narrative(
        self,
        quality: Dict[str, Any],
    ) -> str:
        """
        Generate narrative for data quality assessment.

        Args:
            quality: Quality metrics

        Returns:
            Natural language narrative
        """
        level = quality.get("quality_level", "unknown")
        score = quality.get("overall_score", 0)
        issues = quality.get("issues", [])
        recommendations = quality.get("recommendations", [])

        narrative = f"""## Data Quality Assessment

**Quality Level: {level.title()}** (Score: {score*100:.0f}%)

"""
        if issues and issues != ["No significant issues detected"]:
            narrative += "### Issues Identified\n\n"
            for issue in issues:
                narrative += f"- ⚠️ {issue}\n"
            narrative += "\n"

        if recommendations:
            narrative += "### Recommendations\n\n"
            for rec in recommendations:
                narrative += f"- {rec}\n"

        return narrative

    def _describe_accuracy(self, mape: float) -> str:
        """Describe accuracy in plain language."""
        if mape < 0.05:
            return "Exceptional - predictions within 5% of actual values"
        elif mape < 0.10:
            return "Very good - predictions within 10% of actual values"
        elif mape < 0.15:
            return "Acceptable - predictions within 15% of actual values"
        else:
            return "Needs improvement - prediction error exceeds 15%"

    def _describe_fit(self, r2: float) -> str:
        """Describe model fit in plain language."""
        if r2 > 0.95:
            return f"Excellent fit, explaining {r2*100:.0f}% of variation"
        elif r2 > 0.85:
            return f"Good fit, explaining {r2*100:.0f}% of variation"
        elif r2 > 0.70:
            return f"Moderate fit, explaining {r2*100:.0f}% of variation"
        else:
            return f"Weak fit, only explaining {r2*100:.0f}% of variation"

    def _describe_reliability(self, metrics: Dict[str, Any]) -> str:
        """Describe model reliability."""
        rhat = metrics.get("rhat_max", 1.0)
        ess = metrics.get("ess_min", 400)

        if rhat < 1.05 and ess > 400:
            return "High reliability with good convergence"
        elif rhat < 1.10 and ess > 200:
            return "Acceptable reliability"
        else:
            return "Reliability concerns - review convergence"


def generate_executive_summary(
    data: Dict[str, Any],
    summary_type: str = "general",
) -> str:
    """
    Generate an executive summary from analytics data.

    Args:
        data: Analytics data to summarize
        summary_type: Type of summary to generate

    Returns:
        Executive summary text
    """
    generator = NarrativeGenerator()

    sections = []

    # Model performance section
    if "model_performance" in data:
        sections.append(
            generator.generate_performance_narrative(
                data["model_performance"],
                data.get("model_name", "Model"),
            )
        )

    # Optimization section
    if "optimization" in data:
        sections.append(
            generator.generate_optimization_narrative(data["optimization"])
        )

    # Data quality section
    if "data_quality" in data:
        sections.append(
            generator.generate_data_quality_narrative(data["data_quality"])
        )

    if not sections:
        return "No data available for executive summary."

    # Combine sections
    return "\n---\n".join(sections)


def format_for_stakeholder(
    content: str,
    audience: str = "executive",
) -> str:
    """
    Format content for specific stakeholder audience.

    Args:
        content: Raw content to format
        audience: Target audience

    Returns:
        Formatted content
    """
    if audience == "executive":
        # Keep high-level, remove technical details
        lines = content.split("\n")
        filtered = []
        skip_technical = False

        for line in lines:
            # Skip technical sections
            if "convergence" in line.lower() or "r-hat" in line.lower():
                skip_technical = True
                continue
            if skip_technical and line.startswith("#"):
                skip_technical = False

            if not skip_technical:
                filtered.append(line)

        return "\n".join(filtered)

    elif audience == "technical":
        # Include all technical details
        return content

    elif audience == "marketing":
        # Focus on ROI and channel performance
        lines = content.split("\n")
        marketing_relevant = []

        for line in lines:
            if any(
                keyword in line.lower()
                for keyword in ["roi", "channel", "budget", "spend", "revenue", "conversion"]
            ):
                marketing_relevant.append(line)
            elif line.startswith("#"):
                marketing_relevant.append(line)

        return "\n".join(marketing_relevant)

    return content
