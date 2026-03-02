"""
Domain Events

Events that occur within the domain layer.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid
from abc import ABC


@dataclass
class DomainEvent(ABC):
    """Base class for domain events."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    version: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def event_type(self) -> str:
        return self.__class__.__name__

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "version": self.version,
            "metadata": self.metadata,
        }


@dataclass
class ForecastCreatedEvent(DomainEvent):
    """Event raised when a forecast is created."""
    forecast_id: str = ""
    model_type: str = ""
    target_metric: str = ""
    horizon: int = 0
    organization_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "forecast_id": self.forecast_id,
            "model_type": self.model_type,
            "target_metric": self.target_metric,
            "horizon": self.horizon,
            "organization_id": self.organization_id,
        })
        return data


@dataclass
class ForecastCompletedEvent(DomainEvent):
    """Event raised when a forecast completes."""
    forecast_id: str = ""
    status: str = "completed"  # completed, failed
    metrics: Dict[str, float] = field(default_factory=dict)
    duration_seconds: float = 0.0
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "forecast_id": self.forecast_id,
            "status": self.status,
            "metrics": self.metrics,
            "duration_seconds": self.duration_seconds,
            "error_message": self.error_message,
        })
        return data


@dataclass
class ModelTrainedEvent(DomainEvent):
    """Event raised when a model is trained."""
    model_id: str = ""
    model_type: str = ""
    training_data_size: int = 0
    training_duration_seconds: float = 0.0
    metrics: Dict[str, float] = field(default_factory=dict)
    hyperparameters: Dict[str, Any] = field(default_factory=dict)
    organization_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "model_id": self.model_id,
            "model_type": self.model_type,
            "training_data_size": self.training_data_size,
            "training_duration_seconds": self.training_duration_seconds,
            "metrics": self.metrics,
            "hyperparameters": self.hyperparameters,
            "organization_id": self.organization_id,
        })
        return data


@dataclass
class CampaignCreatedEvent(DomainEvent):
    """Event raised when a campaign is created."""
    campaign_id: str = ""
    campaign_name: str = ""
    channel_id: str = ""
    budget: float = 0.0
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    organization_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "campaign_id": self.campaign_id,
            "campaign_name": self.campaign_name,
            "channel_id": self.channel_id,
            "budget": self.budget,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "organization_id": self.organization_id,
        })
        return data


@dataclass
class DataImportedEvent(DomainEvent):
    """Event raised when data is imported."""
    import_id: str = ""
    source: str = ""  # csv, api, database
    table_name: str = ""
    row_count: int = 0
    column_count: int = 0
    date_range: Optional[str] = None
    organization_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "import_id": self.import_id,
            "source": self.source,
            "table_name": self.table_name,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "date_range": self.date_range,
            "organization_id": self.organization_id,
        })
        return data


@dataclass
class OptimizationCompletedEvent(DomainEvent):
    """Event raised when budget optimization completes."""
    optimization_id: str = ""
    total_budget: float = 0.0
    predicted_roi: float = 0.0
    channel_allocations: Dict[str, float] = field(default_factory=dict)
    constraints_satisfied: bool = True
    organization_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "optimization_id": self.optimization_id,
            "total_budget": self.total_budget,
            "predicted_roi": self.predicted_roi,
            "channel_allocations": self.channel_allocations,
            "constraints_satisfied": self.constraints_satisfied,
            "organization_id": self.organization_id,
        })
        return data


@dataclass
class AlertTriggeredEvent(DomainEvent):
    """Event raised when an alert is triggered."""
    alert_id: str = ""
    alert_type: str = ""  # anomaly, threshold, forecast_drift
    severity: str = "warning"  # info, warning, critical
    metric_name: str = ""
    current_value: float = 0.0
    threshold_value: Optional[float] = None
    message: str = ""
    organization_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "alert_id": self.alert_id,
            "alert_type": self.alert_type,
            "severity": self.severity,
            "metric_name": self.metric_name,
            "current_value": self.current_value,
            "threshold_value": self.threshold_value,
            "message": self.message,
            "organization_id": self.organization_id,
        })
        return data


@dataclass
class UserActionEvent(DomainEvent):
    """Event raised for user actions (audit trail)."""
    user_id: str = ""
    action: str = ""  # create, update, delete, view, export
    resource_type: str = ""  # campaign, forecast, model, report
    resource_id: str = ""
    changes: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    organization_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "user_id": self.user_id,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "changes": self.changes,
            "organization_id": self.organization_id,
        })
        return data


class EventBus:
    """Simple in-memory event bus for domain events."""

    def __init__(self):
        self._handlers: Dict[str, List[callable]] = {}
        self._event_log: List[DomainEvent] = []

    def subscribe(self, event_type: str, handler: callable) -> None:
        """Subscribe a handler to an event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: callable) -> None:
        """Unsubscribe a handler from an event type."""
        if event_type in self._handlers:
            self._handlers[event_type].remove(handler)

    def publish(self, event: DomainEvent) -> None:
        """Publish an event to all subscribers."""
        self._event_log.append(event)

        event_type = event.event_type
        if event_type in self._handlers:
            for handler in self._handlers[event_type]:
                try:
                    handler(event)
                except Exception as e:
                    # Log error but don't stop other handlers
                    print(f"Error in event handler: {e}")

    def get_events(
        self,
        event_type: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> List[DomainEvent]:
        """Get events from the log."""
        events = self._event_log

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        if since:
            events = [e for e in events if e.timestamp >= since]

        return events

    def clear_log(self) -> None:
        """Clear the event log."""
        self._event_log.clear()


# Global event bus instance
event_bus = EventBus()
