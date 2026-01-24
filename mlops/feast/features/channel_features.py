"""
Marketing channel feature definitions for Feast.

These features capture marketing spend, impressions, and derived metrics
for each marketing channel with various transformations.
"""

from datetime import timedelta

from feast import Entity, Feature, FeatureView, Field, ValueType
from feast.infra.offline_stores.contrib.postgres_offline_store.postgres_source import (
    PostgreSQLSource,
)
from feast.types import Float32, Float64, Int64, String

# Entity: Marketing Channel
channel_entity = Entity(
    name="channel",
    join_keys=["channel_id"],
    description="Marketing channel entity (e.g., TV, Digital, Print)",
)

# Data Source: Channel daily statistics from PostgreSQL
channel_daily_source = PostgreSQLSource(
    name="channel_daily_source",
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
            -- Adstock transformations (pre-computed)
            spend_adstock_alpha_0_3 as spend_adstock_low,
            spend_adstock_alpha_0_5 as spend_adstock_mid,
            spend_adstock_alpha_0_7 as spend_adstock_high,
            -- Saturation transformations
            spend_saturation_lambda_0_5 as spend_saturated_low,
            spend_saturation_lambda_0_8 as spend_saturated_mid,
            -- Lag features
            spend_lag_1,
            spend_lag_7,
            spend_lag_14,
            impressions_lag_1,
            impressions_lag_7,
            -- Rolling aggregates
            spend_rolling_7d_mean,
            spend_rolling_7d_sum,
            spend_rolling_14d_mean,
            spend_rolling_30d_mean,
            impressions_rolling_7d_mean,
            impressions_rolling_7d_sum,
            -- Time-based features
            updated_at as event_timestamp,
            created_at
        FROM marketing_channel_metrics
        WHERE date >= NOW() - INTERVAL '365 days'
    """,
    timestamp_field="event_timestamp",
    created_timestamp_column="created_at",
)

# Feature View: Channel daily statistics
channel_daily_stats = FeatureView(
    name="channel_daily_stats",
    entities=[channel_entity],
    ttl=timedelta(days=365),
    schema=[
        # Basic metrics
        Field(name="channel_name", dtype=String),
        Field(name="spend", dtype=Float64),
        Field(name="impressions", dtype=Float64),
        Field(name="clicks", dtype=Float64),
        Field(name="conversions", dtype=Float64),
        Field(name="cost_per_click", dtype=Float64),
        Field(name="cost_per_impression", dtype=Float64),
        Field(name="conversion_rate", dtype=Float64),
        # Adstock features
        Field(name="spend_adstock_low", dtype=Float64),
        Field(name="spend_adstock_mid", dtype=Float64),
        Field(name="spend_adstock_high", dtype=Float64),
        # Saturation features
        Field(name="spend_saturated_low", dtype=Float64),
        Field(name="spend_saturated_mid", dtype=Float64),
        # Lag features
        Field(name="spend_lag_1", dtype=Float64),
        Field(name="spend_lag_7", dtype=Float64),
        Field(name="spend_lag_14", dtype=Float64),
        Field(name="impressions_lag_1", dtype=Float64),
        Field(name="impressions_lag_7", dtype=Float64),
        # Rolling aggregates
        Field(name="spend_rolling_7d_mean", dtype=Float64),
        Field(name="spend_rolling_7d_sum", dtype=Float64),
        Field(name="spend_rolling_14d_mean", dtype=Float64),
        Field(name="spend_rolling_30d_mean", dtype=Float64),
        Field(name="impressions_rolling_7d_mean", dtype=Float64),
        Field(name="impressions_rolling_7d_sum", dtype=Float64),
    ],
    source=channel_daily_source,
    online=True,
    tags={
        "team": "marketing_analytics",
        "data_quality": "gold",
        "refresh_frequency": "daily",
    },
)

# Data Source: Channel weekly aggregates
channel_weekly_source = PostgreSQLSource(
    name="channel_weekly_source",
    query="""
        SELECT
            channel_id,
            date_trunc('week', date) as week_start,
            channel_name,
            SUM(spend) as weekly_spend,
            SUM(impressions) as weekly_impressions,
            SUM(clicks) as weekly_clicks,
            SUM(conversions) as weekly_conversions,
            AVG(cost_per_click) as avg_cpc,
            AVG(cost_per_impression) as avg_cpm,
            AVG(conversion_rate) as avg_conversion_rate,
            -- Week-over-week changes
            LAG(SUM(spend), 1) OVER (PARTITION BY channel_id ORDER BY date_trunc('week', date)) as prev_week_spend,
            (SUM(spend) - LAG(SUM(spend), 1) OVER (PARTITION BY channel_id ORDER BY date_trunc('week', date))) /
                NULLIF(LAG(SUM(spend), 1) OVER (PARTITION BY channel_id ORDER BY date_trunc('week', date)), 0) * 100 as spend_wow_change_pct,
            MAX(updated_at) as event_timestamp,
            MIN(created_at) as created_at
        FROM marketing_channel_metrics
        WHERE date >= NOW() - INTERVAL '365 days'
        GROUP BY channel_id, date_trunc('week', date), channel_name
    """,
    timestamp_field="event_timestamp",
    created_timestamp_column="created_at",
)

# Feature View: Channel weekly aggregates
channel_weekly_aggregates = FeatureView(
    name="channel_weekly_aggregates",
    entities=[channel_entity],
    ttl=timedelta(days=365),
    schema=[
        Field(name="channel_name", dtype=String),
        Field(name="weekly_spend", dtype=Float64),
        Field(name="weekly_impressions", dtype=Float64),
        Field(name="weekly_clicks", dtype=Float64),
        Field(name="weekly_conversions", dtype=Float64),
        Field(name="avg_cpc", dtype=Float64),
        Field(name="avg_cpm", dtype=Float64),
        Field(name="avg_conversion_rate", dtype=Float64),
        Field(name="prev_week_spend", dtype=Float64),
        Field(name="spend_wow_change_pct", dtype=Float64),
    ],
    source=channel_weekly_source,
    online=True,
    tags={
        "team": "marketing_analytics",
        "data_quality": "gold",
        "refresh_frequency": "weekly",
    },
)
