"""
Optimization Tools for MCP.

Provides tools for budget optimization, ROI analysis, and attribution.
"""

from typing import Any, Dict, List, Optional

import structlog

from app.mcp.core.auth import MCPTokenClaims
from app.mcp.core.exceptions import MCPError, MCPErrorCode
from app.mcp.formatters.insight_formatter import format_optimization_results
from app.mcp.tools.base import (
    BaseTool,
    ParameterType,
    ToolParameter,
    ToolResult,
)

logger = structlog.get_logger("mcp.tools.optimization")


class OptimizeBudgetTool(BaseTool):
    """
    Run budget optimization.

    Optimizes marketing budget allocation across channels.
    """

    name = "optimize_budget"
    description = "Optimize marketing budget allocation across channels for maximum ROI"
    required_scope = "optimize:execute"

    parameters = [
        ToolParameter(
            name="model_id",
            param_type=ParameterType.STRING,
            description="ID of the model to use for optimization",
            required=True,
        ),
        ToolParameter(
            name="total_budget",
            param_type=ParameterType.NUMBER,
            description="Total budget to allocate",
            required=True,
            minimum=0,
        ),
        ToolParameter(
            name="channels",
            param_type=ParameterType.ARRAY,
            description="Channels to optimize (uses all if not specified)",
            required=False,
        ),
        ToolParameter(
            name="constraints",
            param_type=ParameterType.OBJECT,
            description="Budget constraints per channel (min/max)",
            required=False,
        ),
        ToolParameter(
            name="objective",
            param_type=ParameterType.STRING,
            description="Optimization objective",
            required=False,
            default="maximize_revenue",
            enum=["maximize_revenue", "maximize_roi", "minimize_cpa"],
        ),
    ]

    async def execute(
        self,
        arguments: Dict[str, Any],
        claims: Optional[MCPTokenClaims],
    ) -> ToolResult:
        """Execute budget optimization."""
        model_id = arguments["model_id"]
        total_budget = arguments["total_budget"]
        channels = arguments.get("channels")
        constraints = arguments.get("constraints", {})
        objective = arguments.get("objective", "maximize_revenue")

        self.logger.info(
            "Running budget optimization",
            model_id=model_id,
            total_budget=total_budget,
            objective=objective,
        )

        optimization = await self._run_optimization(
            model_id=model_id,
            total_budget=total_budget,
            channels=channels,
            constraints=constraints,
            objective=objective,
            org_id=claims.org_id if claims else None,
        )

        # Format with insight formatter
        formatted = format_optimization_results(optimization)

        return ToolResult(
            success=True,
            data=formatted,
        )

    async def _run_optimization(
        self,
        model_id: str,
        total_budget: float,
        channels: Optional[List[str]],
        constraints: Dict[str, Any],
        objective: str,
        org_id: Optional[str],
    ) -> Dict[str, Any]:
        """Run budget optimization."""
        if not self.db:
            # Mock optimization result
            channel_list = channels or ["tv_spend", "digital_spend", "social_spend", "email_spend"]

            allocation = {}
            total = 0
            for i, channel in enumerate(channel_list):
                # Simulate optimal allocation
                pct = 0.4 - i * 0.1 if i < 3 else 0.1
                amount = total_budget * pct
                allocation[channel] = {
                    "amount": round(amount, 2),
                    "percentage": round(pct * 100, 1),
                    "contribution": round(amount * 2.5, 2),  # Simulated ROI
                    "efficiency_rank": i + 1,
                }
                total += amount

            expected_return = sum(ch["contribution"] for ch in allocation.values())

            return {
                "model_id": model_id,
                "total_budget": total_budget,
                "objective": objective,
                "allocation": allocation,
                "expected_return": round(expected_return, 2),
                "roi": round((expected_return - total_budget) / total_budget, 4),
            }

        # Real optimization
        from app.ml.optimization.budget_optimizer import BudgetOptimizer

        optimizer = BudgetOptimizer()
        result = await optimizer.optimize(
            model_id=model_id,
            total_budget=total_budget,
            channels=channels,
            constraints=constraints,
            objective=objective,
        )

        return result


class AnalyzeROITool(BaseTool):
    """
    Analyze ROI by channel.

    Provides return on investment analysis per marketing channel.
    """

    name = "analyze_roi"
    description = "Analyze return on investment by marketing channel"
    required_scope = "optimize:read"

    parameters = [
        ToolParameter(
            name="model_id",
            param_type=ParameterType.STRING,
            description="ID of the model to use",
            required=True,
        ),
        ToolParameter(
            name="channels",
            param_type=ParameterType.ARRAY,
            description="Channels to analyze (all if not specified)",
            required=False,
        ),
        ToolParameter(
            name="time_period",
            param_type=ParameterType.STRING,
            description="Time period for analysis",
            required=False,
            default="last_quarter",
            enum=["last_week", "last_month", "last_quarter", "last_year", "all_time"],
        ),
    ]

    async def execute(
        self,
        arguments: Dict[str, Any],
        claims: Optional[MCPTokenClaims],
    ) -> ToolResult:
        """Analyze ROI."""
        model_id = arguments["model_id"]
        channels = arguments.get("channels")
        time_period = arguments.get("time_period", "last_quarter")

        self.logger.info(
            "Analyzing ROI",
            model_id=model_id,
            time_period=time_period,
        )

        analysis = await self._analyze_roi(
            model_id=model_id,
            channels=channels,
            time_period=time_period,
            org_id=claims.org_id if claims else None,
        )

        return ToolResult(
            success=True,
            data=analysis,
        )

    async def _analyze_roi(
        self,
        model_id: str,
        channels: Optional[List[str]],
        time_period: str,
        org_id: Optional[str],
    ) -> Dict[str, Any]:
        """Analyze ROI per channel."""
        if not self.db:
            # Mock ROI analysis
            channel_list = channels or ["tv_spend", "digital_spend", "social_spend", "email_spend"]

            channel_roi = []
            for i, channel in enumerate(channel_list):
                roi = 2.5 - i * 0.4  # Decreasing ROI
                channel_roi.append({
                    "channel": channel,
                    "spend": 50000 - i * 10000,
                    "attributed_revenue": round((50000 - i * 10000) * roi, 2),
                    "roi": round(roi, 2),
                    "marginal_roi": round(roi * 0.7, 2),  # Diminishing returns
                    "efficiency_rank": i + 1,
                })

            # Sort by ROI
            channel_roi.sort(key=lambda x: x["roi"], reverse=True)

            total_spend = sum(ch["spend"] for ch in channel_roi)
            total_revenue = sum(ch["attributed_revenue"] for ch in channel_roi)
            overall_roi = (total_revenue - total_spend) / total_spend

            return {
                "model_id": model_id,
                "time_period": time_period,
                "summary": f"Average ROI of {overall_roi:.0%} across {len(channel_roi)} channels",
                "overall_metrics": {
                    "total_spend": total_spend,
                    "attributed_revenue": round(total_revenue, 2),
                    "overall_roi": round(overall_roi, 4),
                },
                "channels": channel_roi,
                "insights": [
                    f"{channel_roi[0]['channel'].replace('_', ' ').title()} has highest ROI at {channel_roi[0]['roi']:.2f}x",
                    "Consider reallocating from lower-performing channels",
                ],
            }

        # Real implementation
        return {}


class RunWhatIfScenarioTool(BaseTool):
    """
    Run what-if scenario analysis.

    Simulates different budget scenarios and their outcomes.
    """

    name = "run_what_if_scenario"
    description = "Run what-if scenario analysis to simulate different budget allocations"
    required_scope = "optimize:execute"

    parameters = [
        ToolParameter(
            name="model_id",
            param_type=ParameterType.STRING,
            description="ID of the model to use",
            required=True,
        ),
        ToolParameter(
            name="scenario_name",
            param_type=ParameterType.STRING,
            description="Name for this scenario",
            required=True,
        ),
        ToolParameter(
            name="budget_changes",
            param_type=ParameterType.OBJECT,
            description="Budget changes per channel (absolute or percentage)",
            required=True,
        ),
        ToolParameter(
            name="compare_to_baseline",
            param_type=ParameterType.BOOLEAN,
            description="Compare results to current baseline",
            required=False,
            default=True,
        ),
    ]

    async def execute(
        self,
        arguments: Dict[str, Any],
        claims: Optional[MCPTokenClaims],
    ) -> ToolResult:
        """Run what-if scenario."""
        model_id = arguments["model_id"]
        scenario_name = arguments["scenario_name"]
        budget_changes = arguments["budget_changes"]
        compare_to_baseline = arguments.get("compare_to_baseline", True)

        self.logger.info(
            "Running what-if scenario",
            model_id=model_id,
            scenario_name=scenario_name,
        )

        result = await self._run_scenario(
            model_id=model_id,
            scenario_name=scenario_name,
            budget_changes=budget_changes,
            compare_to_baseline=compare_to_baseline,
            org_id=claims.org_id if claims else None,
        )

        return ToolResult(
            success=True,
            data=result,
        )

    async def _run_scenario(
        self,
        model_id: str,
        scenario_name: str,
        budget_changes: Dict[str, Any],
        compare_to_baseline: bool,
        org_id: Optional[str],
    ) -> Dict[str, Any]:
        """Run what-if scenario simulation."""
        if not self.db:
            # Mock scenario simulation
            baseline = {
                "total_budget": 200000,
                "expected_revenue": 500000,
                "roi": 1.5,
            }

            # Apply changes
            scenario_budget = baseline["total_budget"]
            for channel, change in budget_changes.items():
                if isinstance(change, dict):
                    scenario_budget += change.get("delta", 0)

            # Simulate outcome
            revenue_impact = sum(
                change.get("delta", 0) * 2.2 if isinstance(change, dict) else 0
                for change in budget_changes.values()
            )

            scenario = {
                "total_budget": scenario_budget,
                "expected_revenue": baseline["expected_revenue"] + revenue_impact,
                "roi": (baseline["expected_revenue"] + revenue_impact - scenario_budget) / scenario_budget,
            }

            result = {
                "scenario_name": scenario_name,
                "model_id": model_id,
                "scenario_results": scenario,
                "summary": f"Scenario '{scenario_name}' projects {(scenario['roi'] - baseline['roi'])/baseline['roi']*100:+.1f}% change in ROI",
            }

            if compare_to_baseline:
                result["baseline"] = baseline
                result["comparison"] = {
                    "budget_change": scenario["total_budget"] - baseline["total_budget"],
                    "revenue_change": scenario["expected_revenue"] - baseline["expected_revenue"],
                    "roi_change": scenario["roi"] - baseline["roi"],
                }

            return result

        # Real implementation
        from app.ml.simulation.what_if import WhatIfSimulator

        simulator = WhatIfSimulator()
        return await simulator.run_scenario(
            model_id=model_id,
            budget_changes=budget_changes,
        )


class AnalyzeAttributionTool(BaseTool):
    """
    Analyze multi-touch attribution.

    Provides attribution analysis across touchpoints.
    """

    name = "analyze_attribution"
    description = "Analyze multi-touch attribution to understand channel contribution"
    required_scope = "optimize:read"

    parameters = [
        ToolParameter(
            name="model_type",
            param_type=ParameterType.STRING,
            description="Attribution model type",
            required=True,
            enum=["last_touch", "first_touch", "linear", "time_decay", "position_based", "markov", "shapley"],
        ),
        ToolParameter(
            name="dataset_id",
            param_type=ParameterType.STRING,
            description="ID of the conversion dataset",
            required=True,
        ),
        ToolParameter(
            name="conversion_window",
            param_type=ParameterType.INTEGER,
            description="Conversion window in days",
            required=False,
            default=30,
            minimum=1,
            maximum=90,
        ),
    ]

    async def execute(
        self,
        arguments: Dict[str, Any],
        claims: Optional[MCPTokenClaims],
    ) -> ToolResult:
        """Analyze attribution."""
        model_type = arguments["model_type"]
        dataset_id = arguments["dataset_id"]
        conversion_window = arguments.get("conversion_window", 30)

        self.logger.info(
            "Analyzing attribution",
            model_type=model_type,
            dataset_id=dataset_id,
        )

        attribution = await self._analyze_attribution(
            model_type=model_type,
            dataset_id=dataset_id,
            conversion_window=conversion_window,
            org_id=claims.org_id if claims else None,
        )

        return ToolResult(
            success=True,
            data=attribution,
        )

    async def _analyze_attribution(
        self,
        model_type: str,
        dataset_id: str,
        conversion_window: int,
        org_id: Optional[str],
    ) -> Dict[str, Any]:
        """Run attribution analysis."""
        if not self.db:
            # Mock attribution results
            channels = ["organic_search", "paid_search", "social", "email", "direct"]

            attributions = []
            total_conversions = 1000
            remaining = 1.0

            for i, channel in enumerate(channels):
                if i == len(channels) - 1:
                    pct = remaining
                else:
                    pct = remaining * (0.35 - i * 0.05)
                    remaining -= pct

                attributions.append({
                    "channel": channel,
                    "attributed_conversions": round(total_conversions * pct),
                    "attribution_percentage": round(pct * 100, 1),
                    "avg_touchpoints": round(2.5 - i * 0.3, 1),
                })

            # Sort by attribution
            attributions.sort(key=lambda x: x["attributed_conversions"], reverse=True)

            return {
                "model_type": model_type,
                "dataset_id": dataset_id,
                "conversion_window_days": conversion_window,
                "total_conversions": total_conversions,
                "summary": f"Attribution analysis using {model_type} model across {len(channels)} channels",
                "channels": attributions,
                "insights": [
                    f"{attributions[0]['channel'].replace('_', ' ').title()} drives {attributions[0]['attribution_percentage']:.0f}% of conversions",
                    f"Average customer journey involves {sum(a['avg_touchpoints'] for a in attributions)/len(attributions):.1f} touchpoints",
                ],
                "methodology": self._get_methodology_description(model_type),
            }

        # Real implementation
        from app.ml.attribution.multi_touch import MultiTouchAttribution

        mta = MultiTouchAttribution()
        return await mta.analyze(
            dataset_id=dataset_id,
            model_type=model_type,
            conversion_window=conversion_window,
        )

    def _get_methodology_description(self, model_type: str) -> str:
        """Get methodology description for attribution model."""
        descriptions = {
            "last_touch": "Credits 100% of the conversion to the last touchpoint before conversion.",
            "first_touch": "Credits 100% of the conversion to the first touchpoint in the journey.",
            "linear": "Distributes credit equally across all touchpoints in the journey.",
            "time_decay": "Assigns more credit to touchpoints closer to the conversion.",
            "position_based": "Gives 40% credit to first and last touch, 20% distributed among middle touchpoints.",
            "markov": "Uses Markov chains to model transition probabilities between channels.",
            "shapley": "Uses Shapley values from game theory to fairly distribute credit.",
        }
        return descriptions.get(model_type, "Unknown attribution model.")
