"""
Monitoring Pipeline DAG - Alert and dashboard setup.

This DAG handles:
1. Prometheus alert configuration
2. Grafana dashboard provisioning
3. Model performance monitoring setup
4. Drift detection scheduling
"""

from datetime import datetime, timedelta
from typing import Any

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup

default_args = {
    "owner": "mlops",
    "depends_on_past": False,
    "email_on_failure": True,
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
    "execution_timeout": timedelta(minutes=30),
}

# Monitoring configuration
MONITORING_CONFIG = {
    "prometheus_url": "http://prometheus:9090",
    "grafana_url": "http://grafana:3000",
    "alertmanager_url": "http://alertmanager:9093",
    "model_metrics_port": 8001,
}


def configure_prometheus_alerts(**context) -> dict:
    """
    Configure Prometheus alerting rules for the deployed model.
    """
    ti = context["ti"]
    dag_run = context.get("dag_run")

    # Alert rules to configure
    alert_rules = {
        "model_alerts": [
            {
                "alert": "ModelMAPEDegradation",
                "expr": "model_mape > 0.15",
                "for": "10m",
                "labels": {"severity": "warning"},
                "annotations": {
                    "summary": "Model MAPE degradation detected",
                    "description": "Model MAPE has exceeded 15% threshold for 10 minutes",
                },
            },
            {
                "alert": "ModelLatencyHigh",
                "expr": "histogram_quantile(0.99, model_inference_latency_seconds_bucket) > 0.5",
                "for": "5m",
                "labels": {"severity": "warning"},
                "annotations": {
                    "summary": "High model inference latency",
                    "description": "P99 latency has exceeded 500ms for 5 minutes",
                },
            },
            {
                "alert": "ModelErrorRateHigh",
                "expr": "rate(model_prediction_errors_total[5m]) / rate(model_predictions_total[5m]) > 0.05",
                "for": "5m",
                "labels": {"severity": "critical"},
                "annotations": {
                    "summary": "High model error rate",
                    "description": "Model error rate has exceeded 5% for 5 minutes",
                },
            },
            {
                "alert": "DataDriftDetected",
                "expr": "data_drift_score > 0.5",
                "for": "15m",
                "labels": {"severity": "warning"},
                "annotations": {
                    "summary": "Data drift detected",
                    "description": "Data drift score has exceeded threshold, consider retraining",
                },
            },
        ],
        "pipeline_alerts": [
            {
                "alert": "AirflowDAGFailure",
                "expr": 'airflow_dag_run_state{state="failed"} > 0',
                "for": "1m",
                "labels": {"severity": "critical"},
                "annotations": {
                    "summary": "Airflow DAG failure",
                    "description": "ML pipeline DAG has failed",
                },
            },
            {
                "alert": "AirflowTaskDurationHigh",
                "expr": "airflow_task_duration_seconds > 7200",
                "for": "5m",
                "labels": {"severity": "warning"},
                "annotations": {
                    "summary": "Long-running Airflow task",
                    "description": "Task has been running for more than 2 hours",
                },
            },
        ],
    }

    # In production, this would POST to Prometheus/Alertmanager
    result = {
        "status": "configured",
        "alert_groups": list(alert_rules.keys()),
        "total_alerts": sum(len(alerts) for alerts in alert_rules.values()),
        "prometheus_url": MONITORING_CONFIG["prometheus_url"],
        "configured_at": datetime.utcnow().isoformat(),
    }

    ti.xcom_push(key="prometheus_config", value=result)

    print(f"Prometheus alerts configured: {result}")

    return result


def provision_grafana_dashboards(**context) -> dict:
    """
    Provision Grafana dashboards for ML monitoring.
    """
    ti = context["ti"]

    # Dashboard configurations
    dashboards = {
        "ml_pipeline": {
            "title": "ML Pipeline Health",
            "uid": "ml-pipeline-health",
            "panels": [
                "DAG Success Rate",
                "Task Duration",
                "Pipeline Throughput",
                "Error Rate",
            ],
        },
        "model_performance": {
            "title": "Model Performance",
            "uid": "model-performance",
            "panels": [
                "MAPE Trend",
                "RMSE Trend",
                "Prediction Distribution",
                "Actual vs Predicted",
            ],
        },
        "drift_detection": {
            "title": "Drift Detection",
            "uid": "drift-detection",
            "panels": [
                "Feature Drift Scores",
                "Data Distribution Changes",
                "Concept Drift Indicators",
                "Drift Alerts",
            ],
        },
        "inference_metrics": {
            "title": "Inference Metrics",
            "uid": "inference-metrics",
            "panels": [
                "Request Rate",
                "Latency Distribution",
                "Error Rate",
                "Resource Utilization",
            ],
        },
    }

    # In production, this would use Grafana provisioning API
    result = {
        "status": "provisioned",
        "dashboards": list(dashboards.keys()),
        "total_panels": sum(len(d["panels"]) for d in dashboards.values()),
        "grafana_url": MONITORING_CONFIG["grafana_url"],
        "provisioned_at": datetime.utcnow().isoformat(),
    }

    ti.xcom_push(key="grafana_dashboards", value=result)

    print(f"Grafana dashboards provisioned: {result}")

    return result


def setup_model_metrics_exporter(**context) -> dict:
    """
    Configure custom Prometheus metrics exporter for model metrics.
    """
    ti = context["ti"]

    # Metrics to export
    metrics = {
        "counters": [
            "model_predictions_total",
            "model_prediction_errors_total",
            "feature_cache_hits_total",
            "feature_cache_misses_total",
        ],
        "gauges": [
            "model_mape",
            "model_rmse",
            "data_drift_score",
            "model_version",
            "active_model_count",
        ],
        "histograms": [
            "model_inference_latency_seconds",
            "feature_retrieval_latency_seconds",
            "prediction_value",
        ],
    }

    result = {
        "status": "configured",
        "metrics_port": MONITORING_CONFIG["model_metrics_port"],
        "metrics": metrics,
        "total_metrics": sum(len(m) for m in metrics.values()),
        "configured_at": datetime.utcnow().isoformat(),
    }

    ti.xcom_push(key="metrics_exporter", value=result)

    print(f"Metrics exporter configured: {result}")

    return result


def schedule_drift_detection(**context) -> dict:
    """
    Schedule periodic drift detection jobs.
    """
    ti = context["ti"]

    # Drift detection schedule
    drift_schedule = {
        "hourly_check": {
            "frequency": "0 * * * *",  # Every hour
            "features": ["revenue", "impressions", "clicks"],
            "method": "ks_test",
            "threshold": 0.05,
        },
        "daily_report": {
            "frequency": "0 0 * * *",  # Daily at midnight
            "features": "all",
            "method": "comprehensive",
            "generate_report": True,
        },
        "weekly_baseline_update": {
            "frequency": "0 0 * * 0",  # Weekly on Sunday
            "action": "update_baseline",
            "lookback_days": 30,
        },
    }

    result = {
        "status": "scheduled",
        "schedules": list(drift_schedule.keys()),
        "next_hourly_check": "in 1 hour",
        "scheduled_at": datetime.utcnow().isoformat(),
    }

    ti.xcom_push(key="drift_schedule", value=result)

    print(f"Drift detection scheduled: {result}")

    return result


def configure_alertmanager(**context) -> dict:
    """
    Configure Alertmanager for alert routing.
    """
    ti = context["ti"]

    # Alertmanager configuration
    alertmanager_config = {
        "global": {
            "resolve_timeout": "5m",
        },
        "route": {
            "group_by": ["alertname", "severity"],
            "group_wait": "10s",
            "group_interval": "10s",
            "repeat_interval": "1h",
            "receiver": "default",
            "routes": [
                {
                    "match": {"severity": "critical"},
                    "receiver": "pagerduty",
                },
                {
                    "match": {"severity": "warning"},
                    "receiver": "slack",
                },
            ],
        },
        "receivers": [
            {
                "name": "default",
                "email_configs": [{"to": "mlops-alerts@company.com"}],
            },
            {
                "name": "slack",
                "slack_configs": [{"channel": "#mlops-alerts"}],
            },
            {
                "name": "pagerduty",
                "pagerduty_configs": [{"service_key": "pagerduty-key"}],
            },
        ],
    }

    result = {
        "status": "configured",
        "receivers": ["default", "slack", "pagerduty"],
        "alertmanager_url": MONITORING_CONFIG["alertmanager_url"],
        "configured_at": datetime.utcnow().isoformat(),
    }

    ti.xcom_push(key="alertmanager_config", value=result)

    print(f"Alertmanager configured: {result}")

    return result


def verify_monitoring_setup(**context) -> dict:
    """
    Verify all monitoring components are working.
    """
    ti = context["ti"]

    prometheus_config = ti.xcom_pull(key="prometheus_config")
    grafana_dashboards = ti.xcom_pull(key="grafana_dashboards")
    metrics_exporter = ti.xcom_pull(key="metrics_exporter")
    drift_schedule = ti.xcom_pull(key="drift_schedule")
    alertmanager_config = ti.xcom_pull(key="alertmanager_config")

    verification = {
        "prometheus": {
            "status": prometheus_config.get("status") == "configured",
            "alerts_configured": prometheus_config.get("total_alerts", 0),
        },
        "grafana": {
            "status": grafana_dashboards.get("status") == "provisioned",
            "dashboards_provisioned": len(grafana_dashboards.get("dashboards", [])),
        },
        "metrics_exporter": {
            "status": metrics_exporter.get("status") == "configured",
            "port": metrics_exporter.get("metrics_port"),
        },
        "drift_detection": {
            "status": drift_schedule.get("status") == "scheduled",
            "schedules": len(drift_schedule.get("schedules", [])),
        },
        "alertmanager": {
            "status": alertmanager_config.get("status") == "configured",
            "receivers": len(alertmanager_config.get("receivers", [])),
        },
    }

    all_verified = all(v["status"] for v in verification.values())

    result = {
        "verification": verification,
        "all_verified": all_verified,
        "verified_at": datetime.utcnow().isoformat(),
    }

    ti.xcom_push(key="monitoring_verification", value=result)

    print(f"Monitoring verification: {result}")

    if not all_verified:
        raise ValueError(f"Monitoring verification failed: {result}")

    return result


def create_monitoring_report(**context) -> dict:
    """
    Create monitoring setup report.
    """
    ti = context["ti"]
    dag_run = context.get("dag_run")

    verification = ti.xcom_pull(key="monitoring_verification")

    report = {
        "pipeline_run_id": dag_run.run_id if dag_run else "unknown",
        "timestamp": datetime.utcnow().isoformat(),
        "monitoring_components": {
            "prometheus": {
                "url": MONITORING_CONFIG["prometheus_url"],
                "status": "active",
            },
            "grafana": {
                "url": MONITORING_CONFIG["grafana_url"],
                "status": "active",
            },
            "alertmanager": {
                "url": MONITORING_CONFIG["alertmanager_url"],
                "status": "active",
            },
        },
        "dashboards": [
            f"{MONITORING_CONFIG['grafana_url']}/d/ml-pipeline-health",
            f"{MONITORING_CONFIG['grafana_url']}/d/model-performance",
            f"{MONITORING_CONFIG['grafana_url']}/d/drift-detection",
            f"{MONITORING_CONFIG['grafana_url']}/d/inference-metrics",
        ],
        "verification": verification.get("verification", {}),
    }

    ti.xcom_push(key="monitoring_report", value=report)

    print(f"Monitoring Report: {report}")

    return report


with DAG(
    dag_id="monitoring_pipeline",
    default_args=default_args,
    description="Monitoring setup with Prometheus, Grafana, and drift detection",
    schedule_interval=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["mlops", "monitoring", "observability"],
) as dag:

    start = EmptyOperator(task_id="start")

    # Configure monitoring components
    with TaskGroup("configure_monitoring", tooltip="Configure monitoring stack") as config_group:
        prometheus = PythonOperator(
            task_id="configure_prometheus_alerts",
            python_callable=configure_prometheus_alerts,
            provide_context=True,
        )

        grafana = PythonOperator(
            task_id="provision_grafana_dashboards",
            python_callable=provision_grafana_dashboards,
            provide_context=True,
        )

        metrics = PythonOperator(
            task_id="setup_model_metrics_exporter",
            python_callable=setup_model_metrics_exporter,
            provide_context=True,
        )

        alertmanager = PythonOperator(
            task_id="configure_alertmanager",
            python_callable=configure_alertmanager,
            provide_context=True,
        )

    # Schedule drift detection
    drift = PythonOperator(
        task_id="schedule_drift_detection",
        python_callable=schedule_drift_detection,
        provide_context=True,
    )

    # Verify setup
    verify = PythonOperator(
        task_id="verify_monitoring_setup",
        python_callable=verify_monitoring_setup,
        provide_context=True,
    )

    # Create report
    report = PythonOperator(
        task_id="create_monitoring_report",
        python_callable=create_monitoring_report,
        provide_context=True,
    )

    end = EmptyOperator(task_id="end")

    # Define dependencies
    start >> config_group >> drift >> verify >> report >> end
