"""
Quality gate evaluation for automated deployment decisions.

Evaluates multiple quality gates to determine if a model
should be automatically deployed to production.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class GateStatus(Enum):
    """Status of a quality gate."""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WARNING = "warning"


class DeploymentDecision(Enum):
    """Deployment decision outcome."""

    AUTO_DEPLOY = "auto_deploy"
    MANUAL_REVIEW = "manual_review"
    REJECT = "reject"


@dataclass
class QualityGateConfig:
    """Configuration for quality gate thresholds."""

    # Performance gates
    mape_improvement_threshold: float = 2.0  # Minimum % improvement
    max_mape: float = 0.15  # Maximum acceptable MAPE
    max_rmse: float = 5000.0  # Maximum acceptable RMSE
    min_r2: float = 0.80  # Minimum acceptable R2

    # Drift gates
    drift_p_value_threshold: float = 0.05  # KS-test p-value threshold

    # Latency gates
    p99_latency_ms: float = 500.0  # Maximum P99 latency

    # Data quality gates
    min_ge_success_rate: float = 0.95  # Great Expectations success rate

    # Required gates for auto-deploy
    required_gates: list[str] | None = None

    def __post_init__(self):
        if self.required_gates is None:
            self.required_gates = [
                "mape_improvement",
                "no_drift",
                "latency",
                "data_quality",
            ]


@dataclass
class GateResult:
    """Result of a single quality gate evaluation."""

    gate_name: str
    status: GateStatus
    value: float | bool | str
    threshold: float | bool | str
    message: str
    is_required: bool = True


class QualityGateEvaluator:
    """
    Evaluates quality gates for model deployment.

    Quality gates checked:
    1. MAPE improvement over champion
    2. No data drift detected
    3. Inference latency within bounds
    4. All Great Expectations checks pass
    5. Absolute performance thresholds met
    """

    def __init__(self, config: QualityGateConfig | None = None):
        self.config = config or QualityGateConfig()
        self.gate_results: list[GateResult] = []

    def evaluate_mape_improvement(
        self,
        champion_mape: float,
        challenger_mape: float,
    ) -> GateResult:
        """Evaluate MAPE improvement gate."""
        if champion_mape == 0:
            improvement = 100.0 if challenger_mape < champion_mape else 0.0
        else:
            improvement = ((champion_mape - challenger_mape) / champion_mape) * 100

        passed = improvement >= self.config.mape_improvement_threshold

        result = GateResult(
            gate_name="mape_improvement",
            status=GateStatus.PASSED if passed else GateStatus.FAILED,
            value=round(improvement, 2),
            threshold=self.config.mape_improvement_threshold,
            message=f"MAPE improvement: {improvement:.2f}% (threshold: {self.config.mape_improvement_threshold}%)",
            is_required="mape_improvement" in (self.config.required_gates or []),
        )
        self.gate_results.append(result)
        return result

    def evaluate_max_mape(self, mape: float) -> GateResult:
        """Evaluate maximum MAPE gate."""
        passed = mape <= self.config.max_mape

        result = GateResult(
            gate_name="max_mape",
            status=GateStatus.PASSED if passed else GateStatus.FAILED,
            value=round(mape, 4),
            threshold=self.config.max_mape,
            message=f"MAPE: {mape:.4f} (threshold: {self.config.max_mape})",
            is_required="max_mape" in (self.config.required_gates or []),
        )
        self.gate_results.append(result)
        return result

    def evaluate_drift(
        self,
        drift_detected: bool,
        drift_score: float = 0.0,
    ) -> GateResult:
        """Evaluate data drift gate."""
        passed = not drift_detected

        result = GateResult(
            gate_name="no_drift",
            status=GateStatus.PASSED if passed else GateStatus.FAILED,
            value=drift_score,
            threshold=self.config.drift_p_value_threshold,
            message=f"Drift detected: {drift_detected} (score: {drift_score:.3f})",
            is_required="no_drift" in (self.config.required_gates or []),
        )
        self.gate_results.append(result)
        return result

    def evaluate_latency(self, p99_latency_ms: float) -> GateResult:
        """Evaluate inference latency gate."""
        passed = p99_latency_ms <= self.config.p99_latency_ms

        result = GateResult(
            gate_name="latency",
            status=GateStatus.PASSED if passed else GateStatus.FAILED,
            value=round(p99_latency_ms, 2),
            threshold=self.config.p99_latency_ms,
            message=f"P99 latency: {p99_latency_ms:.2f}ms (threshold: {self.config.p99_latency_ms}ms)",
            is_required="latency" in (self.config.required_gates or []),
        )
        self.gate_results.append(result)
        return result

    def evaluate_data_quality(
        self,
        ge_success_rate: float,
        ge_passed: bool = True,
    ) -> GateResult:
        """Evaluate Great Expectations data quality gate."""
        passed = ge_passed and ge_success_rate >= self.config.min_ge_success_rate

        result = GateResult(
            gate_name="data_quality",
            status=GateStatus.PASSED if passed else GateStatus.FAILED,
            value=round(ge_success_rate, 4),
            threshold=self.config.min_ge_success_rate,
            message=f"GE success rate: {ge_success_rate:.2%} (threshold: {self.config.min_ge_success_rate:.2%})",
            is_required="data_quality" in (self.config.required_gates or []),
        )
        self.gate_results.append(result)
        return result

    def evaluate_r2(self, r2: float) -> GateResult:
        """Evaluate R2 score gate."""
        passed = r2 >= self.config.min_r2

        result = GateResult(
            gate_name="r2",
            status=GateStatus.PASSED if passed else GateStatus.FAILED,
            value=round(r2, 4),
            threshold=self.config.min_r2,
            message=f"R2: {r2:.4f} (threshold: {self.config.min_r2})",
            is_required="r2" in (self.config.required_gates or []),
        )
        self.gate_results.append(result)
        return result

    def evaluate_all(
        self,
        champion_mape: float,
        challenger_mape: float,
        drift_detected: bool,
        drift_score: float,
        p99_latency_ms: float,
        ge_success_rate: float,
        ge_passed: bool = True,
        r2: float | None = None,
    ) -> dict[str, Any]:
        """
        Evaluate all quality gates.

        Returns comprehensive evaluation result with deployment decision.
        """
        self.gate_results = []

        # Evaluate all gates
        self.evaluate_mape_improvement(champion_mape, challenger_mape)
        self.evaluate_max_mape(challenger_mape)
        self.evaluate_drift(drift_detected, drift_score)
        self.evaluate_latency(p99_latency_ms)
        self.evaluate_data_quality(ge_success_rate, ge_passed)

        if r2 is not None:
            self.evaluate_r2(r2)

        # Determine deployment decision
        required_gates = [g for g in self.gate_results if g.is_required]
        all_required_passed = all(g.status == GateStatus.PASSED for g in required_gates)
        all_gates_passed = all(g.status == GateStatus.PASSED for g in self.gate_results)

        if all_required_passed and all_gates_passed:
            decision = DeploymentDecision.AUTO_DEPLOY
        elif all_required_passed:
            decision = DeploymentDecision.MANUAL_REVIEW
        else:
            decision = DeploymentDecision.REJECT

        return {
            "gates": [
                {
                    "name": g.gate_name,
                    "status": g.status.value,
                    "value": g.value,
                    "threshold": g.threshold,
                    "message": g.message,
                    "is_required": g.is_required,
                }
                for g in self.gate_results
            ],
            "summary": {
                "total_gates": len(self.gate_results),
                "passed_gates": sum(1 for g in self.gate_results if g.status == GateStatus.PASSED),
                "failed_gates": sum(1 for g in self.gate_results if g.status == GateStatus.FAILED),
                "required_gates_passed": sum(
                    1 for g in required_gates if g.status == GateStatus.PASSED
                ),
                "required_gates_total": len(required_gates),
            },
            "decision": {
                "action": decision.value,
                "reason": self._get_decision_reason(decision, all_required_passed, all_gates_passed),
                "auto_deploy_eligible": decision == DeploymentDecision.AUTO_DEPLOY,
            },
            # Fields for Airflow DAG compatibility
            "all_gates_passed": all_gates_passed,
            "mape_improvement": next(
                (g.value for g in self.gate_results if g.gate_name == "mape_improvement"),
                0,
            ),
            "drift_detected": drift_detected,
            "p99_latency_ms": p99_latency_ms,
            "ge_checks_passed": ge_passed,
            "evaluated_at": datetime.now().isoformat(),
        }

    def _get_decision_reason(
        self,
        decision: DeploymentDecision,
        all_required_passed: bool,
        all_gates_passed: bool,
    ) -> str:
        """Generate human-readable decision reason."""
        if decision == DeploymentDecision.AUTO_DEPLOY:
            return "All quality gates passed - model eligible for automatic deployment"
        elif decision == DeploymentDecision.MANUAL_REVIEW:
            failed_optional = [
                g.gate_name for g in self.gate_results
                if g.status == GateStatus.FAILED and not g.is_required
            ]
            return f"Required gates passed but optional gates failed: {', '.join(failed_optional)}"
        else:
            failed_required = [
                g.gate_name for g in self.gate_results
                if g.status == GateStatus.FAILED and g.is_required
            ]
            return f"Required gates failed: {', '.join(failed_required)}"


def evaluate_quality_gates(
    validation_data: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Evaluate quality gates from validation data.

    Args:
        validation_data: Dictionary containing validation results
        config: Optional quality gate configuration

    Returns:
        Quality gate evaluation result with deployment decision
    """
    gate_config = None
    if config:
        gate_config = QualityGateConfig(
            mape_improvement_threshold=config.get("mape_improvement_threshold", 2.0),
            max_mape=config.get("max_mape", 0.15),
            drift_p_value_threshold=config.get("drift_p_value_threshold", 0.05),
            p99_latency_ms=config.get("p99_latency_ms", 500.0),
            min_ge_success_rate=config.get("min_ge_success_rate", 0.95),
            required_gates=config.get("required_gates"),
        )

    evaluator = QualityGateEvaluator(gate_config)

    return evaluator.evaluate_all(
        champion_mape=validation_data.get("champion_mape", 0.0),
        challenger_mape=validation_data.get("challenger_mape", 0.0),
        drift_detected=validation_data.get("drift_detected", False),
        drift_score=validation_data.get("drift_score", 0.0),
        p99_latency_ms=validation_data.get("p99_latency_ms", 0.0),
        ge_success_rate=validation_data.get("ge_success_rate", 1.0),
        ge_passed=validation_data.get("ge_passed", True),
        r2=validation_data.get("r2"),
    )
