"""
Workflow Prompts for MCP.

Provides common workflow prompt templates for analytics scenarios.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PromptArgument:
    """Prompt argument definition."""

    name: str
    description: str
    required: bool = True


@dataclass
class WorkflowPrompt:
    """
    MCP Prompt template for common workflows.

    Example:
        prompt = WorkflowPrompt(
            name="analyze_campaign",
            description="Analyze campaign performance",
            template="Analyze the performance of campaign {campaign_id}...",
        )
    """

    name: str
    description: str
    template: str
    arguments: List[PromptArgument] = field(default_factory=list)
    category: str = "general"
    tags: List[str] = field(default_factory=list)

    def get_metadata(self) -> Dict[str, Any]:
        """Get prompt metadata for MCP listing."""
        return {
            "name": self.name,
            "description": self.description,
            "arguments": [
                {
                    "name": arg.name,
                    "description": arg.description,
                    "required": arg.required,
                }
                for arg in self.arguments
            ],
        }

    def render(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Render the prompt with provided arguments.

        Returns MCP prompt result format.
        """
        # Validate required arguments
        for arg in self.arguments:
            if arg.required and arg.name not in arguments:
                raise ValueError(f"Missing required argument: {arg.name}")

        # Render template
        rendered = self.template.format(**arguments)

        return {
            "description": self.description,
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": rendered,
                    },
                }
            ],
        }


# Pre-defined workflow prompts
WORKFLOW_PROMPTS: Dict[str, WorkflowPrompt] = {
    "analyze_model_performance": WorkflowPrompt(
        name="analyze_model_performance",
        description="Analyze model performance and provide recommendations",
        template="""Analyze the performance of model {model_id}.

Please provide:
1. Overall performance assessment (accuracy, fit, reliability)
2. Comparison to benchmarks if available
3. Specific recommendations for improvement
4. Whether the model is ready for production

Focus on actionable insights that can guide decision-making.""",
        arguments=[
            PromptArgument("model_id", "ID of the model to analyze"),
        ],
        category="models",
        tags=["analysis", "performance", "recommendations"],
    ),
    "optimize_q4_budget": WorkflowPrompt(
        name="optimize_q4_budget",
        description="Optimize Q4 marketing budget allocation",
        template="""Help me optimize the Q4 marketing budget of ${total_budget:,.0f}.

Context:
- Focus channels: {channels}
- Primary goal: {objective}
- Key constraints: {constraints}

Please:
1. Analyze current channel performance using the model
2. Run budget optimization to find optimal allocation
3. Provide specific dollar recommendations per channel
4. Highlight trade-offs and risks
5. Suggest A/B testing opportunities""",
        arguments=[
            PromptArgument("total_budget", "Total Q4 budget in dollars"),
            PromptArgument("channels", "Comma-separated list of channels"),
            PromptArgument("objective", "Primary optimization objective"),
            PromptArgument("constraints", "Any budget constraints", required=False),
        ],
        category="optimization",
        tags=["budget", "q4", "planning"],
    ),
    "diagnose_forecast_accuracy": WorkflowPrompt(
        name="diagnose_forecast_accuracy",
        description="Diagnose why forecasts may be inaccurate",
        template="""Our forecasts have been {accuracy_status} recently.

Observed issues:
- Forecast period: {forecast_period}
- Actual vs predicted gap: {gap_description}

Please investigate:
1. Check data quality for the training dataset
2. Review model performance metrics
3. Look for data drift or seasonality changes
4. Identify potential feature gaps
5. Recommend specific fixes

Provide a prioritized action plan.""",
        arguments=[
            PromptArgument("accuracy_status", "Description of accuracy (e.g., 'underperforming')"),
            PromptArgument("forecast_period", "Time period of concern"),
            PromptArgument("gap_description", "Description of the accuracy gap"),
        ],
        category="forecasting",
        tags=["diagnosis", "troubleshooting", "accuracy"],
    ),
    "prepare_executive_report": WorkflowPrompt(
        name="prepare_executive_report",
        description="Prepare executive summary of marketing analytics",
        template="""Prepare an executive summary for {audience} covering:

Time Period: {time_period}
Key Metrics: {metrics_focus}

The report should include:
1. Performance highlights (top 3 wins)
2. ROI summary by channel
3. Forecast for next period
4. Budget optimization recommendations
5. Key risks and mitigations

Keep it concise - 1 page max. Use business language, not technical jargon.""",
        arguments=[
            PromptArgument("audience", "Target audience (e.g., 'CMO', 'Board')"),
            PromptArgument("time_period", "Reporting period"),
            PromptArgument("metrics_focus", "Key metrics to highlight"),
        ],
        category="reporting",
        tags=["executive", "summary", "stakeholders"],
    ),
    "compare_model_versions": WorkflowPrompt(
        name="compare_model_versions",
        description="Compare different model versions for deployment decision",
        template="""Compare these model versions to decide which to deploy:

Models to compare: {model_ids}

Evaluation criteria:
1. Accuracy metrics (MAPE, R², RMSE)
2. Convergence quality
3. Business interpretability
4. Inference speed
5. Robustness to edge cases

Provide a clear recommendation with justification.""",
        arguments=[
            PromptArgument("model_ids", "Comma-separated list of model IDs to compare"),
        ],
        category="models",
        tags=["comparison", "deployment", "selection"],
    ),
    "analyze_channel_saturation": WorkflowPrompt(
        name="analyze_channel_saturation",
        description="Analyze channel saturation and spending efficiency",
        template="""Analyze spending efficiency for {channels}.

Current monthly spend: ${current_spend:,.0f}
Target: Understand if we're over/under-investing

Please:
1. Get model parameters for each channel
2. Identify saturation levels
3. Calculate marginal ROI at current spend
4. Recommend optimal spend adjustments
5. Quantify expected impact of changes""",
        arguments=[
            PromptArgument("channels", "Channels to analyze"),
            PromptArgument("current_spend", "Current monthly spend"),
        ],
        category="optimization",
        tags=["saturation", "efficiency", "spending"],
    ),
    "validate_data_pipeline": WorkflowPrompt(
        name="validate_data_pipeline",
        description="Validate data pipeline output before model training",
        template="""Validate the data pipeline output for dataset {dataset_id}.

Pre-training checklist:
1. Run data validation checks
2. Assess data quality scores
3. Preview sample data
4. Verify schema matches model requirements
5. Check for temporal gaps or anomalies

Target model type: {model_type}
Minimum quality threshold: {quality_threshold}%

Flag any issues that could impact model training.""",
        arguments=[
            PromptArgument("dataset_id", "Dataset to validate"),
            PromptArgument("model_type", "Target model type"),
            PromptArgument("quality_threshold", "Minimum quality score (1-100)", required=False),
        ],
        category="data",
        tags=["validation", "pipeline", "quality"],
    ),
    "attribution_deep_dive": WorkflowPrompt(
        name="attribution_deep_dive",
        description="Deep dive into multi-touch attribution",
        template="""Perform attribution analysis for our conversion data.

Dataset: {dataset_id}
Attribution models to compare: {attribution_models}
Conversion window: {conversion_window} days

Analysis should:
1. Run attribution for each model type
2. Compare results across models
3. Identify high-impact touchpoints
4. Recommend optimal attribution model
5. Suggest budget reallocation based on findings""",
        arguments=[
            PromptArgument("dataset_id", "Conversion dataset ID"),
            PromptArgument("attribution_models", "Attribution models to compare"),
            PromptArgument("conversion_window", "Conversion window in days"),
        ],
        category="attribution",
        tags=["multi-touch", "conversions", "analysis"],
    ),
}


def get_available_prompts() -> List[Dict[str, Any]]:
    """Get list of all available prompts."""
    return [prompt.get_metadata() for prompt in WORKFLOW_PROMPTS.values()]


def get_prompt_by_name(name: str) -> Optional[WorkflowPrompt]:
    """Get prompt by name."""
    return WORKFLOW_PROMPTS.get(name)


def get_prompts_by_category(category: str) -> List[WorkflowPrompt]:
    """Get prompts by category."""
    return [p for p in WORKFLOW_PROMPTS.values() if p.category == category]


def get_prompts_by_tag(tag: str) -> List[WorkflowPrompt]:
    """Get prompts that have a specific tag."""
    return [p for p in WORKFLOW_PROMPTS.values() if tag in p.tags]


async def handle_prompt_request(
    name: str,
    arguments: Dict[str, Any],
) -> Dict[str, Any]:
    """Handle MCP prompt get request."""
    prompt = get_prompt_by_name(name)

    if not prompt:
        from app.mcp.core.exceptions import MCPError, MCPErrorCode

        raise MCPError(
            code=MCPErrorCode.RESOURCE_NOT_FOUND,
            message=f"Prompt '{name}' not found",
            recovery_suggestions=[
                "Use prompts/list to see available prompts",
                f"Available prompts: {list(WORKFLOW_PROMPTS.keys())}",
            ],
        )

    return prompt.render(arguments)
