"""
Deployment Pipeline DAG - Blue-green Kubernetes deployment.

This DAG handles:
1. Model artifact preparation
2. Helm chart deployment to Kubernetes
3. Blue-green deployment strategy
4. Health checks and rollback
5. Traffic shifting
"""

from datetime import datetime, timedelta
from typing import Any

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import BranchPythonOperator, PythonOperator
from airflow.utils.task_group import TaskGroup
from airflow.utils.trigger_rule import TriggerRule

default_args = {
    "owner": "mlops",
    "depends_on_past": False,
    "email_on_failure": True,
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
    "execution_timeout": timedelta(hours=1),
}

# Deployment configuration
DEPLOYMENT_CONFIG = {
    "namespace": "sales-forecasting",
    "chart_name": "sales-forecasting",
    "chart_path": "mlops/infrastructure/helm/charts/sales-forecasting",
    "registry": "ghcr.io/company/sales-forecasting",
    "health_check_retries": 10,
    "health_check_interval": 30,
    "traffic_shift_steps": [10, 25, 50, 75, 100],
    "rollback_threshold_error_rate": 0.05,
}


def prepare_deployment_artifacts(**context) -> dict:
    """
    Prepare model artifacts for deployment.
    """
    ti = context["ti"]
    dag_run = context.get("dag_run")
    conf = dag_run.conf if dag_run else {}

    # In production, this would:
    # 1. Download model from MLflow
    # 2. Package into Docker image
    # 3. Push to container registry

    deployment_artifacts = {
        "model_uri": "models:/sales-forecast-ensemble/Staging",
        "image_tag": f"v1.0.0-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        "image_full": f"{DEPLOYMENT_CONFIG['registry']}:latest",
        "artifacts_prepared": True,
        "prepared_at": datetime.utcnow().isoformat(),
    }

    ti.xcom_push(key="deployment_artifacts", value=deployment_artifacts)

    print(f"Deployment artifacts prepared: {deployment_artifacts}")

    return deployment_artifacts


def deploy_green_environment(**context) -> dict:
    """
    Deploy new model version to green environment (inactive).
    """
    ti = context["ti"]
    dag_run = context.get("dag_run")
    conf = dag_run.conf if dag_run else {}

    artifacts = ti.xcom_pull(key="deployment_artifacts")

    # In production, this would run Helm upgrade
    # helm upgrade --install sales-forecasting-green ./chart \
    #   --namespace sales-forecasting \
    #   --set image.tag={artifacts['image_tag']} \
    #   --set deployment.slot=green

    deployment_result = {
        "environment": "green",
        "release_name": "sales-forecasting-green",
        "namespace": DEPLOYMENT_CONFIG["namespace"],
        "image_tag": artifacts["image_tag"],
        "helm_status": "deployed",
        "replicas": {
            "desired": 3,
            "ready": 3,
            "available": 3,
        },
        "deployed_at": datetime.utcnow().isoformat(),
    }

    ti.xcom_push(key="green_deployment", value=deployment_result)

    print(f"Green environment deployed: {deployment_result}")

    return deployment_result


def run_health_checks(**context) -> dict:
    """
    Run health checks on the green environment.
    """
    import time

    ti = context["ti"]
    green_deployment = ti.xcom_pull(key="green_deployment")

    # In production, this would call the actual health endpoints
    health_checks = {
        "readiness": True,
        "liveness": True,
        "model_loaded": True,
        "database_connected": True,
        "cache_connected": True,
    }

    # Simulate health check retries
    retries = 0
    all_healthy = all(health_checks.values())

    health_result = {
        "environment": green_deployment["environment"],
        "checks": health_checks,
        "all_healthy": all_healthy,
        "retries": retries,
        "checked_at": datetime.utcnow().isoformat(),
    }

    ti.xcom_push(key="health_check_result", value=health_result)

    if not all_healthy:
        raise ValueError(f"Health checks failed: {health_result}")

    print(f"Health checks passed: {health_result}")

    return health_result


def run_smoke_tests(**context) -> dict:
    """
    Run smoke tests on green environment.
    """
    ti = context["ti"]
    green_deployment = ti.xcom_pull(key="green_deployment")

    # In production, this would run actual smoke tests
    smoke_tests = {
        "api_health": {"passed": True, "latency_ms": 45},
        "predict_endpoint": {"passed": True, "latency_ms": 120},
        "model_info": {"passed": True, "latency_ms": 30},
        "metrics_endpoint": {"passed": True, "latency_ms": 25},
    }

    all_passed = all(test["passed"] for test in smoke_tests.values())

    smoke_result = {
        "environment": green_deployment["environment"],
        "tests": smoke_tests,
        "all_passed": all_passed,
        "total_tests": len(smoke_tests),
        "passed_tests": sum(1 for t in smoke_tests.values() if t["passed"]),
        "tested_at": datetime.utcnow().isoformat(),
    }

    ti.xcom_push(key="smoke_test_result", value=smoke_result)

    if not all_passed:
        raise ValueError(f"Smoke tests failed: {smoke_result}")

    print(f"Smoke tests passed: {smoke_result}")

    return smoke_result


def shift_traffic(**context) -> dict:
    """
    Gradually shift traffic from blue to green environment.
    """
    import time

    ti = context["ti"]
    dag_run = context.get("dag_run")
    conf = dag_run.conf if dag_run else {}

    deployment_strategy = conf.get("deployment_strategy", "blue_green")

    traffic_history = []

    if deployment_strategy == "blue_green":
        # Instant switch for blue-green
        traffic_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "green_percentage": 100,
            "blue_percentage": 0,
        })
    else:
        # Canary deployment with gradual shift
        for percentage in DEPLOYMENT_CONFIG["traffic_shift_steps"]:
            traffic_history.append({
                "timestamp": datetime.utcnow().isoformat(),
                "green_percentage": percentage,
                "blue_percentage": 100 - percentage,
            })
            # In production, would monitor error rates here
            time.sleep(1)  # Shortened for demo

    traffic_result = {
        "strategy": deployment_strategy,
        "final_state": {
            "green_percentage": 100,
            "blue_percentage": 0,
        },
        "traffic_history": traffic_history,
        "shifted_at": datetime.utcnow().isoformat(),
    }

    ti.xcom_push(key="traffic_shift_result", value=traffic_result)

    print(f"Traffic shifted: {traffic_result}")

    return traffic_result


def verify_deployment(**context) -> dict:
    """
    Verify deployment is working correctly after traffic shift.
    """
    ti = context["ti"]

    # In production, this would:
    # 1. Monitor error rates
    # 2. Check latency metrics
    # 3. Verify predictions are valid

    verification_result = {
        "error_rate": 0.001,
        "error_rate_threshold": DEPLOYMENT_CONFIG["rollback_threshold_error_rate"],
        "p50_latency_ms": 48,
        "p99_latency_ms": 180,
        "requests_served": 1000,
        "successful_requests": 999,
        "verification_passed": True,
        "verified_at": datetime.utcnow().isoformat(),
    }

    ti.xcom_push(key="verification_result", value=verification_result)

    print(f"Deployment verified: {verification_result}")

    return verification_result


def decide_rollback(**context) -> str:
    """
    Decide whether to proceed or rollback.
    """
    ti = context["ti"]
    verification_result = ti.xcom_pull(key="verification_result")

    if verification_result.get("verification_passed", False):
        return "finalize_deployment"
    else:
        return "rollback_deployment"


def finalize_deployment(**context) -> dict:
    """
    Finalize deployment and clean up blue environment.
    """
    ti = context["ti"]
    artifacts = ti.xcom_pull(key="deployment_artifacts")

    # In production, this would:
    # 1. Update MLflow model stage to Production
    # 2. Scale down/delete blue environment
    # 3. Update DNS/ingress to point to green

    finalization_result = {
        "status": "success",
        "active_environment": "green",
        "model_stage": "Production",
        "image_tag": artifacts["image_tag"],
        "blue_environment_status": "scaled_down",
        "finalized_at": datetime.utcnow().isoformat(),
    }

    ti.xcom_push(key="finalization_result", value=finalization_result)

    print(f"Deployment finalized: {finalization_result}")

    return finalization_result


def rollback_deployment(**context) -> dict:
    """
    Rollback to blue environment on failure.
    """
    ti = context["ti"]

    # In production, this would:
    # 1. Shift traffic back to blue
    # 2. Scale down green environment
    # 3. Alert on-call team

    rollback_result = {
        "status": "rolled_back",
        "active_environment": "blue",
        "green_environment_status": "scaled_down",
        "reason": "Verification failed",
        "rolled_back_at": datetime.utcnow().isoformat(),
    }

    ti.xcom_push(key="rollback_result", value=rollback_result)

    print(f"Deployment rolled back: {rollback_result}")

    return rollback_result


def update_model_registry(**context) -> dict:
    """
    Update MLflow Model Registry with deployment status.
    """
    ti = context["ti"]
    finalization_result = ti.xcom_pull(key="finalization_result")

    # In production, this would:
    # mlflow.tracking.MlflowClient().transition_model_version_stage(
    #     name="sales-forecast-ensemble",
    #     version=version,
    #     stage="Production"
    # )

    registry_update = {
        "model_name": "sales-forecast-ensemble",
        "new_stage": "Production" if finalization_result else "Archived",
        "previous_stage": "Staging",
        "updated_at": datetime.utcnow().isoformat(),
    }

    ti.xcom_push(key="registry_update", value=registry_update)

    print(f"Model registry updated: {registry_update}")

    return registry_update


def notify_deployment_status(**context) -> None:
    """
    Send deployment notifications.
    """
    ti = context["ti"]

    finalization_result = ti.xcom_pull(key="finalization_result")
    rollback_result = ti.xcom_pull(key="rollback_result")

    if finalization_result:
        status = "SUCCESS"
        message = f"Model deployed successfully to production. Image: {finalization_result['image_tag']}"
    elif rollback_result:
        status = "ROLLED_BACK"
        message = f"Deployment rolled back. Reason: {rollback_result['reason']}"
    else:
        status = "UNKNOWN"
        message = "Deployment status unknown"

    # In production, this would send to Slack/Teams/PagerDuty
    print(f"Deployment Notification [{status}]: {message}")


with DAG(
    dag_id="deployment_pipeline",
    default_args=default_args,
    description="Blue-green Kubernetes deployment with health checks and rollback",
    schedule_interval=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["mlops", "deployment", "kubernetes"],
    params={
        "deployment_strategy": "blue_green",  # blue_green or canary
    },
) as dag:

    start = EmptyOperator(task_id="start")

    # Prepare artifacts
    prepare = PythonOperator(
        task_id="prepare_deployment_artifacts",
        python_callable=prepare_deployment_artifacts,
        provide_context=True,
    )

    # Deploy to green environment
    with TaskGroup("deploy_green", tooltip="Deploy to green environment") as deploy_group:
        deploy = PythonOperator(
            task_id="deploy_green_environment",
            python_callable=deploy_green_environment,
            provide_context=True,
        )

        health = PythonOperator(
            task_id="run_health_checks",
            python_callable=run_health_checks,
            provide_context=True,
        )

        smoke = PythonOperator(
            task_id="run_smoke_tests",
            python_callable=run_smoke_tests,
            provide_context=True,
        )

        deploy >> health >> smoke

    # Traffic management
    with TaskGroup("traffic_management", tooltip="Traffic shifting and verification") as traffic_group:
        shift = PythonOperator(
            task_id="shift_traffic",
            python_callable=shift_traffic,
            provide_context=True,
        )

        verify = PythonOperator(
            task_id="verify_deployment",
            python_callable=verify_deployment,
            provide_context=True,
        )

        shift >> verify

    # Rollback decision
    decide = BranchPythonOperator(
        task_id="decide_rollback",
        python_callable=decide_rollback,
        provide_context=True,
    )

    # Finalization paths
    finalize = PythonOperator(
        task_id="finalize_deployment",
        python_callable=finalize_deployment,
        provide_context=True,
    )

    rollback = PythonOperator(
        task_id="rollback_deployment",
        python_callable=rollback_deployment,
        provide_context=True,
    )

    # Post-deployment
    update_registry = PythonOperator(
        task_id="update_model_registry",
        python_callable=update_model_registry,
        provide_context=True,
        trigger_rule=TriggerRule.ONE_SUCCESS,
    )

    notify = PythonOperator(
        task_id="notify_deployment_status",
        python_callable=notify_deployment_status,
        provide_context=True,
        trigger_rule=TriggerRule.ALL_DONE,
    )

    end = EmptyOperator(
        task_id="end",
        trigger_rule=TriggerRule.ALL_DONE,
    )

    # Define dependencies
    start >> prepare >> deploy_group >> traffic_group >> decide
    decide >> [finalize, rollback] >> update_registry >> notify >> end
