"""Logging and monitoring configuration."""

import logging
import sys
from typing import Any

import structlog
from structlog.types import Processor

from app.config import settings


def configure_logging() -> None:
    """Configure structured logging for the application."""
    # Set log level
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # Common processors for all environments
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.LOG_FORMAT == "json":
        # JSON format for production
        processors: list[Processor] = [
            *shared_processors,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Console format for development
        processors = [
            *shared_processors,
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # Set third-party loggers to WARNING to reduce noise
    for logger_name in ["uvicorn", "uvicorn.access", "sqlalchemy", "httpx"]:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a logger instance."""
    return structlog.get_logger(name)


class RequestLogger:
    """Middleware for logging HTTP requests."""

    def __init__(self, logger: structlog.stdlib.BoundLogger | None = None) -> None:
        self.logger = logger or get_logger("http")

    async def log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        user_id: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """Log HTTP request details."""
        log_data = {
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
        }
        if user_id:
            log_data["user_id"] = user_id
        if extra:
            log_data.update(extra)

        if status_code >= 500:
            self.logger.error("HTTP request failed", **log_data)
        elif status_code >= 400:
            self.logger.warning("HTTP request error", **log_data)
        else:
            self.logger.info("HTTP request", **log_data)


class MLLogger:
    """Logger for ML operations."""

    def __init__(self, logger: structlog.stdlib.BoundLogger | None = None) -> None:
        self.logger = logger or get_logger("ml")

    def log_training_start(
        self,
        model_type: str,
        experiment_id: str,
        parameters: dict[str, Any],
    ) -> None:
        """Log the start of model training."""
        self.logger.info(
            "Model training started",
            model_type=model_type,
            experiment_id=experiment_id,
            parameters=parameters,
        )

    def log_training_complete(
        self,
        model_type: str,
        experiment_id: str,
        metrics: dict[str, Any],
        duration_seconds: float,
    ) -> None:
        """Log successful model training completion."""
        self.logger.info(
            "Model training completed",
            model_type=model_type,
            experiment_id=experiment_id,
            metrics=metrics,
            duration_seconds=round(duration_seconds, 2),
        )

    def log_training_error(
        self,
        model_type: str,
        experiment_id: str,
        error: str,
        traceback: str | None = None,
    ) -> None:
        """Log model training error."""
        self.logger.error(
            "Model training failed",
            model_type=model_type,
            experiment_id=experiment_id,
            error=error,
            traceback=traceback,
        )

    def log_prediction(
        self,
        model_id: str,
        input_shape: tuple[int, ...],
        duration_ms: float,
    ) -> None:
        """Log model prediction."""
        self.logger.info(
            "Model prediction",
            model_id=model_id,
            input_shape=input_shape,
            duration_ms=round(duration_ms, 2),
        )


class AuditLogger:
    """Logger for audit events."""

    def __init__(self, logger: structlog.stdlib.BoundLogger | None = None) -> None:
        self.logger = logger or get_logger("audit")

    def log_event(
        self,
        event_type: str,
        user_id: str | None,
        resource_type: str,
        resource_id: str | None,
        action: str,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
    ) -> None:
        """Log an audit event."""
        self.logger.info(
            f"Audit: {event_type}",
            event_type=event_type,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            details=details or {},
            ip_address=ip_address,
        )
