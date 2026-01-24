"""
Custom Airflow operators for MLflow operations.
"""

from typing import Any

from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults


class MLflowExperimentOperator(BaseOperator):
    """
    Operator to manage MLflow experiments.

    Handles:
    - Creating/getting experiments
    - Setting experiment tags
    - Managing experiment lifecycle
    """

    template_fields = ("experiment_name", "tags")

    @apply_defaults
    def __init__(
        self,
        experiment_name: str = "sales-forecasting",
        tags: dict[str, str] | None = None,
        artifact_location: str | None = None,
        mlflow_tracking_uri: str = "http://mlflow:5000",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.experiment_name = experiment_name
        self.tags = tags or {}
        self.artifact_location = artifact_location
        self.mlflow_tracking_uri = mlflow_tracking_uri

    def execute(self, context: dict) -> dict:
        """Create or get MLflow experiment."""
        from datetime import datetime

        self.log.info(f"Setting up MLflow experiment: {self.experiment_name}")

        # In production, this would use MLflow client
        # import mlflow
        # mlflow.set_tracking_uri(self.mlflow_tracking_uri)
        # experiment = mlflow.set_experiment(self.experiment_name)

        result = {
            "experiment_name": self.experiment_name,
            "experiment_id": "exp_123",
            "artifact_location": self.artifact_location or f"s3://mlflow-artifacts/{self.experiment_name}",
            "tags": self.tags,
            "tracking_uri": self.mlflow_tracking_uri,
            "created_at": datetime.now().isoformat(),
        }

        self.log.info(f"MLflow experiment ready: {result}")

        context["ti"].xcom_push(key="mlflow_experiment", value=result)

        return result


class MLflowModelRegistryOperator(BaseOperator):
    """
    Operator to register models in MLflow Model Registry.

    Handles:
    - Model registration
    - Version management
    - Stage transitions (Staging -> Production)
    - Model aliases and tags
    """

    template_fields = ("model_name", "run_id", "stage")

    @apply_defaults
    def __init__(
        self,
        model_name: str,
        run_id: str | None = None,
        model_uri: str | None = None,
        stage: str = "Staging",
        tags: dict[str, str] | None = None,
        description: str | None = None,
        archive_existing_versions: bool = False,
        mlflow_tracking_uri: str = "http://mlflow:5000",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.model_name = model_name
        self.run_id = run_id
        self.model_uri = model_uri
        self.stage = stage
        self.tags = tags or {}
        self.description = description
        self.archive_existing_versions = archive_existing_versions
        self.mlflow_tracking_uri = mlflow_tracking_uri

    def execute(self, context: dict) -> dict:
        """Register model in MLflow Model Registry."""
        from datetime import datetime

        ti = context["ti"]

        # Get run_id from upstream task if not provided
        if not self.run_id:
            training_result = ti.xcom_pull(key="training_result")
            if training_result:
                self.run_id = training_result.get("mlflow_run_id")

        self.log.info(
            f"Registering model: name={self.model_name}, run_id={self.run_id}, stage={self.stage}"
        )

        # In production, this would use MLflow client
        # import mlflow
        # from mlflow.tracking import MlflowClient
        #
        # client = MlflowClient(tracking_uri=self.mlflow_tracking_uri)
        #
        # model_uri = self.model_uri or f"runs:/{self.run_id}/model"
        # model_version = mlflow.register_model(model_uri, self.model_name)
        #
        # client.transition_model_version_stage(
        #     name=self.model_name,
        #     version=model_version.version,
        #     stage=self.stage,
        #     archive_existing_versions=self.archive_existing_versions
        # )

        result = {
            "model_name": self.model_name,
            "model_version": 1,
            "run_id": self.run_id,
            "model_uri": self.model_uri or f"runs:/{self.run_id}/model",
            "stage": self.stage,
            "tags": self.tags,
            "description": self.description,
            "registered_at": datetime.now().isoformat(),
        }

        self.log.info(f"Model registered: {result}")

        context["ti"].xcom_push(key="registered_model", value=result)

        return result


class MLflowModelTransitionOperator(BaseOperator):
    """
    Operator to transition model versions between stages.

    Handles stage transitions:
    - None -> Staging
    - Staging -> Production
    - Production -> Archived
    """

    template_fields = ("model_name", "version", "target_stage")

    @apply_defaults
    def __init__(
        self,
        model_name: str,
        version: int | None = None,
        source_stage: str | None = None,
        target_stage: str = "Production",
        archive_existing_versions: bool = True,
        mlflow_tracking_uri: str = "http://mlflow:5000",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.model_name = model_name
        self.version = version
        self.source_stage = source_stage
        self.target_stage = target_stage
        self.archive_existing_versions = archive_existing_versions
        self.mlflow_tracking_uri = mlflow_tracking_uri

    def execute(self, context: dict) -> dict:
        """Transition model version to new stage."""
        from datetime import datetime

        ti = context["ti"]

        # Get version from registered model if not provided
        if self.version is None:
            registered = ti.xcom_pull(key="registered_model")
            if registered:
                self.version = registered.get("model_version")

        self.log.info(
            f"Transitioning model: name={self.model_name}, "
            f"version={self.version}, target_stage={self.target_stage}"
        )

        # In production:
        # from mlflow.tracking import MlflowClient
        # client = MlflowClient(tracking_uri=self.mlflow_tracking_uri)
        # client.transition_model_version_stage(
        #     name=self.model_name,
        #     version=self.version,
        #     stage=self.target_stage,
        #     archive_existing_versions=self.archive_existing_versions
        # )

        result = {
            "model_name": self.model_name,
            "version": self.version,
            "source_stage": self.source_stage or "Staging",
            "target_stage": self.target_stage,
            "archive_existing": self.archive_existing_versions,
            "transitioned_at": datetime.now().isoformat(),
        }

        self.log.info(f"Model transitioned: {result}")

        context["ti"].xcom_push(key="model_transition", value=result)

        return result


class MLflowCompareModelsOperator(BaseOperator):
    """
    Operator to compare model versions.

    Compares:
    - Challenger (new model) vs Champion (current production)
    - Multiple model types
    - Metrics comparison
    """

    template_fields = ("model_name", "challenger_version", "champion_stage")

    @apply_defaults
    def __init__(
        self,
        model_name: str,
        challenger_version: int | None = None,
        champion_stage: str = "Production",
        comparison_metrics: list[str] | None = None,
        mlflow_tracking_uri: str = "http://mlflow:5000",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.model_name = model_name
        self.challenger_version = challenger_version
        self.champion_stage = champion_stage
        self.comparison_metrics = comparison_metrics or ["test_mape", "test_rmse", "r2_score"]
        self.mlflow_tracking_uri = mlflow_tracking_uri

    def execute(self, context: dict) -> dict:
        """Compare challenger model against champion."""
        from datetime import datetime

        ti = context["ti"]

        self.log.info(
            f"Comparing models: name={self.model_name}, "
            f"challenger_version={self.challenger_version}"
        )

        # In production, this would query MLflow for model metrics
        # from mlflow.tracking import MlflowClient
        # client = MlflowClient(tracking_uri=self.mlflow_tracking_uri)
        #
        # champion_versions = client.get_latest_versions(self.model_name, stages=[self.champion_stage])
        # challenger_run = client.get_run(client.get_model_version(self.model_name, self.challenger_version).run_id)
        # champion_run = client.get_run(champion_versions[0].run_id)

        # Mock comparison
        comparison_result = {
            "model_name": self.model_name,
            "challenger": {
                "version": self.challenger_version or 2,
                "metrics": {
                    "test_mape": 0.038,
                    "test_rmse": 1180.2,
                    "r2_score": 0.94,
                },
            },
            "champion": {
                "version": 1,
                "stage": self.champion_stage,
                "metrics": {
                    "test_mape": 0.051,
                    "test_rmse": 1420.3,
                    "r2_score": 0.91,
                },
            },
            "comparison": {
                metric: {
                    "challenger": 0.038 if metric == "test_mape" else (1180.2 if metric == "test_rmse" else 0.94),
                    "champion": 0.051 if metric == "test_mape" else (1420.3 if metric == "test_rmse" else 0.91),
                    "improvement": 25.5 if metric == "test_mape" else (16.9 if metric == "test_rmse" else 3.3),
                    "challenger_better": True,
                }
                for metric in self.comparison_metrics
            },
            "overall_challenger_better": True,
            "compared_at": datetime.now().isoformat(),
        }

        self.log.info(f"Model comparison: {comparison_result}")

        context["ti"].xcom_push(key="model_comparison", value=comparison_result)

        return comparison_result
