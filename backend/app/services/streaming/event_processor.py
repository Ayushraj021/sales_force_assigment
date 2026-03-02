"""
Event Processor for Real-Time Analytics

Processes incoming events and computes real-time metrics.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Callable, Any
from datetime import datetime, timedelta
from enum import Enum
import asyncio
from collections import defaultdict
import json
import logging

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Types of events that can be processed."""
    IMPRESSION = "impression"
    CLICK = "click"
    CONVERSION = "conversion"
    PAGE_VIEW = "page_view"
    ADD_TO_CART = "add_to_cart"
    PURCHASE = "purchase"
    SIGNUP = "signup"
    CUSTOM = "custom"


@dataclass
class Event:
    """Raw event from data source."""

    event_id: str
    event_type: EventType
    timestamp: datetime
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    channel: Optional[str] = None
    campaign: Optional[str] = None
    value: float = 0.0
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "session_id": self.session_id,
            "channel": self.channel,
            "campaign": self.campaign,
            "value": self.value,
            "properties": self.properties,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Event":
        return cls(
            event_id=data["event_id"],
            event_type=EventType(data["event_type"]),
            timestamp=datetime.fromisoformat(data["timestamp"]) if isinstance(data["timestamp"], str) else data["timestamp"],
            user_id=data.get("user_id"),
            session_id=data.get("session_id"),
            channel=data.get("channel"),
            campaign=data.get("campaign"),
            value=data.get("value", 0.0),
            properties=data.get("properties", {}),
        )


@dataclass
class ProcessedEvent:
    """Processed event with enriched data."""

    event: Event
    processed_at: datetime
    enrichments: Dict[str, Any] = field(default_factory=dict)
    aggregation_keys: List[str] = field(default_factory=list)


@dataclass
class AggregationWindow:
    """Aggregation window for real-time metrics."""

    start_time: datetime
    end_time: datetime
    metrics: Dict[str, float] = field(default_factory=dict)
    event_count: int = 0


class EventProcessor:
    """
    Real-Time Event Processor.

    Features:
    - Event enrichment with additional context
    - Real-time aggregation by time windows
    - Metric computation (impressions, clicks, conversions)
    - Channel attribution tracking
    - Anomaly detection on metrics

    Example:
        processor = EventProcessor()

        # Register handlers
        processor.register_handler(EventType.CONVERSION, handle_conversion)

        # Process events
        for event in event_stream:
            processed = await processor.process(event)
    """

    def __init__(
        self,
        window_size: timedelta = timedelta(minutes=5),
        max_windows: int = 12,  # Keep 1 hour of windows
    ):
        self.window_size = window_size
        self.max_windows = max_windows

        # Handlers for each event type
        self.handlers: Dict[EventType, List[Callable]] = defaultdict(list)

        # Time-based aggregation windows
        self.windows: Dict[str, List[AggregationWindow]] = defaultdict(list)

        # Channel-level metrics
        self.channel_metrics: Dict[str, Dict[str, float]] = defaultdict(
            lambda: defaultdict(float)
        )

        # User journey tracking
        self.user_journeys: Dict[str, List[Event]] = defaultdict(list)

        # Real-time counters
        self.counters: Dict[str, int] = defaultdict(int)

        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

    def register_handler(
        self,
        event_type: EventType,
        handler: Callable[[Event], Any],
    ) -> None:
        """Register a handler for an event type."""
        self.handlers[event_type].append(handler)

    async def process(self, event: Event) -> ProcessedEvent:
        """
        Process a single event.

        Args:
            event: Raw event to process

        Returns:
            ProcessedEvent with enrichments
        """
        processed = ProcessedEvent(
            event=event,
            processed_at=datetime.utcnow(),
        )

        async with self._lock:
            # Update counters
            self.counters[event.event_type.value] += 1
            self.counters["total"] += 1

            # Update channel metrics
            if event.channel:
                self._update_channel_metrics(event)

            # Track user journey
            if event.user_id:
                self._track_journey(event)

            # Update aggregation windows
            self._update_windows(event)

            # Call registered handlers
            for handler in self.handlers.get(event.event_type, []):
                try:
                    result = handler(event)
                    if asyncio.iscoroutine(result):
                        result = await result
                    processed.enrichments["handler_result"] = result
                except Exception as e:
                    logger.error(f"Handler error: {e}")

            # Add computed enrichments
            processed.enrichments.update(self._compute_enrichments(event))

        return processed

    async def process_batch(self, events: List[Event]) -> List[ProcessedEvent]:
        """Process a batch of events."""
        return [await self.process(event) for event in events]

    def _update_channel_metrics(self, event: Event) -> None:
        """Update channel-level metrics."""
        channel = event.channel
        if not channel:
            return

        metrics = self.channel_metrics[channel]

        if event.event_type == EventType.IMPRESSION:
            metrics["impressions"] += 1
        elif event.event_type == EventType.CLICK:
            metrics["clicks"] += 1
            # Update CTR
            if metrics["impressions"] > 0:
                metrics["ctr"] = metrics["clicks"] / metrics["impressions"]
        elif event.event_type == EventType.CONVERSION:
            metrics["conversions"] += 1
            metrics["revenue"] += event.value
            # Update conversion rate
            if metrics["clicks"] > 0:
                metrics["cvr"] = metrics["conversions"] / metrics["clicks"]

    def _track_journey(self, event: Event) -> None:
        """Track user journey touchpoints."""
        journey = self.user_journeys[event.user_id]

        # Keep last 50 touchpoints per user
        if len(journey) >= 50:
            journey.pop(0)

        journey.append(event)

    def _update_windows(self, event: Event) -> None:
        """Update time-based aggregation windows."""
        window_key = event.channel or "all"
        windows = self.windows[window_key]

        # Get or create current window
        now = datetime.utcnow()
        window_start = now.replace(
            minute=(now.minute // int(self.window_size.total_seconds() / 60)) * int(self.window_size.total_seconds() / 60),
            second=0,
            microsecond=0,
        )
        window_end = window_start + self.window_size

        # Find or create window
        current_window = None
        for window in windows:
            if window.start_time == window_start:
                current_window = window
                break

        if current_window is None:
            current_window = AggregationWindow(
                start_time=window_start,
                end_time=window_end,
            )
            windows.append(current_window)

            # Clean up old windows
            while len(windows) > self.max_windows:
                windows.pop(0)

        # Update window metrics
        current_window.event_count += 1
        metric_key = f"{event.event_type.value}_count"
        current_window.metrics[metric_key] = current_window.metrics.get(metric_key, 0) + 1

        if event.value > 0:
            value_key = f"{event.event_type.value}_value"
            current_window.metrics[value_key] = current_window.metrics.get(value_key, 0) + event.value

    def _compute_enrichments(self, event: Event) -> Dict[str, Any]:
        """Compute enrichments for an event."""
        enrichments = {}

        # Add time-based features
        enrichments["hour_of_day"] = event.timestamp.hour
        enrichments["day_of_week"] = event.timestamp.weekday()
        enrichments["is_weekend"] = event.timestamp.weekday() >= 5

        # Add user journey length
        if event.user_id and event.user_id in self.user_journeys:
            journey = self.user_journeys[event.user_id]
            enrichments["journey_length"] = len(journey)
            enrichments["is_returning"] = len(journey) > 1

            # Time since last event
            if len(journey) > 1:
                last_event = journey[-2]
                time_diff = (event.timestamp - last_event.timestamp).total_seconds()
                enrichments["seconds_since_last_event"] = time_diff

        return enrichments

    def get_channel_metrics(
        self,
        channel: Optional[str] = None,
    ) -> Dict[str, Dict[str, float]]:
        """Get current channel metrics."""
        if channel:
            return {channel: dict(self.channel_metrics[channel])}
        return {ch: dict(metrics) for ch, metrics in self.channel_metrics.items()}

    def get_window_metrics(
        self,
        channel: Optional[str] = None,
        n_windows: int = 12,
    ) -> List[Dict]:
        """Get aggregated metrics by time window."""
        window_key = channel or "all"
        windows = self.windows.get(window_key, [])

        return [
            {
                "start_time": w.start_time.isoformat(),
                "end_time": w.end_time.isoformat(),
                "event_count": w.event_count,
                "metrics": w.metrics,
            }
            for w in windows[-n_windows:]
        ]

    def get_user_journey(self, user_id: str) -> List[Dict]:
        """Get journey for a specific user."""
        journey = self.user_journeys.get(user_id, [])
        return [e.to_dict() for e in journey]

    def get_realtime_stats(self) -> Dict[str, Any]:
        """Get current real-time statistics."""
        return {
            "total_events": self.counters["total"],
            "events_by_type": {
                et.value: self.counters[et.value]
                for et in EventType
                if self.counters[et.value] > 0
            },
            "active_channels": len(self.channel_metrics),
            "tracked_users": len(self.user_journeys),
            "active_windows": sum(len(w) for w in self.windows.values()),
        }

    async def detect_anomalies(
        self,
        metric: str = "conversions",
        threshold: float = 2.0,
    ) -> List[Dict]:
        """
        Detect anomalies in real-time metrics.

        Uses simple z-score based detection on windowed data.
        """
        anomalies = []

        for channel, windows in self.windows.items():
            if len(windows) < 3:
                continue

            values = [w.metrics.get(f"{metric}_count", 0) for w in windows]

            if len(values) < 3:
                continue

            import numpy as np
            mean = np.mean(values[:-1])
            std = np.std(values[:-1]) + 1e-6
            current = values[-1]

            z_score = abs(current - mean) / std

            if z_score > threshold:
                anomalies.append({
                    "channel": channel,
                    "metric": metric,
                    "current_value": current,
                    "expected_value": mean,
                    "z_score": z_score,
                    "direction": "high" if current > mean else "low",
                    "window_end": windows[-1].end_time.isoformat(),
                })

        return anomalies

    def reset(self) -> None:
        """Reset all state."""
        self.windows.clear()
        self.channel_metrics.clear()
        self.user_journeys.clear()
        self.counters.clear()
