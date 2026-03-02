"""
Data Clean Room Implementation

Privacy-preserving data collaboration and analysis.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Protocol
from datetime import datetime
from enum import Enum
import logging
import hashlib
import pandas as pd

logger = logging.getLogger(__name__)


class QueryType(str, Enum):
    """Types of clean room queries."""
    OVERLAP = "overlap"  # Audience overlap analysis
    AGGREGATE = "aggregate"  # Aggregated statistics
    REACH = "reach"  # Reach and frequency
    ATTRIBUTION = "attribution"  # Cross-publisher attribution
    LOOKALIKE = "lookalike"  # Lookalike modeling


class AggregationType(str, Enum):
    """Aggregation types for privacy."""
    SUM = "sum"
    COUNT = "count"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT_DISTINCT = "count_distinct"


@dataclass
class CleanRoomConfig:
    """Configuration for clean room operations."""
    provider: str = "aws"  # aws, snowflake, google_ads_data_hub
    min_aggregation_threshold: int = 50  # Minimum records for aggregation
    noise_enabled: bool = True
    epsilon: float = 1.0  # Differential privacy epsilon
    allowed_columns: List[str] = field(default_factory=list)
    blocked_columns: List[str] = field(default_factory=list)
    max_query_rows: int = 1000000


@dataclass
class CleanRoomQuery:
    """Clean room query definition."""
    query_id: str
    query_type: QueryType
    datasets: List[str]  # Datasets involved
    join_keys: List[str]  # Keys to join on (hashed)
    select_columns: List[str]
    aggregations: Dict[str, AggregationType] = field(default_factory=dict)
    filters: Dict[str, Any] = field(default_factory=dict)
    group_by: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class QueryResult:
    """Result from a clean room query."""
    query_id: str
    status: str  # success, failed, privacy_violation
    row_count: int = 0
    execution_time_ms: float = 0.0
    data: Optional[pd.DataFrame] = None
    error_message: Optional[str] = None
    privacy_budget_used: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class CleanRoomProvider(Protocol):
    """Protocol for clean room providers."""

    def connect(self) -> bool:
        """Connect to the clean room."""
        ...

    def execute_query(self, query: CleanRoomQuery) -> QueryResult:
        """Execute a clean room query."""
        ...

    def list_datasets(self) -> List[str]:
        """List available datasets."""
        ...

    def get_schema(self, dataset: str) -> Dict[str, str]:
        """Get dataset schema."""
        ...


class CleanRoom:
    """
    Data Clean Room Manager.

    Features:
    - Multi-provider support (AWS, Snowflake, Google)
    - Privacy-preserving queries
    - Aggregation thresholds
    - Differential privacy noise

    Example:
        config = CleanRoomConfig(provider="aws")
        clean_room = CleanRoom(config)

        # Run overlap query
        query = CleanRoomQuery(
            query_id="q1",
            query_type=QueryType.OVERLAP,
            datasets=["first_party", "publisher"],
            join_keys=["hashed_email"],
            select_columns=["segment"],
            aggregations={"user_count": AggregationType.COUNT},
        )
        result = clean_room.execute(query)
    """

    def __init__(self, config: CleanRoomConfig, provider: Optional[CleanRoomProvider] = None):
        self.config = config
        self._provider = provider
        self._query_log: List[CleanRoomQuery] = []
        self._privacy_budget_used = 0.0

    def set_provider(self, provider: CleanRoomProvider) -> None:
        """Set the clean room provider."""
        self._provider = provider

    def execute(self, query: CleanRoomQuery) -> QueryResult:
        """
        Execute a clean room query.

        Args:
            query: Clean room query to execute

        Returns:
            QueryResult with data or error
        """
        # Validate query
        validation_error = self._validate_query(query)
        if validation_error:
            return QueryResult(
                query_id=query.query_id,
                status="failed",
                error_message=validation_error,
            )

        # Check privacy budget
        estimated_budget = self._estimate_privacy_budget(query)
        if self._privacy_budget_used + estimated_budget > self.config.epsilon:
            return QueryResult(
                query_id=query.query_id,
                status="privacy_violation",
                error_message="Privacy budget exhausted",
            )

        # Execute with provider
        if self._provider:
            result = self._provider.execute_query(query)
        else:
            # Mock execution for testing
            result = self._mock_execute(query)

        # Apply privacy controls
        if result.data is not None and self.config.noise_enabled:
            result.data = self._apply_privacy_controls(result.data, query)

        # Log query
        self._query_log.append(query)
        self._privacy_budget_used += estimated_budget
        result.privacy_budget_used = estimated_budget

        return result

    def _validate_query(self, query: CleanRoomQuery) -> Optional[str]:
        """Validate query against policy."""
        # Check blocked columns
        for col in query.select_columns + query.group_by:
            if col in self.config.blocked_columns:
                return f"Column '{col}' is blocked by policy"

        # Check allowed columns if specified
        if self.config.allowed_columns:
            for col in query.select_columns + query.group_by:
                if col not in self.config.allowed_columns:
                    return f"Column '{col}' is not in allowed list"

        return None

    def _estimate_privacy_budget(self, query: CleanRoomQuery) -> float:
        """Estimate privacy budget for query."""
        # Simple budget estimation based on aggregations
        base_budget = 0.1
        per_aggregation = 0.05
        return base_budget + len(query.aggregations) * per_aggregation

    def _apply_privacy_controls(
        self,
        data: pd.DataFrame,
        query: CleanRoomQuery,
    ) -> pd.DataFrame:
        """Apply privacy controls to query results."""
        import numpy as np

        # Apply minimum aggregation threshold
        if "count" in data.columns:
            data = data[data["count"] >= self.config.min_aggregation_threshold]

        # Add differential privacy noise to numeric columns
        for col in data.select_dtypes(include=[np.number]).columns:
            if col in query.aggregations:
                sensitivity = data[col].max() - data[col].min()
                if sensitivity > 0:
                    noise = np.random.laplace(
                        0, sensitivity / self.config.epsilon, len(data)
                    )
                    data[col] = data[col] + noise

        return data

    def _mock_execute(self, query: CleanRoomQuery) -> QueryResult:
        """Mock execution for testing."""
        import numpy as np

        # Generate mock data
        n_rows = 100
        data = {}

        for col in query.select_columns:
            data[col] = [f"{col}_{i}" for i in range(n_rows)]

        for col in query.group_by:
            data[col] = [f"group_{i % 5}" for i in range(n_rows)]

        for col, agg in query.aggregations.items():
            if agg == AggregationType.COUNT:
                data[col] = np.random.randint(50, 1000, n_rows)
            elif agg in (AggregationType.SUM, AggregationType.AVG):
                data[col] = np.random.uniform(100, 10000, n_rows)
            else:
                data[col] = np.random.uniform(0, 100, n_rows)

        df = pd.DataFrame(data)

        return QueryResult(
            query_id=query.query_id,
            status="success",
            row_count=len(df),
            execution_time_ms=150.0,
            data=df,
        )

    def overlap_analysis(
        self,
        first_party_dataset: str,
        partner_dataset: str,
        join_key: str = "hashed_email",
        segments: Optional[List[str]] = None,
    ) -> QueryResult:
        """
        Run audience overlap analysis.

        Args:
            first_party_dataset: First party data
            partner_dataset: Partner/publisher data
            join_key: Hashed key to join on
            segments: Optional segments to analyze

        Returns:
            QueryResult with overlap statistics
        """
        query = CleanRoomQuery(
            query_id=f"overlap_{datetime.utcnow().timestamp()}",
            query_type=QueryType.OVERLAP,
            datasets=[first_party_dataset, partner_dataset],
            join_keys=[join_key],
            select_columns=segments or [],
            aggregations={
                "total_users": AggregationType.COUNT_DISTINCT,
                "overlap_users": AggregationType.COUNT,
                "overlap_rate": AggregationType.AVG,
            },
            group_by=segments or [],
        )
        return self.execute(query)

    def reach_frequency(
        self,
        impression_dataset: str,
        conversion_dataset: str,
        join_key: str = "hashed_user_id",
        time_window: int = 30,
    ) -> QueryResult:
        """
        Calculate reach and frequency metrics.

        Args:
            impression_dataset: Impression data
            conversion_dataset: Conversion data
            join_key: Hashed key to join on
            time_window: Analysis time window in days

        Returns:
            QueryResult with reach/frequency metrics
        """
        query = CleanRoomQuery(
            query_id=f"reach_{datetime.utcnow().timestamp()}",
            query_type=QueryType.REACH,
            datasets=[impression_dataset, conversion_dataset],
            join_keys=[join_key],
            select_columns=[],
            aggregations={
                "unique_reach": AggregationType.COUNT_DISTINCT,
                "total_impressions": AggregationType.COUNT,
                "avg_frequency": AggregationType.AVG,
            },
            filters={"time_window_days": time_window},
        )
        return self.execute(query)

    def hash_pii(self, value: str, salt: str = "") -> str:
        """
        Hash PII for clean room matching.

        Args:
            value: PII value to hash
            salt: Optional salt

        Returns:
            SHA-256 hash
        """
        normalized = value.lower().strip()
        salted = f"{normalized}{salt}"
        return hashlib.sha256(salted.encode()).hexdigest()

    def get_query_log(self) -> List[CleanRoomQuery]:
        """Get query history."""
        return self._query_log.copy()

    def get_privacy_budget_remaining(self) -> float:
        """Get remaining privacy budget."""
        return max(0, self.config.epsilon - self._privacy_budget_used)

    def reset_privacy_budget(self) -> None:
        """Reset privacy budget (for new time period)."""
        self._privacy_budget_used = 0.0
