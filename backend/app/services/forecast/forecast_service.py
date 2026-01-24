"""
Forecast Service

Orchestrates forecast generation and management.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum
import uuid
import logging
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class ModelType(str, Enum):
    """Available forecast models."""
    PROPHET = "prophet"
    ARIMA = "arima"
    ENSEMBLE = "ensemble"
    NEURAL = "neural"
    NBEATS = "nbeats"
    TFT = "tft"


class JobStatus(str, Enum):
    """Forecast job status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ForecastConfig:
    """Forecast configuration."""
    model_type: ModelType = ModelType.PROPHET
    horizon: int = 30
    confidence_level: float = 0.95
    include_holidays: bool = True
    country: str = "US"
    seasonality_mode: str = "multiplicative"
    changepoint_prior_scale: float = 0.05


@dataclass
class ForecastJob:
    """Forecast job entity."""
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: JobStatus = JobStatus.PENDING
    model_type: ModelType = ModelType.PROPHET
    config: ForecastConfig = field(default_factory=ForecastConfig)
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metrics: Dict[str, float] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "model_type": self.model_type.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "metrics": self.metrics,
        }


class ForecastService:
    """
    Forecast Service.

    Orchestrates forecast generation and model management.

    Example:
        service = ForecastService()

        # Create forecast
        job = service.create_forecast(
            data=df,
            target_col="sales",
            config=ForecastConfig(model_type=ModelType.PROPHET, horizon=30)
        )

        # Check status
        status = service.get_job_status(job.job_id)
    """

    def __init__(self):
        self._jobs: Dict[str, ForecastJob] = {}
        self._models: Dict[str, Any] = {}

    def create_forecast(
        self,
        data: pd.DataFrame,
        target_col: str,
        date_col: str = "date",
        config: Optional[ForecastConfig] = None,
    ) -> ForecastJob:
        """
        Create a forecast job.

        Args:
            data: Historical data
            target_col: Target column
            date_col: Date column
            config: Forecast configuration

        Returns:
            ForecastJob
        """
        config = config or ForecastConfig()

        job = ForecastJob(
            model_type=config.model_type,
            config=config,
        )
        self._jobs[job.job_id] = job

        try:
            job.status = JobStatus.RUNNING
            job.started_at = datetime.utcnow()

            # Run forecast
            result = self._run_forecast(data, target_col, date_col, config)

            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            job.result = result
            job.metrics = result.get("metrics", {})

        except Exception as e:
            logger.error(f"Forecast failed: {e}")
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()

        return job

    def _run_forecast(
        self,
        data: pd.DataFrame,
        target_col: str,
        date_col: str,
        config: ForecastConfig,
    ) -> Dict[str, Any]:
        """Run the forecast."""
        data = data.copy()
        data[date_col] = pd.to_datetime(data[date_col])
        data = data.sort_values(date_col)

        if config.model_type == ModelType.PROPHET:
            return self._run_prophet(data, target_col, date_col, config)
        elif config.model_type == ModelType.ARIMA:
            return self._run_arima(data, target_col, config)
        elif config.model_type == ModelType.ENSEMBLE:
            return self._run_ensemble(data, target_col, date_col, config)
        else:
            return self._run_simple(data, target_col, config)

    def _run_prophet(
        self,
        data: pd.DataFrame,
        target_col: str,
        date_col: str,
        config: ForecastConfig,
    ) -> Dict[str, Any]:
        """Run Prophet forecast."""
        try:
            from prophet import Prophet

            # Prepare data for Prophet
            prophet_df = data[[date_col, target_col]].rename(
                columns={date_col: "ds", target_col: "y"}
            )

            model = Prophet(
                seasonality_mode=config.seasonality_mode,
                changepoint_prior_scale=config.changepoint_prior_scale,
            )

            if config.include_holidays:
                model.add_country_holidays(country_name=config.country)

            model.fit(prophet_df)

            # Generate forecast
            future = model.make_future_dataframe(periods=config.horizon)
            forecast = model.predict(future)

            # Extract results
            predictions = forecast.tail(config.horizon)

            return {
                "dates": predictions["ds"].dt.strftime("%Y-%m-%d").tolist(),
                "values": predictions["yhat"].tolist(),
                "lower": predictions["yhat_lower"].tolist(),
                "upper": predictions["yhat_upper"].tolist(),
                "metrics": self._calculate_metrics(
                    data[target_col].values,
                    forecast.head(len(data))["yhat"].values
                ),
            }

        except ImportError:
            logger.warning("Prophet not available, using simple method")
            return self._run_simple(data, target_col, config)

    def _run_arima(
        self,
        data: pd.DataFrame,
        target_col: str,
        config: ForecastConfig,
    ) -> Dict[str, Any]:
        """Run ARIMA forecast."""
        try:
            from statsmodels.tsa.arima.model import ARIMA

            y = data[target_col].values

            model = ARIMA(y, order=(1, 1, 1))
            fitted = model.fit()

            forecast = fitted.forecast(steps=config.horizon)
            conf_int = fitted.get_forecast(steps=config.horizon).conf_int(alpha=1-config.confidence_level)

            # Generate future dates
            last_date = data.iloc[-1].get("date", pd.Timestamp.now())
            if isinstance(last_date, str):
                last_date = pd.to_datetime(last_date)
            future_dates = pd.date_range(start=last_date, periods=config.horizon + 1)[1:]

            return {
                "dates": future_dates.strftime("%Y-%m-%d").tolist(),
                "values": forecast.tolist(),
                "lower": conf_int.iloc[:, 0].tolist(),
                "upper": conf_int.iloc[:, 1].tolist(),
                "metrics": {"aic": fitted.aic, "bic": fitted.bic},
            }

        except ImportError:
            logger.warning("statsmodels not available, using simple method")
            return self._run_simple(data, target_col, config)

    def _run_ensemble(
        self,
        data: pd.DataFrame,
        target_col: str,
        date_col: str,
        config: ForecastConfig,
    ) -> Dict[str, Any]:
        """Run ensemble forecast."""
        results = []

        # Try multiple models
        for model_type in [ModelType.PROPHET, ModelType.ARIMA]:
            try:
                config_copy = ForecastConfig(
                    model_type=model_type,
                    horizon=config.horizon,
                    confidence_level=config.confidence_level,
                )
                if model_type == ModelType.PROPHET:
                    result = self._run_prophet(data, target_col, date_col, config_copy)
                else:
                    result = self._run_arima(data, target_col, config_copy)
                results.append(result)
            except Exception:
                continue

        if not results:
            return self._run_simple(data, target_col, config)

        # Average the forecasts
        values = np.mean([r["values"] for r in results], axis=0)
        lower = np.min([r["lower"] for r in results], axis=0)
        upper = np.max([r["upper"] for r in results], axis=0)

        return {
            "dates": results[0]["dates"],
            "values": values.tolist(),
            "lower": lower.tolist(),
            "upper": upper.tolist(),
            "metrics": {"models_used": len(results)},
        }

    def _run_simple(
        self,
        data: pd.DataFrame,
        target_col: str,
        config: ForecastConfig,
    ) -> Dict[str, Any]:
        """Run simple moving average forecast."""
        y = data[target_col].values

        # Simple exponential smoothing
        alpha = 0.3
        forecast = [y[-1]]
        for _ in range(config.horizon - 1):
            forecast.append(alpha * y[-1] + (1 - alpha) * forecast[-1])

        # Generate confidence intervals
        std = np.std(y)
        z = 1.96 if config.confidence_level == 0.95 else 2.576
        lower = [f - z * std for f in forecast]
        upper = [f + z * std for f in forecast]

        # Generate dates
        last_date = data.iloc[-1].get("date", pd.Timestamp.now())
        if isinstance(last_date, str):
            last_date = pd.to_datetime(last_date)
        future_dates = pd.date_range(start=last_date, periods=config.horizon + 1)[1:]

        return {
            "dates": future_dates.strftime("%Y-%m-%d").tolist(),
            "values": forecast,
            "lower": lower,
            "upper": upper,
            "metrics": {"method": "exponential_smoothing"},
        }

    def _calculate_metrics(
        self,
        actual: np.ndarray,
        predicted: np.ndarray,
    ) -> Dict[str, float]:
        """Calculate forecast metrics."""
        actual = np.asarray(actual).flatten()
        predicted = np.asarray(predicted).flatten()

        min_len = min(len(actual), len(predicted))
        actual = actual[:min_len]
        predicted = predicted[:min_len]

        errors = actual - predicted
        abs_errors = np.abs(errors)

        mape = np.mean(abs_errors / np.abs(actual + 1e-10)) * 100
        rmse = np.sqrt(np.mean(errors ** 2))
        mae = np.mean(abs_errors)

        return {
            "mape": round(float(mape), 2),
            "rmse": round(float(rmse), 2),
            "mae": round(float(mae), 2),
        }

    def get_job(self, job_id: str) -> Optional[ForecastJob]:
        """Get a forecast job."""
        return self._jobs.get(job_id)

    def get_job_status(self, job_id: str) -> Optional[str]:
        """Get job status."""
        job = self._jobs.get(job_id)
        return job.status.value if job else None

    def list_jobs(
        self,
        status: Optional[JobStatus] = None,
    ) -> List[ForecastJob]:
        """List forecast jobs."""
        jobs = list(self._jobs.values())
        if status:
            jobs = [j for j in jobs if j.status == status]
        return jobs

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a forecast job."""
        job = self._jobs.get(job_id)
        if job and job.status == JobStatus.RUNNING:
            job.status = JobStatus.CANCELLED
            return True
        return False
