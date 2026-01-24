"""
Validation Pipeline DAG - Quality gates and champion/challenger comparison.

This DAG handles:
1. Model performance validation (MAPE, RMSE thresholds)
2. Champion/challenger comparison
3. Inference latency testing
4. Automated quality gate decisions
"""

from datetime import datetime, timedelta
from typing import Any

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import BranchPythonOperator, PythonOperator
from airflow.utils.task_group import TaskGroup

default_args = {
    "owner": "mlops",
    "depends_on_past": False,
    "email_on_failure": True,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
    "execution_timeout": timedelta(hours=1),
}

# Quality gate thresholds
QUALITY_GATES = {
    "mape_improvement_threshold": 2.0,  # Minimum 2% improvement over champion
    "max_mape": 0.15,  # Maximum acceptable MAPE (15%)
    "drift_p_value_threshold": 0.05,  # KS-test p-value for drift detection
    "p99_latency_ms": 500,  # Maximum p99 inference latency
    "min_ge_success_rate": 0.95,  # Minimum Great Expectations success rate
}


def load_challenger_metrics(**context) -> dict:
    """
    Load metrics from the challenger model (new model being validated).
    """
    ti = context["ti"]
    dag_run = context.get("dag_run")
    conf = dag_run.conf if dag_run else {}

    # In production, this would query MLflow
    # client = mlflow.tracking.MlflowClient()
    # run = client.get_run(run_id)

    challenger_metrics = {
        "model_name": "sales-forecast-ensemble",
        "model_version": "challenger",
        "mlflow_run_id": "challenger_run_123",
        "metrics": {
            "test_mape": 0.038,
            "test_rmse": 1180.2,
            "val_mape": 0.042,
            "val_rmse": 1250.5,
            "r2_score": 0.94,
        },
        "training_timestamp": datetime.utcnow().isoformat(),
    }

    ti.xcom_push(key="challenger_metrics", value=challenger_metrics)

    return challenger_metrics


def load_champion_metrics(**context) -> dict:
    """
    Load metrics from the current champion model (production model).
    """
    ti = context["ti"]

    # In production, this would query MLflow Model Registry
    # client = mlflow.tracking.MlflowClient()
    # latest_version = client.get_latest_versions("sales-forecast-ensemble", stages=["Production"])

    champion_metrics = {
        "model_name": "sales-forecast-ensemble",
        "model_version": "1",
        "stage": "Production",
        "mlflow_run_id": "champion_run_abc",
        "metrics": {
            "test_mape": 0.051,
            "test_rmse": 1420.3,
            "val_mape": 0.055,
            "val_rmse": 1480.2,
            "r2_score": 0.91,
        },
        "deployed_timestamp": "2024-01-01T00:00:00",
    }

    ti.xcom_push(key="champion_metrics", value=champion_metrics)

    return champion_metrics


def compare_champion_challenger(**context) -> dict:
    """
    Compare challenger model against champion model.
    """
    ti = context["ti"]

    challenger = ti.xcom_pull(key="challenger_metrics")
    champion = ti.xcom_pull(key="champion_metrics")

    challenger_mape = challenger["metrics"]["test_mape"]
    champion_mape = champion["metrics"]["test_mape"]

    # Calculate improvement
    mape_improvement_pct = ((champion_mape - challenger_mape) / champion_mape) * 100

    comparison_result = {
        "challenger_mape": challenger_mape,
        "champion_mape": champion_mape,
        "mape_improvement_pct": round(mape_improvement_pct, 2),
        "challenger_better": challenger_mape < champion_mape,
        "meets_threshold": mape_improvement_pct >= QUALITY_GATES["mape_improvement_threshold"],
        "comparison_timestamp": datetime.utcnow().isoformat(),
    }

    ti.xcom_push(key="comparison_result", value=comparison_result)

    print(f"Champion vs Challenger: {comparison_result}")

    return comparison_result


def run_latency_tests(**context) -> dict:
    """
    Run inference latency tests on the challenger model.
    """
    import httpx
    import statistics

    ti = context["ti"]
    challenger = ti.xcom_pull(key="challenger_metrics")

    # In production, this would run actual inference tests
    # Simulate latency measurements
    latencies = [45, 52, 48, 51, 47, 55, 49, 53, 46, 50,
                 48, 52, 54, 47, 51, 49, 56, 45, 53, 48]

    # Add some outliers for p99
    latencies.extend([120, 180, 250])

    sorted_latencies = sorted(latencies)
    p50 = sorted_latencies[len(sorted_latencies) // 2]
    p95 = sorted_latencies[int(len(sorted_latencies) * 0.95)]
    p99 = sorted_latencies[int(len(sorted_latencies) * 0.99)]

    latency_result = {
        "model_version": challenger["model_version"],
        "test_requests": len(latencies),
        "latency_ms": {
            "mean": round(statistics.mean(latencies), 2),
            "median": round(statistics.median(latencies), 2),
            "std": round(statistics.stdev(latencies), 2),
            "p50": p50,
            "p95": p95,
            "p99": p99,
            "min": min(latencies),
            "max": max(latencies),
        },
        "meets_threshold": p99 < QUALITY_GATES["p99_latency_ms"],
    }

    ti.xcom_push(key="latency_result", value=latency_result)

    print(f"Latency Test Results: {latency_result}")

    return latency_result


def check_data_quality_results(**context) -> dict:
    """
    Check Great Expectations validation results from data pipeline.
    """
    ti = context["ti"]

    # In production, this would pull from data pipeline or re-run GE
    ge_results = {
        "suite_name": "feature_suite",
        "success": True,
        "success_rate": 0.98,
        "total_expectations": 50,
        "successful_expectations": 49,
        "failed_expectations": 1,
        "failed_details": [
            {
                "expectation": "expect_column_values_to_be_between",
                "column": "impressions",
                "observed_value": -5,
                "reason": "Single negative value detected",
            }
        ],
        "meets_threshold": 0.98 >= QUALITY_GATES["min_ge_success_rate"],
    }

    ti.xcom_push(key="ge_results", value=ge_results)

    return ge_results


def check_drift_results(**context) -> dict:
    """
    Check data drift detection results.
    """
    ti = context["ti"]

    # In production, this would use alibi-detect or custom drift detection
    drift_results = {
        "drift_detected": False,
        "feature_drift_scores": {
            "revenue": {"drift": False, "p_value": 0.42, "statistic": 0.08},
            "impressions": {"drift": False, "p_value": 0.18, "statistic": 0.12},
            "clicks": {"drift": False, "p_value": 0.67, "statistic": 0.05},
            "spend": {"drift": False, "p_value": 0.31, "statistic": 0.09},
        },
        "overall_drift_score": 0.085,
        "drift_threshold": 0.5,
        "meets_threshold": True,
    }

    ti.xcom_push(key="drift_results", value=drift_results)

    return drift_results


def evaluate_quality_gates(**context) -> dict:
    """
    Evaluate all quality gates and determine deployment decision.
    """
    ti = context["ti"]
    dag_run = context.get("dag_run")
    conf = dag_run.conf if dag_run else {}

    auto_deploy = conf.get("auto_deploy", True)

    # Pull all validation results
    comparison = ti.xcom_pull(key="comparison_result")
    latency = ti.xcom_pull(key="latency_result")
    ge_results = ti.xcom_pull(key="ge_results")
    drift_results = ti.xcom_pull(key="drift_results")

    # Evaluate each quality gate
    gates = {
        "mape_improvement": {
            "passed": comparison.get("meets_threshold", False),
            "value": comparison.get("mape_improvement_pct", 0),
            "threshold": QUALITY_GATES["mape_improvement_threshold"],
            "message": f"MAPE improvement: {comparison.get('mape_improvement_pct', 0)}% (threshold: {QUALITY_GATES['mape_improvement_threshold']}%)",
        },
        "latency": {
            "passed": latency.get("meets_threshold", False),
            "value": latency.get("latency_ms", {}).get("p99", 0),
            "threshold": QUALITY_GATES["p99_latency_ms"],
            "message": f"P99 latency: {latency.get('latency_ms', {}).get('p99', 0)}ms (threshold: {QUALITY_GATES['p99_latency_ms']}ms)",
        },
        "data_quality": {
            "passed": ge_results.get("meets_threshold", False),
            "value": ge_results.get("success_rate", 0),
            "threshold": QUALITY_GATES["min_ge_success_rate"],
            "message": f"GE success rate: {ge_results.get('success_rate', 0)} (threshold: {QUALITY_GATES['min_ge_success_rate']})",
        },
        "no_drift": {
            "passed": not drift_results.get("drift_detected", True),
            "value": drift_results.get("overall_drift_score", 1),
            "threshold": 0.5,
            "message": f"Drift score: {drift_results.get('overall_drift_score', 1)} (drift detected: {drift_results.get('drift_detected', True)})",
        },
    }

    # Overall decision
    all_passed = all(gate["passed"] for gate in gates.values())
    critical_gates_passed = gates["mape_improvement"]["passed"] and gates["no_drift"]["passed"]

    validation_results = {
        "quality_gates": gates,
        "all_gates_passed": all_passed,
        "critical_gates_passed": critical_gates_passed,
        "auto_deploy_eligible": auto_deploy and all_passed,
        "recommendation": "deploy" if all_passed else ("manual_review" if critical_gates_passed else "reject"),
        "mape_improvement": comparison.get("mape_improvement_pct", 0),
        "drift_detected": drift_results.get("drift_detected", True),
        "p99_latency_ms": latency.get("latency_ms", {}).get("p99", 0),
        "ge_checks_passed": ge_results.get("success", False),
        "timestamp": datetime.utcnow().isoformat(),
    }

    ti.xcom_push(key="validation_results", value=validation_results)

    # Log results
    print("=" * 60)
    print("QUALITY GATE EVALUATION RESULTS")
    print("=" * 60)
    for gate_name, gate_result in gates.items():
        status = "PASSED" if gate_result["passed"] else "FAILED"
        print(f"  [{status}] {gate_name}: {gate_result['message']}")
    print("=" * 60)
    print(f"  Overall: {'ALL PASSED' if all_passed else 'SOME FAILED'}")
    print(f"  Recommendation: {validation_results['recommendation'].upper()}")
    print("=" * 60)

    return validation_results


def decide_deployment(**context) -> str:
    """
    Branch based on quality gate results.
    """
    ti = context["ti"]
    validation_results = ti.xcom_pull(key="validation_results")

    if validation_results.get("auto_deploy_eligible", False):
        return "approve_deployment"
    elif validation_results.get("critical_gates_passed", False):
        return "request_manual_review"
    else:
        return "reject_deployment"


def approve_deployment(**context) -> dict:
    """
    Mark model for deployment approval.
    """
    ti = context["ti"]
    challenger = ti.xcom_pull(key="challenger_metrics")
    validation_results = ti.xcom_pull(key="validation_results")

    result = {
        "status": "approved",
        "model_name": challenger["model_name"],
        "model_version": challenger["model_version"],
        "mlflow_run_id": challenger["mlflow_run_id"],
        "validation_results": validation_results,
        "approved_at": datetime.utcnow().isoformat(),
        "approved_by": "automated_quality_gates",
    }

    ti.xcom_push(key="deployment_decision", value=result)

    print(f"Deployment APPROVED: {result}")

    return result


def request_manual_review(**context) -> dict:
    """
    Request manual review for borderline cases.
    """
    ti = context["ti"]
    challenger = ti.xcom_pull(key="challenger_metrics")
    validation_results = ti.xcom_pull(key="validation_results")

    result = {
        "status": "pending_review",
        "model_name": challenger["model_name"],
        "model_version": challenger["model_version"],
        "validation_results": validation_results,
        "review_requested_at": datetime.utcnow().isoformat(),
        "review_reason": "Some non-critical quality gates failed",
    }

    ti.xcom_push(key="deployment_decision", value=result)

    # In production, this would create a ticket or send notification
    print(f"Manual Review REQUESTED: {result}")

    return result


def reject_deployment(**context) -> dict:
    """
    Reject model deployment due to quality gate failures.
    """
    ti = context["ti"]
    challenger = ti.xcom_pull(key="challenger_metrics")
    validation_results = ti.xcom_pull(key="validation_results")

    result = {
        "status": "rejected",
        "model_name": challenger["model_name"],
        "model_version": challenger["model_version"],
        "validation_results": validation_results,
        "rejected_at": datetime.utcnow().isoformat(),
        "rejection_reason": "Critical quality gates failed",
    }

    ti.xcom_push(key="deployment_decision", value=result)

    print(f"Deployment REJECTED: {result}")

    return result


with DAG(
    dag_id="validation_pipeline",
    default_args=default_args,
    description="Model validation with quality gates and champion/challenger comparison",
    schedule_interval=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["mlops", "validation", "quality-gates"],
    params={
        "auto_deploy": True,
    },
) as dag:

    start = EmptyOperator(task_id="start")

    # Load model metrics
    with TaskGroup("load_metrics", tooltip="Load model metrics") as load_metrics_group:
        load_challenger = PythonOperator(
            task_id="load_challenger_metrics",
            python_callable=load_challenger_metrics,
            provide_context=True,
        )

        load_champion = PythonOperator(
            task_id="load_champion_metrics",
            python_callable=load_champion_metrics,
            provide_context=True,
        )

    # Run validation tests
    with TaskGroup("run_validations", tooltip="Run validation tests") as validation_group:
        compare_models = PythonOperator(
            task_id="compare_champion_challenger",
            python_callable=compare_champion_challenger,
            provide_context=True,
        )

        test_latency = PythonOperator(
            task_id="run_latency_tests",
            python_callable=run_latency_tests,
            provide_context=True,
        )

        check_ge = PythonOperator(
            task_id="check_data_quality",
            python_callable=check_data_quality_results,
            provide_context=True,
        )

        check_drift = PythonOperator(
            task_id="check_drift",
            python_callable=check_drift_results,
            provide_context=True,
        )

    # Quality gate evaluation
    evaluate_gates = PythonOperator(
        task_id="evaluate_quality_gates",
        python_callable=evaluate_quality_gates,
        provide_context=True,
    )

    # Deployment decision branching
    decide = BranchPythonOperator(
        task_id="decide_deployment",
        python_callable=decide_deployment,
        provide_context=True,
    )

    # Decision outcomes
    approve = PythonOperator(
        task_id="approve_deployment",
        python_callable=approve_deployment,
        provide_context=True,
    )

    review = PythonOperator(
        task_id="request_manual_review",
        python_callable=request_manual_review,
        provide_context=True,
    )

    reject = PythonOperator(
        task_id="reject_deployment",
        python_callable=reject_deployment,
        provide_context=True,
    )

    end = EmptyOperator(task_id="end")

    # Define dependencies
    start >> load_metrics_group >> validation_group >> evaluate_gates >> decide
    decide >> [approve, review, reject] >> end
