"""Forecast generation tasks."""

from typing import Any, Dict, Optional
import pandas as pd
import structlog

from app.workers.celery_app import celery_app
from app.infrastructure.database.session import get_sync_session
from app.infrastructure.database.models.forecast import Forecast
from app.infrastructure.database.models.dataset import Dataset
from app.services.forecast.forecast_service import (
    ForecastService,
    ForecastConfig,
    ModelType,
)

logger = structlog.get_logger()


@celery_app.task(bind=True, name="generate_forecast")
def generate_forecast(
    self,
    forecast_id: str,
) -> Dict[str, Any]:
    """Generate a forecast using the configured model.

    Args:
        forecast_id: UUID of the forecast to generate.

    Returns:
        Dictionary with generation results.
    """
    logger.info(
        "Starting forecast generation task",
        forecast_id=forecast_id,
        task_id=self.request.id,
    )

    try:
        self.update_state(state="PROGRESS", meta={"status": "loading_forecast"})

        # Load forecast record from DB
        with get_sync_session() as db:
            forecast = db.query(Forecast).filter(
                Forecast.id == forecast_id
            ).first()

            if not forecast:
                logger.error("Forecast not found", forecast_id=forecast_id)
                return {
                    "status": "failed",
                    "forecast_id": forecast_id,
                    "error": "Forecast not found",
                }

            # Update status to running
            forecast.status = "running"
            db.commit()

            self.update_state(state="PROGRESS", meta={"status": "loading_data"})

            # Load dataset
            dataset = db.query(Dataset).filter(
                Dataset.id == forecast.dataset_id
            ).first()

            if not dataset:
                forecast.status = "failed"
                forecast.error_message = "Dataset not found"
                db.commit()
                return {
                    "status": "failed",
                    "forecast_id": forecast_id,
                    "error": "Dataset not found",
                }

            # Load data from storage
            data = _load_dataset(dataset)

            if data is None or data.empty:
                forecast.status = "failed"
                forecast.error_message = "Failed to load dataset or dataset is empty"
                db.commit()
                return {
                    "status": "failed",
                    "forecast_id": forecast_id,
                    "error": "Failed to load dataset",
                }

            self.update_state(state="PROGRESS", meta={"status": "generating_forecast"})

            # Determine target column
            target_col = forecast.target_metric
            if not target_col:
                # Try to find a target metric from dataset
                target_cols = [m.column_name for m in dataset.metrics if m.is_target]
                if target_cols:
                    target_col = target_cols[0]
                else:
                    # Default to first numeric column
                    numeric_cols = data.select_dtypes(include=['number']).columns.tolist()
                    target_col = numeric_cols[0] if numeric_cols else None

            if not target_col or target_col not in data.columns:
                forecast.status = "failed"
                forecast.error_message = f"Target column '{target_col}' not found in dataset"
                db.commit()
                return {
                    "status": "failed",
                    "forecast_id": forecast_id,
                    "error": f"Target column not found",
                }

            # Determine date column
            date_col = "date"
            possible_date_cols = ["date", "ds", "Date", "DATE", "timestamp", "time"]
            for col in possible_date_cols:
                if col in data.columns:
                    date_col = col
                    break

            # Build forecast config
            model_type_map = {
                "prophet": ModelType.PROPHET,
                "arima": ModelType.ARIMA,
                "ensemble": ModelType.ENSEMBLE,
                "neural": ModelType.NEURAL,
                "nbeats": ModelType.NBEATS,
                "tft": ModelType.TFT,
            }
            model_type = model_type_map.get(
                forecast.model_type.lower(),
                ModelType.PROPHET
            )

            config = ForecastConfig(
                model_type=model_type,
                horizon=forecast.horizon or 30,
                confidence_level=forecast.confidence_level or 0.95,
            )

            # Run forecast service
            service = ForecastService()
            job = service.create_forecast(
                data=data,
                target_col=target_col,
                date_col=date_col,
                config=config,
            )

            self.update_state(state="PROGRESS", meta={"status": "saving_results"})

            # Save results to database
            if job.result:
                forecast.predicted_values = job.result.get("values", [])
                forecast.lower_bounds = job.result.get("lower", [])
                forecast.upper_bounds = job.result.get("upper", [])
                forecast.forecast_dates = job.result.get("dates", [])
                forecast.metrics = job.result.get("metrics", {})
                forecast.status = "completed"
                forecast.error_message = None

                # Set forecast date range
                if forecast.forecast_dates:
                    forecast.forecast_start_date = forecast.forecast_dates[0]
                    forecast.forecast_end_date = forecast.forecast_dates[-1]
            else:
                forecast.status = "failed"
                forecast.error_message = job.error_message or "Forecast generation failed"

            db.commit()

            logger.info(
                "Forecast generation completed",
                forecast_id=forecast_id,
                status=forecast.status,
                metrics=forecast.metrics,
            )

            return {
                "status": forecast.status,
                "forecast_id": forecast_id,
                "metrics": forecast.metrics,
            }

    except Exception as e:
        logger.exception("Forecast generation failed", forecast_id=forecast_id)

        # Update forecast status
        try:
            with get_sync_session() as db:
                forecast = db.query(Forecast).filter(
                    Forecast.id == forecast_id
                ).first()
                if forecast:
                    forecast.status = "failed"
                    forecast.error_message = str(e)
                    db.commit()
        except Exception:
            pass

        return {
            "status": "failed",
            "forecast_id": forecast_id,
            "error": str(e),
        }


def _load_dataset(dataset: Dataset) -> Optional[pd.DataFrame]:
    """Load dataset from storage.

    Args:
        dataset: Dataset model instance.

    Returns:
        DataFrame with data or None if loading fails.
    """
    try:
        storage_path = dataset.storage_path
        if not storage_path:
            logger.warning("Dataset has no storage path", dataset_id=str(dataset.id))
            return None

        # Load based on format
        storage_format = dataset.storage_format.lower() if dataset.storage_format else "csv"

        if storage_format == "parquet":
            data = pd.read_parquet(storage_path)
        elif storage_format == "csv":
            data = pd.read_csv(storage_path)
        elif storage_format == "json":
            data = pd.read_json(storage_path)
        else:
            # Default to CSV
            data = pd.read_csv(storage_path)

        logger.info(
            "Dataset loaded",
            dataset_id=str(dataset.id),
            rows=len(data),
            columns=len(data.columns),
        )
        return data

    except Exception as e:
        logger.error(
            "Failed to load dataset",
            dataset_id=str(dataset.id),
            error=str(e),
        )
        return None
