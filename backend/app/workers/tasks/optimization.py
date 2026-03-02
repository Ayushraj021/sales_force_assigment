"""Budget optimization tasks."""

from typing import Any, Dict, List
from uuid import UUID

import structlog
from celery import shared_task

from app.workers.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(bind=True, name="run_budget_optimization")
def run_budget_optimization(
    self,
    scenario_id: str,
    model_id: str,
    config: Dict[str, Any],
    user_id: str,
) -> Dict[str, Any]:
    """Run budget optimization for a scenario.

    Args:
        scenario_id: UUID of the budget scenario.
        model_id: UUID of the MMM model to use.
        config: Optimization configuration.
        user_id: UUID of the user who initiated optimization.

    Returns:
        Dictionary with optimization results.
    """
    logger.info(
        "Starting budget optimization task",
        scenario_id=scenario_id,
        model_id=model_id,
        task_id=self.request.id,
    )

    try:
        self.update_state(state="PROGRESS", meta={"status": "loading_model"})

        # Load model and get response parameters
        # TODO: Load from database/MLflow

        self.update_state(state="PROGRESS", meta={"status": "optimizing"})

        from app.ml.optimization.optimizer import BudgetOptimizer, OptimizationConfig, ChannelConstraint

        # Build channel constraints
        channel_constraints = []
        for constraint in config.get("constraints", []):
            channel_constraints.append(
                ChannelConstraint(
                    channel_name=constraint["channel_name"],
                    min_spend=constraint.get("min_spend"),
                    max_spend=constraint.get("max_spend"),
                    min_ratio=constraint.get("min_ratio"),
                    max_ratio=constraint.get("max_ratio"),
                    fixed_spend=constraint.get("fixed_spend"),
                    max_increase_pct=constraint.get("max_increase_pct"),
                    max_decrease_pct=constraint.get("max_decrease_pct"),
                )
            )

        # Create optimizer config
        opt_config = OptimizationConfig(
            objective=config.get("objective", "maximize_revenue"),
            total_budget=config["total_budget"],
            periods=config.get("periods", 1),
            channel_constraints=channel_constraints,
            response_params=config.get("response_params", {}),
        )

        optimizer = BudgetOptimizer(opt_config)

        # Run optimization
        channels = config.get("channels", [])
        baseline_spend = config.get("baseline_spend", {})

        result = optimizer.optimize(
            channels=channels,
            baseline_spend=baseline_spend,
        )

        self.update_state(state="PROGRESS", meta={"status": "saving"})

        # Save results
        # TODO: Save to database

        logger.info("Budget optimization completed", scenario_id=scenario_id)

        return {
            "status": "success",
            "scenario_id": scenario_id,
            "result": result,
        }

    except Exception as e:
        logger.exception("Budget optimization failed", scenario_id=scenario_id)
        return {
            "status": "failed",
            "scenario_id": scenario_id,
            "error": str(e),
        }


@celery_app.task(bind=True, name="run_what_if_analysis")
def run_what_if_analysis(
    self,
    model_id: str,
    scenarios: List[Dict[str, float]],
    user_id: str,
) -> Dict[str, Any]:
    """Run what-if analysis for multiple spend scenarios.

    Args:
        model_id: UUID of the MMM model.
        scenarios: List of spend scenarios (channel -> spend mappings).
        user_id: UUID of the user.

    Returns:
        Dictionary with what-if analysis results.
    """
    logger.info(
        "Starting what-if analysis task",
        model_id=model_id,
        n_scenarios=len(scenarios),
        task_id=self.request.id,
    )

    try:
        self.update_state(state="PROGRESS", meta={"status": "analyzing"})

        from app.ml.optimization.optimizer import BudgetOptimizer, OptimizationConfig

        # Load model response parameters
        # TODO: Load from database
        response_params = {}

        optimizer = BudgetOptimizer(
            OptimizationConfig(
                total_budget=0,  # Not used for what-if
                response_params=response_params,
            )
        )

        channels = list(scenarios[0].keys()) if scenarios else []
        results_df = optimizer.what_if_analysis(channels, scenarios)

        logger.info("What-if analysis completed", model_id=model_id)

        return {
            "status": "success",
            "model_id": model_id,
            "results": results_df.to_dict(orient="records"),
        }

    except Exception as e:
        logger.exception("What-if analysis failed", model_id=model_id)
        return {
            "status": "failed",
            "model_id": model_id,
            "error": str(e),
        }
