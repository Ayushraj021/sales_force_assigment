"""
PostgreSQL data source configurations for Feast.

Defines reusable data sources for feature retrieval from
the PostgreSQL/TimescaleDB database.
"""

import os

from feast.infra.offline_stores.contrib.postgres_offline_store.postgres_source import (
    PostgreSQLSource,
)


def get_postgres_connection_string() -> str:
    """Get PostgreSQL connection string from environment."""
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    database = os.getenv("POSTGRES_DB", "sales_forecasting")

    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


# Marketing channel metrics source
marketing_channel_source = PostgreSQLSource(
    name="marketing_channels",
    query="""
        SELECT
            channel_id,
            date,
            channel_name,
            spend,
            impressions,
            clicks,
            conversions,
            cost_per_click,
            cost_per_impression,
            conversion_rate,
            updated_at as event_timestamp,
            created_at
        FROM marketing_channel_metrics
    """,
    timestamp_field="event_timestamp",
    created_timestamp_column="created_at",
)

# Sales metrics source
sales_metrics_source = PostgreSQLSource(
    name="sales_metrics",
    query="""
        SELECT
            sales_id,
            date,
            revenue,
            units_sold,
            transactions,
            average_order_value,
            updated_at as event_timestamp,
            created_at
        FROM sales_metrics
    """,
    timestamp_field="event_timestamp",
    created_timestamp_column="created_at",
)

# Product metrics source
product_metrics_source = PostgreSQLSource(
    name="product_metrics",
    query="""
        SELECT
            product_id,
            date,
            product_name,
            category,
            revenue,
            units_sold,
            average_price,
            updated_at as event_timestamp,
            created_at
        FROM product_metrics
    """,
    timestamp_field="event_timestamp",
    created_timestamp_column="created_at",
)

# Customer segment metrics source
customer_segment_source = PostgreSQLSource(
    name="customer_segments",
    query="""
        SELECT
            segment_id,
            date,
            segment_name,
            customer_count,
            total_revenue,
            average_order_value,
            retention_rate,
            updated_at as event_timestamp,
            created_at
        FROM customer_segment_metrics
    """,
    timestamp_field="event_timestamp",
    created_timestamp_column="created_at",
)

# Pre-computed feature store source (for transformed features)
transformed_features_source = PostgreSQLSource(
    name="transformed_features",
    query="""
        SELECT
            entity_id,
            entity_type,
            date,
            feature_name,
            feature_value,
            updated_at as event_timestamp,
            created_at
        FROM feast_transformed_features
    """,
    timestamp_field="event_timestamp",
    created_timestamp_column="created_at",
)
