"""
Insight Formatter Module.

Transforms raw analytics data into LLM-digestible insights.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from enum import Enum


class PerformanceGrade(str, Enum):
    """Performance grade for models."""

    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"


class QualityLevel(str, Enum):
    """Data quality level."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    CRITICAL = "critical"


@dataclass
class InsightContext:
    """Context for insight generation."""

    org_id: str
    user_role: str
    detail_level: str = "summary"  # "summary", "detailed", "technical"


class InsightFormatter:
    """
    Transforms raw analytics data into LLM-friendly insights.

    Principles:
    1. Summarize, don't dump - Provide insights, not raw metrics
    2. Include interpretations - Natural language explanations
    3. Suggest next actions - What the LLM might do next
    4. Respect token budgets - Progressive summarization

    Example:
        formatter = InsightFormatter()
        insights = formatter.format_model_metrics(raw_metrics)
    """

    def format_model_performance(
        self,
        raw_metrics: Dict[str, Any],
        model_type: str = "mmm",
    ) -> Dict[str, Any]:
        """
        Transform raw model metrics into LLM-friendly insights.

        Args:
            raw_metrics: Raw performance metrics
            model_type: Type of model (mmm, prophet, etc.)

        Returns:
            Formatted insights
        """
        mape = raw_metrics.get("mape", 0)
        rmse = raw_metrics.get("rmse", 0)
        r2 = raw_metrics.get("r2", 0)
        rhat_max = raw_metrics.get("rhat_max", 1.0)
        ess_min = raw_metrics.get("ess_min", 400)

        # Determine grade
        grade = self._grade_model_performance(mape, r2, rhat_max, ess_min)

        # Generate interpretations
        accuracy_interpretation = self._interpret_accuracy(mape)
        fit_interpretation = self._interpret_fit(r2)
        reliability = self._assess_reliability(rhat_max, ess_min)

        # Generate recommendations
        recommendations = self._generate_performance_recommendations(
            grade, mape, r2, rhat_max, ess_min
        )

        return {
            "performance_grade": grade.value,
            "summary": self._generate_performance_summary(
                grade, mape, r2, model_type
            ),
            "key_metrics": {
                "accuracy": {
                    "mape": round(mape, 4),
                    "interpretation": accuracy_interpretation,
                },
                "fit": {
                    "r2": round(r2, 4),
                    "rmse": round(rmse, 2),
                    "interpretation": fit_interpretation,
                },
            },
            "reliability": reliability,
            "recommendations": recommendations,
        }

    def _grade_model_performance(
        self,
        mape: float,
        r2: float,
        rhat_max: float,
        ess_min: int,
    ) -> PerformanceGrade:
        """Grade model performance."""
        # Score based on metrics
        score = 0

        # MAPE scoring (lower is better)
        if mape < 0.05:
            score += 3
        elif mape < 0.10:
            score += 2
        elif mape < 0.20:
            score += 1

        # R2 scoring (higher is better)
        if r2 > 0.95:
            score += 3
        elif r2 > 0.85:
            score += 2
        elif r2 > 0.70:
            score += 1

        # Convergence scoring
        if rhat_max < 1.05 and ess_min > 400:
            score += 2
        elif rhat_max < 1.10 and ess_min > 200:
            score += 1

        # Map score to grade
        if score >= 7:
            return PerformanceGrade.EXCELLENT
        elif score >= 5:
            return PerformanceGrade.GOOD
        elif score >= 3:
            return PerformanceGrade.FAIR
        elif score >= 1:
            return PerformanceGrade.POOR
        else:
            return PerformanceGrade.CRITICAL

    def _interpret_accuracy(self, mape: float) -> str:
        """Generate accuracy interpretation."""
        pct = mape * 100
        if mape < 0.05:
            return f"{pct:.1f}% average prediction error - exceptionally accurate"
        elif mape < 0.10:
            return f"{pct:.1f}% average prediction error - highly accurate"
        elif mape < 0.15:
            return f"{pct:.1f}% average prediction error - acceptable accuracy"
        elif mape < 0.25:
            return f"{pct:.1f}% average prediction error - moderate accuracy, consider retraining"
        else:
            return f"{pct:.1f}% average prediction error - poor accuracy, needs improvement"

    def _interpret_fit(self, r2: float) -> str:
        """Generate fit interpretation."""
        pct = r2 * 100
        if r2 > 0.95:
            return f"Explains {pct:.0f}% of variance - excellent fit"
        elif r2 > 0.85:
            return f"Explains {pct:.0f}% of variance - good fit"
        elif r2 > 0.70:
            return f"Explains {pct:.0f}% of variance - acceptable fit"
        elif r2 > 0.50:
            return f"Explains {pct:.0f}% of variance - weak fit, consider additional features"
        else:
            return f"Explains {pct:.0f}% of variance - poor fit, review model specification"

    def _assess_reliability(
        self,
        rhat_max: float,
        ess_min: int,
    ) -> Dict[str, Any]:
        """Assess model reliability."""
        if rhat_max < 1.05 and ess_min > 400:
            assessment = "high"
            details = "Good convergence (R-hat < 1.05), sufficient samples (ESS > 400)"
        elif rhat_max < 1.10 and ess_min > 200:
            assessment = "medium"
            details = "Acceptable convergence, consider longer chains for production"
        else:
            assessment = "low"
            details = f"Convergence issues detected (R-hat: {rhat_max:.2f}, ESS: {ess_min})"

        return {
            "assessment": assessment,
            "details": details,
            "rhat_max": round(rhat_max, 3),
            "ess_min": ess_min,
        }

    def _generate_performance_summary(
        self,
        grade: PerformanceGrade,
        mape: float,
        r2: float,
        model_type: str,
    ) -> str:
        """Generate performance summary text."""
        pct_error = mape * 100
        pct_explained = r2 * 100

        if grade == PerformanceGrade.EXCELLENT:
            return (
                f"Model shows strong predictive accuracy with {pct_error:.1f}% mean error. "
                f"It explains {pct_explained:.0f}% of sales variance, outperforming typical {model_type.upper()}s."
            )
        elif grade == PerformanceGrade.GOOD:
            return (
                f"Model performs well with {pct_error:.1f}% mean error and explains "
                f"{pct_explained:.0f}% of variance. Ready for production use."
            )
        elif grade == PerformanceGrade.FAIR:
            return (
                f"Model shows acceptable performance ({pct_error:.1f}% error, {pct_explained:.0f}% variance explained) "
                f"but could benefit from optimization."
            )
        else:
            return (
                f"Model needs improvement: {pct_error:.1f}% mean error with only "
                f"{pct_explained:.0f}% variance explained."
            )

    def _generate_performance_recommendations(
        self,
        grade: PerformanceGrade,
        mape: float,
        r2: float,
        rhat_max: float,
        ess_min: int,
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        if grade == PerformanceGrade.EXCELLENT:
            recommendations.append("Model is ready for production deployment")
            recommendations.append("Consider monitoring for data drift quarterly")
        elif grade == PerformanceGrade.GOOD:
            recommendations.append("Model is suitable for production with monitoring")
            if mape > 0.08:
                recommendations.append("Consider feature engineering to reduce prediction error")

        if rhat_max > 1.05:
            recommendations.append("Increase MCMC chains or iterations for better convergence")

        if ess_min < 400:
            recommendations.append("Increase effective sample size by running longer chains")

        if r2 < 0.80:
            recommendations.append("Consider adding external features (weather, economic indicators)")

        if mape > 0.15:
            recommendations.append("Review data quality and consider outlier treatment")
            recommendations.append("Try alternative model architectures")

        return recommendations


def format_model_performance(
    raw_metrics: Dict[str, Any],
    model_type: str = "mmm",
) -> Dict[str, Any]:
    """Format model performance metrics."""
    formatter = InsightFormatter()
    return formatter.format_model_performance(raw_metrics, model_type)


def format_data_quality(
    quality_report: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Format data quality report for LLM consumption.

    Args:
        quality_report: Raw quality metrics

    Returns:
        Formatted quality insights
    """
    completeness = quality_report.get("completeness", 0)
    validity = quality_report.get("validity", 0)
    consistency = quality_report.get("consistency", 0)
    uniqueness = quality_report.get("uniqueness", 0)

    # Calculate overall score
    overall_score = (completeness + validity + consistency + uniqueness) / 4

    # Determine quality level
    if overall_score >= 0.95:
        level = QualityLevel.HIGH
        summary = "Data quality is excellent. Ready for analysis."
    elif overall_score >= 0.85:
        level = QualityLevel.MEDIUM
        summary = "Data quality is acceptable with minor issues."
    elif overall_score >= 0.70:
        level = QualityLevel.LOW
        summary = "Data quality issues detected. Review recommended."
    else:
        level = QualityLevel.CRITICAL
        summary = "Significant data quality issues. Remediation required."

    # Generate issues list
    issues = []
    if completeness < 0.95:
        missing_pct = (1 - completeness) * 100
        issues.append(f"{missing_pct:.1f}% missing values detected")
    if validity < 0.95:
        issues.append("Some values fail validation rules")
    if consistency < 0.95:
        issues.append("Inconsistent data patterns found")
    if uniqueness < 0.95:
        dup_pct = (1 - uniqueness) * 100
        issues.append(f"{dup_pct:.1f}% duplicate records found")

    # Generate recommendations
    recommendations = []
    if completeness < 0.95:
        recommendations.append("Implement data imputation strategy")
    if validity < 0.95:
        recommendations.append("Review and correct invalid entries")
    if consistency < 0.95:
        recommendations.append("Standardize data formats and values")
    if uniqueness < 0.95:
        recommendations.append("Deduplicate records before analysis")

    return {
        "quality_level": level.value,
        "overall_score": round(overall_score, 3),
        "summary": summary,
        "dimensions": {
            "completeness": {
                "score": round(completeness, 3),
                "interpretation": f"{completeness*100:.1f}% of expected data present",
            },
            "validity": {
                "score": round(validity, 3),
                "interpretation": f"{validity*100:.1f}% of values pass validation",
            },
            "consistency": {
                "score": round(consistency, 3),
                "interpretation": f"{consistency*100:.1f}% of data is consistent",
            },
            "uniqueness": {
                "score": round(uniqueness, 3),
                "interpretation": f"{uniqueness*100:.1f}% unique records",
            },
        },
        "issues": issues if issues else ["No significant issues detected"],
        "recommendations": recommendations if recommendations else ["Data is ready for use"],
    }


def format_forecast_results(
    forecast: Dict[str, Any],
    historical: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Format forecast results for LLM consumption.

    Args:
        forecast: Raw forecast data
        historical: Optional historical comparison

    Returns:
        Formatted forecast insights
    """
    predictions = forecast.get("predictions", [])
    confidence = forecast.get("confidence_intervals", {})

    if not predictions:
        return {
            "summary": "No forecast data available",
            "predictions": [],
        }

    # Calculate summary statistics
    total_predicted = sum(p.get("value", 0) for p in predictions)
    avg_predicted = total_predicted / len(predictions) if predictions else 0
    horizon = len(predictions)

    # Calculate trend
    if len(predictions) >= 2:
        first_half = predictions[: horizon // 2]
        second_half = predictions[horizon // 2:]
        first_avg = sum(p.get("value", 0) for p in first_half) / len(first_half)
        second_avg = sum(p.get("value", 0) for p in second_half) / len(second_half)
        trend_pct = ((second_avg - first_avg) / first_avg * 100) if first_avg else 0
        trend = "increasing" if trend_pct > 2 else "decreasing" if trend_pct < -2 else "stable"
    else:
        trend = "stable"
        trend_pct = 0

    # Format summary
    summary = (
        f"Forecast covers {horizon} periods with total predicted value of {total_predicted:,.0f}. "
        f"Trend is {trend} ({trend_pct:+.1f}% change)."
    )

    return {
        "summary": summary,
        "horizon": horizon,
        "total_predicted": round(total_predicted, 2),
        "average_predicted": round(avg_predicted, 2),
        "trend": {
            "direction": trend,
            "change_percent": round(trend_pct, 2),
        },
        "confidence": {
            "level": confidence.get("level", 0.95),
            "interpretation": f"{confidence.get('level', 0.95)*100:.0f}% confidence intervals provided",
        },
        "key_periods": _identify_key_periods(predictions),
    }


def _identify_key_periods(predictions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Identify key periods in forecast."""
    if not predictions:
        return []

    # Find max and min periods
    values = [(i, p.get("value", 0)) for i, p in enumerate(predictions)]
    sorted_values = sorted(values, key=lambda x: x[1], reverse=True)

    key_periods = []

    if sorted_values:
        max_idx, max_val = sorted_values[0]
        key_periods.append({
            "type": "peak",
            "period_index": max_idx,
            "value": round(max_val, 2),
            "description": f"Highest predicted period ({max_val:,.0f})",
        })

        min_idx, min_val = sorted_values[-1]
        key_periods.append({
            "type": "trough",
            "period_index": min_idx,
            "value": round(min_val, 2),
            "description": f"Lowest predicted period ({min_val:,.0f})",
        })

    return key_periods


def format_optimization_results(
    optimization: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Format budget optimization results for LLM consumption.

    Args:
        optimization: Raw optimization results

    Returns:
        Formatted optimization insights
    """
    budget = optimization.get("total_budget", 0)
    allocation = optimization.get("allocation", {})
    expected_return = optimization.get("expected_return", 0)
    roi = optimization.get("roi", 0)

    # Calculate allocation summary
    sorted_channels = sorted(
        allocation.items(),
        key=lambda x: x[1].get("amount", 0),
        reverse=True,
    )

    top_channels = sorted_channels[:3]
    other_amount = sum(
        ch[1].get("amount", 0) for ch in sorted_channels[3:]
    )

    # Generate summary
    summary = (
        f"Optimal allocation of ${budget:,.0f} budget across {len(allocation)} channels "
        f"yields expected return of ${expected_return:,.0f} ({roi*100:.1f}% ROI)."
    )

    # Format channel allocations
    channel_insights = []
    for channel, details in top_channels:
        pct = (details.get("amount", 0) / budget * 100) if budget else 0
        channel_insights.append({
            "channel": channel,
            "allocation": round(details.get("amount", 0), 2),
            "percentage": round(pct, 1),
            "expected_contribution": round(details.get("contribution", 0), 2),
            "efficiency_rank": details.get("efficiency_rank", "N/A"),
        })

    # Generate recommendations
    recommendations = []
    if top_channels:
        top_channel = top_channels[0][0]
        recommendations.append(f"Prioritize {top_channel} with highest allocation")

    if other_amount > 0:
        recommendations.append(
            f"Consolidate smaller channels (${other_amount:,.0f} combined) if resource-constrained"
        )

    return {
        "summary": summary,
        "total_budget": round(budget, 2),
        "expected_return": round(expected_return, 2),
        "roi": round(roi, 4),
        "top_channels": channel_insights,
        "recommendations": recommendations,
    }
