"""
Sales and revenue feature definitions for Feast.

These features capture sales metrics and derived features
for forecasting and attribution models.
"""

from datetime import timedelta

from feast import Entity, Feature, FeatureView, Field
from feast.infra.offline_stores.contrib.postgres_offline_store.postgres_source import (
    PostgreSQLSource,
)
from feast.types import Float32, Float64, Int64, String

# Entity: Sales record (could be by product, region, or overall)
sales_entity = Entity(
    name="sales",
    join_keys=["sales_id"],
    description="Sales entity for revenue and transaction metrics",
)

# Data Source: Daily sales metrics
sales_daily_source = PostgreSQLSource(
    name="sales_daily_source",
    query="""
        SELECT
            sales_id,
            date,
            revenue,
            units_sold,
            transactions,
            average_order_value,
            -- Revenue transformations
            LOG(revenue + 1) as log_revenue,
            SQRT(revenue) as sqrt_revenue,
            -- Lag features
            LAG(revenue, 1) OVER (PARTITION BY sales_id ORDER BY date) as revenue_lag_1,
            LAG(revenue, 7) OVER (PARTITION BY sales_id ORDER BY date) as revenue_lag_7,
            LAG(revenue, 14) OVER (PARTITION BY sales_id ORDER BY date) as revenue_lag_14,
            LAG(revenue, 28) OVER (PARTITION BY sales_id ORDER BY date) as revenue_lag_28,
            LAG(revenue, 365) OVER (PARTITION BY sales_id ORDER BY date) as revenue_lag_365,
            -- Rolling aggregates
            AVG(revenue) OVER (
                PARTITION BY sales_id
                ORDER BY date
                ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
            ) as revenue_rolling_7d_mean,
            SUM(revenue) OVER (
                PARTITION BY sales_id
                ORDER BY date
                ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
            ) as revenue_rolling_7d_sum,
            AVG(revenue) OVER (
                PARTITION BY sales_id
                ORDER BY date
                ROWS BETWEEN 13 PRECEDING AND CURRENT ROW
            ) as revenue_rolling_14d_mean,
            AVG(revenue) OVER (
                PARTITION BY sales_id
                ORDER BY date
                ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
            ) as revenue_rolling_30d_mean,
            STDDEV(revenue) OVER (
                PARTITION BY sales_id
                ORDER BY date
                ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
            ) as revenue_rolling_30d_std,
            -- Year-over-year growth
            (revenue - LAG(revenue, 365) OVER (PARTITION BY sales_id ORDER BY date)) /
                NULLIF(LAG(revenue, 365) OVER (PARTITION BY sales_id ORDER BY date), 0) * 100 as revenue_yoy_growth_pct,
            -- Day-over-day growth
            (revenue - LAG(revenue, 1) OVER (PARTITION BY sales_id ORDER BY date)) /
                NULLIF(LAG(revenue, 1) OVER (PARTITION BY sales_id ORDER BY date), 0) * 100 as revenue_dod_growth_pct,
            -- Week-over-week growth (same day last week)
            (revenue - LAG(revenue, 7) OVER (PARTITION BY sales_id ORDER BY date)) /
                NULLIF(LAG(revenue, 7) OVER (PARTITION BY sales_id ORDER BY date), 0) * 100 as revenue_wow_growth_pct,
            -- Metadata
            updated_at as event_timestamp,
            created_at
        FROM sales_metrics
        WHERE date >= NOW() - INTERVAL '365 days'
    """,
    timestamp_field="event_timestamp",
    created_timestamp_column="created_at",
)

# Feature View: Daily sales metrics
sales_daily_metrics = FeatureView(
    name="sales_daily_metrics",
    entities=[sales_entity],
    ttl=timedelta(days=365),
    schema=[
        # Base metrics
        Field(name="revenue", dtype=Float64),
        Field(name="units_sold", dtype=Int64),
        Field(name="transactions", dtype=Int64),
        Field(name="average_order_value", dtype=Float64),
        # Transformations
        Field(name="log_revenue", dtype=Float64),
        Field(name="sqrt_revenue", dtype=Float64),
        # Lag features
        Field(name="revenue_lag_1", dtype=Float64),
        Field(name="revenue_lag_7", dtype=Float64),
        Field(name="revenue_lag_14", dtype=Float64),
        Field(name="revenue_lag_28", dtype=Float64),
        Field(name="revenue_lag_365", dtype=Float64),
        # Rolling aggregates
        Field(name="revenue_rolling_7d_mean", dtype=Float64),
        Field(name="revenue_rolling_7d_sum", dtype=Float64),
        Field(name="revenue_rolling_14d_mean", dtype=Float64),
        Field(name="revenue_rolling_30d_mean", dtype=Float64),
        Field(name="revenue_rolling_30d_std", dtype=Float64),
        # Growth metrics
        Field(name="revenue_yoy_growth_pct", dtype=Float64),
        Field(name="revenue_dod_growth_pct", dtype=Float64),
        Field(name="revenue_wow_growth_pct", dtype=Float64),
    ],
    source=sales_daily_source,
    online=True,
    tags={
        "team": "sales_analytics",
        "data_quality": "gold",
        "refresh_frequency": "daily",
    },
)

# Data Source: Weekly sales aggregates
sales_weekly_source = PostgreSQLSource(
    name="sales_weekly_source",
    query="""
        SELECT
            sales_id,
            date_trunc('week', date) as week_start,
            SUM(revenue) as weekly_revenue,
            SUM(units_sold) as weekly_units,
            SUM(transactions) as weekly_transactions,
            AVG(average_order_value) as avg_order_value,
            MIN(revenue) as min_daily_revenue,
            MAX(revenue) as max_daily_revenue,
            STDDEV(revenue) as revenue_std,
            -- Week-over-week comparisons
            LAG(SUM(revenue), 1) OVER (PARTITION BY sales_id ORDER BY date_trunc('week', date)) as prev_week_revenue,
            LAG(SUM(revenue), 4) OVER (PARTITION BY sales_id ORDER BY date_trunc('week', date)) as same_week_last_month_revenue,
            LAG(SUM(revenue), 52) OVER (PARTITION BY sales_id ORDER BY date_trunc('week', date)) as same_week_last_year_revenue,
            MAX(updated_at) as event_timestamp,
            MIN(created_at) as created_at
        FROM sales_metrics
        WHERE date >= NOW() - INTERVAL '365 days'
        GROUP BY sales_id, date_trunc('week', date)
    """,
    timestamp_field="event_timestamp",
    created_timestamp_column="created_at",
)

# Feature View: Weekly sales aggregates
sales_weekly_aggregates = FeatureView(
    name="sales_weekly_aggregates",
    entities=[sales_entity],
    ttl=timedelta(days=365),
    schema=[
        Field(name="weekly_revenue", dtype=Float64),
        Field(name="weekly_units", dtype=Int64),
        Field(name="weekly_transactions", dtype=Int64),
        Field(name="avg_order_value", dtype=Float64),
        Field(name="min_daily_revenue", dtype=Float64),
        Field(name="max_daily_revenue", dtype=Float64),
        Field(name="revenue_std", dtype=Float64),
        Field(name="prev_week_revenue", dtype=Float64),
        Field(name="same_week_last_month_revenue", dtype=Float64),
        Field(name="same_week_last_year_revenue", dtype=Float64),
    ],
    source=sales_weekly_source,
    online=True,
    tags={
        "team": "sales_analytics",
        "data_quality": "gold",
        "refresh_frequency": "weekly",
    },
)
