"""
Master ML Pipeline DAG - Single trigger orchestration for end-to-end ML workflow.

This DAG orchestrates the complete ML pipeline:
1. Data Pipeline - Ingestion, validation, feature engineering
2. Training Pipeline - Model training with hyperparameter tuning
3. Validation Pipeline - Quality gates and champion/challenger comparison
4. Deployment Pipeline - Blue-green deployment to Kubernetes
5. Monitoring Pipeline - Alert and dashboard setup

Triggers:
- API: POST /api/v1/mlops/pipeline/trigger
- GitHub Webhook: PR merge to main
- Scheduled: Drift detection alerts
"""

from datetime import datetime, timedelta
from typing import Any

from airflow import DAG
from airflow.models import Variable
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import BranchPythonOperator, PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.sensors.external_task import ExternalTaskSensor
from airflow.utils.task_group import TaskGroup
from airflow.utils.trigger_rule import TriggerRule

# Default arguments for all tasks
default_args = {
    "owner": "mlops",
    "depends_on_past": False,
    "email": ["mlops-alerts@company.com"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(hours=2),
}


def determine_pipeline_type(**context) -> str:
    """
    Determine which pipeline stages to execute based on trigger configuration.

    Returns the appropriate branch based on pipeline_type:
    - full: Execute all stages
    - training: Skip data pipeline, use existing features
    - deploy: Skip data and training, deploy specific model
    - retrain: Full pipeline triggered by drift detection
    """
    dag_run = context.get("dag_run")
    conf = dag_run.conf if dag_run else {}

    pipeline_type = conf.get("pipeline_type", "full")
    trigger_source = conf.get("trigger_source", "manual")

    # Log trigger information
    print(f"Pipeline triggered: type={pipeline_type}, source={trigger_source}")

    if pipeline_type == "deploy":
        return "skip_to_deployment"
    elif pipeline_type == "training":
        return "skip_to_training"
    else:  # full or retrain
        return "trigger_data_pipeline"


def check_quality_gates(**context) -> str:
    """
    Check if quality gates pass for auto-deployment.

    Quality Gate Rules:
    - MAPE improvement >= 2% over champion
    - No data drift detected (KS-test p-value > 0.05)
    - Inference latency < 500ms (p99)
    - All Great Expectations checks pass
    """
    ti = context["ti"]

    # Pull validation results from XCom
    validation_results = ti.xcom_pull(
        task_ids="validation_pipeline.quality_gate_check",
        key="validation_results",
    )

    if validation_results is None:
        print("No validation results found, defaulting to manual review")
        return "manual_review_required"

    # Check all quality gates
    mape_improvement = validation_results.get("mape_improvement", 0)
    drift_detected = validation_results.get("drift_detected", True)
    p99_latency = validation_results.get("p99_latency_ms", 1000)
    ge_checks_passed = validation_results.get("ge_checks_passed", False)

    all_gates_pass = (
        mape_improvement >= 2.0 and
        not drift_detected and
        p99_latency < 500 and
        ge_checks_passed
    )

    if all_gates_pass:
        print("All quality gates passed - auto-deploying")
        return "trigger_deployment_pipeline"
    else:
        print(f"Quality gates failed: MAPE={mape_improvement}%, drift={drift_detected}, "
              f"latency={p99_latency}ms, GE={ge_checks_passed}")
        return "manual_review_required"


def notify_pipeline_complete(**context) -> None:
    """Send notification on pipeline completion."""
    dag_run = context.get("dag_run")
    conf = dag_run.conf if dag_run else {}

    pipeline_type = conf.get("pipeline_type", "full")
    model_types = conf.get("model_types", ["prophet"])

    # In production, this would send to Slack/Teams/email
    print(f"ML Pipeline completed successfully!")
    print(f"  Type: {pipeline_type}")
    print(f"  Models: {model_types}")
    print(f"  Run ID: {dag_run.run_id if dag_run else 'N/A'}")


def manual_review_callback(**context) -> None:
    """Handle manual review requirement."""
    ti = context["ti"]

    validation_results = ti.xcom_pull(
        task_ids="validation_pipeline.quality_gate_check",
        key="validation_results",
    )

    print("Manual review required for model deployment")
    print("Review the validation results in MLflow and approve deployment manually")
    print(f"Validation results: {validation_results}")

    # In production, this would create a ticket or send notification
    # requiring human approval before proceeding


with DAG(
    dag_id="ml_pipeline_master",
    default_args=default_args,
    description="Master ML pipeline orchestrating end-to-end model lifecycle",
    schedule_interval=None,  # Triggered externally
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["mlops", "master", "production"],
    params={
        "pipeline_type": "full",  # full, training, deploy, retrain
        "model_types": ["prophet", "arima", "pymc_mmm"],
        "dataset_id": None,
        "auto_deploy": True,
        "trigger_source": "manual",
    },
) as dag:

    # Start marker
    start = EmptyOperator(task_id="start")

    # Determine which pipeline path to take
    determine_path = BranchPythonOperator(
        task_id="determine_pipeline_path",
        python_callable=determine_pipeline_type,
        provide_context=True,
    )

    # Data Pipeline Stage
    with TaskGroup("data_pipeline", tooltip="Data ingestion and validation") as data_pipeline:
        trigger_data = TriggerDagRunOperator(
            task_id="trigger_data_pipeline",
            trigger_dag_id="data_pipeline",
            wait_for_completion=True,
            poke_interval=30,
            conf={
                "parent_run_id": "{{ run_id }}",
                "dataset_id": "{{ dag_run.conf.get('dataset_id') }}",
            },
        )

        wait_data = ExternalTaskSensor(
            task_id="wait_for_data_pipeline",
            external_dag_id="data_pipeline",
            external_task_id="end",
            mode="reschedule",
            timeout=3600,
            poke_interval=60,
        )

        trigger_data >> wait_data

    # Skip to training (when data already processed)
    skip_to_training = EmptyOperator(
        task_id="skip_to_training",
    )

    # Skip to deployment (when deploying existing model)
    skip_to_deployment = EmptyOperator(
        task_id="skip_to_deployment",
    )

    # Training Pipeline Stage
    with TaskGroup("training_pipeline", tooltip="Model training and experiment tracking") as training_pipeline:
        trigger_training = TriggerDagRunOperator(
            task_id="trigger_training",
            trigger_dag_id="training_pipeline",
            wait_for_completion=True,
            poke_interval=30,
            conf={
                "parent_run_id": "{{ run_id }}",
                "model_types": "{{ dag_run.conf.get('model_types', ['prophet']) }}",
            },
        )

        wait_training = ExternalTaskSensor(
            task_id="wait_for_training",
            external_dag_id="training_pipeline",
            external_task_id="end",
            mode="reschedule",
            timeout=7200,
            poke_interval=60,
        )

        trigger_training >> wait_training

    # Validation Pipeline Stage
    with TaskGroup("validation_pipeline", tooltip="Quality gates and model comparison") as validation_pipeline:
        trigger_validation = TriggerDagRunOperator(
            task_id="trigger_validation",
            trigger_dag_id="validation_pipeline",
            wait_for_completion=True,
            poke_interval=30,
            conf={
                "parent_run_id": "{{ run_id }}",
                "auto_deploy": "{{ dag_run.conf.get('auto_deploy', True) }}",
            },
        )

        quality_gate = PythonOperator(
            task_id="quality_gate_check",
            python_callable=check_quality_gates,
            provide_context=True,
        )

        trigger_validation >> quality_gate

    # Quality gate branching
    quality_gate_branch = BranchPythonOperator(
        task_id="quality_gate_decision",
        python_callable=check_quality_gates,
        provide_context=True,
    )

    # Manual review path
    manual_review = PythonOperator(
        task_id="manual_review_required",
        python_callable=manual_review_callback,
        provide_context=True,
    )

    # Deployment Pipeline Stage
    with TaskGroup("deployment_pipeline", tooltip="Blue-green K8s deployment") as deployment_pipeline:
        trigger_deployment = TriggerDagRunOperator(
            task_id="trigger_deployment_pipeline",
            trigger_dag_id="deployment_pipeline",
            wait_for_completion=True,
            poke_interval=30,
            conf={
                "parent_run_id": "{{ run_id }}",
                "deployment_strategy": "blue_green",
            },
        )

        wait_deployment = ExternalTaskSensor(
            task_id="wait_for_deployment",
            external_dag_id="deployment_pipeline",
            external_task_id="end",
            mode="reschedule",
            timeout=1800,
            poke_interval=30,
        )

        trigger_deployment >> wait_deployment

    # Monitoring Pipeline Stage
    with TaskGroup("monitoring_pipeline", tooltip="Alerts and dashboards setup") as monitoring_pipeline:
        trigger_monitoring = TriggerDagRunOperator(
            task_id="trigger_monitoring",
            trigger_dag_id="monitoring_pipeline",
            wait_for_completion=True,
            poke_interval=30,
            conf={
                "parent_run_id": "{{ run_id }}",
            },
        )

    # Join paths before validation
    join_before_validation = EmptyOperator(
        task_id="join_before_validation",
        trigger_rule=TriggerRule.ONE_SUCCESS,
    )

    # Join paths for deployment
    join_for_deployment = EmptyOperator(
        task_id="join_for_deployment",
        trigger_rule=TriggerRule.ONE_SUCCESS,
    )

    # End marker
    notify_complete = PythonOperator(
        task_id="notify_pipeline_complete",
        python_callable=notify_pipeline_complete,
        provide_context=True,
        trigger_rule=TriggerRule.ONE_SUCCESS,
    )

    end = EmptyOperator(
        task_id="end",
        trigger_rule=TriggerRule.ONE_SUCCESS,
    )

    # Define task dependencies
    start >> determine_path

    # Full pipeline path
    determine_path >> data_pipeline >> join_before_validation

    # Training only path
    determine_path >> skip_to_training >> join_before_validation

    # Deploy only path
    determine_path >> skip_to_deployment >> join_for_deployment

    # Validation and quality gates
    join_before_validation >> training_pipeline >> validation_pipeline >> quality_gate_branch

    # Quality gate outcomes
    quality_gate_branch >> deployment_pipeline >> join_for_deployment
    quality_gate_branch >> manual_review >> join_for_deployment

    # Final stages
    join_for_deployment >> monitoring_pipeline >> notify_complete >> end
