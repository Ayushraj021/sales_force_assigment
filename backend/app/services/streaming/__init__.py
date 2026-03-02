"""
Streaming Services Module

Real-time data processing and event streaming:
- Kafka consumer for event ingestion
- Event processing and aggregation
- Real-time feature computation
"""

from .event_processor import (
    EventProcessor,
    Event,
    ProcessedEvent,
    EventType,
)

__all__ = [
    "EventProcessor",
    "Event",
    "ProcessedEvent",
    "EventType",
]

# Kafka consumer is optional (requires aiokafka)
try:
    from .kafka_consumer import (
        KafkaEventConsumer,
        KafkaConfig,
    )
    __all__.extend(["KafkaEventConsumer", "KafkaConfig"])
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
