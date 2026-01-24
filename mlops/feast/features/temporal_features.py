"""
Temporal and calendar feature definitions for Feast.

These features capture time-based patterns, holidays, and seasonality
for time series forecasting models.
"""

from datetime import timedelta

from feast import Entity, Feature, FeatureView, Field
from feast.infra.offline_stores.contrib.postgres_offline_store.postgres_source import (
    PostgreSQLSource,
)
from feast.types import Float32, Float64, Int32, Int64, String, Bool

# Entity: Date
date_entity = Entity(
    name="date",
    join_keys=["date_key"],
    description="Date entity for calendar and temporal features",
)

# Data Source: Calendar features
calendar_source = PostgreSQLSource(
    name="calendar_source",
    query="""
        SELECT
            TO_CHAR(date, 'YYYYMMDD')::INTEGER as date_key,
            date,
            -- Basic date components
            EXTRACT(YEAR FROM date)::INTEGER as year,
            EXTRACT(MONTH FROM date)::INTEGER as month,
            EXTRACT(DAY FROM date)::INTEGER as day_of_month,
            EXTRACT(DOW FROM date)::INTEGER as day_of_week,  -- 0=Sunday
            EXTRACT(DOY FROM date)::INTEGER as day_of_year,
            EXTRACT(WEEK FROM date)::INTEGER as week_of_year,
            EXTRACT(QUARTER FROM date)::INTEGER as quarter,
            -- Boolean flags
            CASE WHEN EXTRACT(DOW FROM date) IN (0, 6) THEN true ELSE false END as is_weekend,
            CASE WHEN EXTRACT(DOW FROM date) = 1 THEN true ELSE false END as is_monday,
            CASE WHEN EXTRACT(DOW FROM date) = 5 THEN true ELSE false END as is_friday,
            CASE WHEN EXTRACT(DAY FROM date) = 1 THEN true ELSE false END as is_month_start,
            CASE WHEN EXTRACT(DAY FROM date + INTERVAL '1 day') = 1 THEN true ELSE false END as is_month_end,
            CASE WHEN EXTRACT(MONTH FROM date) = 1 AND EXTRACT(DAY FROM date) = 1 THEN true ELSE false END as is_year_start,
            CASE WHEN EXTRACT(MONTH FROM date) = 12 AND EXTRACT(DAY FROM date) = 31 THEN true ELSE false END as is_year_end,
            -- Seasonality encoding (Fourier features)
            SIN(2 * PI() * EXTRACT(DOY FROM date) / 365.25) as sin_day_of_year,
            COS(2 * PI() * EXTRACT(DOY FROM date) / 365.25) as cos_day_of_year,
            SIN(2 * PI() * EXTRACT(DOW FROM date) / 7) as sin_day_of_week,
            COS(2 * PI() * EXTRACT(DOW FROM date) / 7) as cos_day_of_week,
            SIN(2 * PI() * EXTRACT(MONTH FROM date) / 12) as sin_month,
            COS(2 * PI() * EXTRACT(MONTH FROM date) / 12) as cos_month,
            SIN(4 * PI() * EXTRACT(DOY FROM date) / 365.25) as sin_day_of_year_2,
            COS(4 * PI() * EXTRACT(DOY FROM date) / 365.25) as cos_day_of_year_2,
            -- Month progress (0 to 1)
            EXTRACT(DAY FROM date)::FLOAT / EXTRACT(DAY FROM date_trunc('month', date) + INTERVAL '1 month' - INTERVAL '1 day')::FLOAT as month_progress,
            -- Year progress (0 to 1)
            EXTRACT(DOY FROM date)::FLOAT / 365.25 as year_progress,
            -- Days since/until month boundaries
            EXTRACT(DAY FROM date)::INTEGER - 1 as days_since_month_start,
            (EXTRACT(DAY FROM date_trunc('month', date) + INTERVAL '1 month' - INTERVAL '1 day') - EXTRACT(DAY FROM date))::INTEGER as days_until_month_end,
            -- Metadata
            date as event_timestamp,
            date as created_at
        FROM generate_series(
            NOW() - INTERVAL '730 days',
            NOW() + INTERVAL '365 days',
            INTERVAL '1 day'
        ) as date
    """,
    timestamp_field="event_timestamp",
    created_timestamp_column="created_at",
)

# Feature View: Calendar features
calendar_features = FeatureView(
    name="calendar_features",
    entities=[date_entity],
    ttl=timedelta(days=1095),  # 3 years
    schema=[
        # Date components
        Field(name="year", dtype=Int32),
        Field(name="month", dtype=Int32),
        Field(name="day_of_month", dtype=Int32),
        Field(name="day_of_week", dtype=Int32),
        Field(name="day_of_year", dtype=Int32),
        Field(name="week_of_year", dtype=Int32),
        Field(name="quarter", dtype=Int32),
        # Boolean flags
        Field(name="is_weekend", dtype=Bool),
        Field(name="is_monday", dtype=Bool),
        Field(name="is_friday", dtype=Bool),
        Field(name="is_month_start", dtype=Bool),
        Field(name="is_month_end", dtype=Bool),
        Field(name="is_year_start", dtype=Bool),
        Field(name="is_year_end", dtype=Bool),
        # Fourier features
        Field(name="sin_day_of_year", dtype=Float64),
        Field(name="cos_day_of_year", dtype=Float64),
        Field(name="sin_day_of_week", dtype=Float64),
        Field(name="cos_day_of_week", dtype=Float64),
        Field(name="sin_month", dtype=Float64),
        Field(name="cos_month", dtype=Float64),
        Field(name="sin_day_of_year_2", dtype=Float64),
        Field(name="cos_day_of_year_2", dtype=Float64),
        # Progress metrics
        Field(name="month_progress", dtype=Float64),
        Field(name="year_progress", dtype=Float64),
        Field(name="days_since_month_start", dtype=Int32),
        Field(name="days_until_month_end", dtype=Int32),
    ],
    source=calendar_source,
    online=True,
    tags={
        "team": "data_engineering",
        "data_quality": "gold",
        "refresh_frequency": "static",
    },
)

# Data Source: Holiday features
holiday_source = PostgreSQLSource(
    name="holiday_source",
    query="""
        SELECT
            TO_CHAR(date, 'YYYYMMDD')::INTEGER as date_key,
            date,
            -- Holiday indicators
            COALESCE(is_holiday, false) as is_holiday,
            COALESCE(holiday_name, '') as holiday_name,
            COALESCE(holiday_type, 'none') as holiday_type,  -- federal, religious, commercial, etc.
            -- Holiday proximity
            CASE
                WHEN is_holiday THEN 0
                ELSE COALESCE(
                    (SELECT MIN(ABS(h.date - date)) FROM holidays h WHERE h.date >= date - 7 AND h.date <= date + 7),
                    999
                )
            END as days_to_nearest_holiday,
            -- Pre/post holiday periods
            COALESCE(days_before_holiday, 999) as days_before_holiday,
            COALESCE(days_after_holiday, 999) as days_after_holiday,
            CASE WHEN days_before_holiday BETWEEN 1 AND 3 THEN true ELSE false END as is_pre_holiday,
            CASE WHEN days_after_holiday BETWEEN 1 AND 3 THEN true ELSE false END as is_post_holiday,
            -- Major commercial holidays
            CASE WHEN holiday_name IN ('Black Friday', 'Cyber Monday', 'Christmas', 'Amazon Prime Day')
                THEN true ELSE false END as is_major_shopping_day,
            -- Holiday week flag
            CASE WHEN is_holiday OR days_before_holiday <= 3 OR days_after_holiday <= 2
                THEN true ELSE false END as is_holiday_week,
            -- Metadata
            date as event_timestamp,
            date as created_at
        FROM calendar_dates cd
        LEFT JOIN holidays h ON cd.date = h.date
        WHERE cd.date >= NOW() - INTERVAL '730 days'
          AND cd.date <= NOW() + INTERVAL '365 days'
    """,
    timestamp_field="event_timestamp",
    created_timestamp_column="created_at",
)

# Feature View: Holiday features
holiday_features = FeatureView(
    name="holiday_features",
    entities=[date_entity],
    ttl=timedelta(days=1095),
    schema=[
        # Holiday indicators
        Field(name="is_holiday", dtype=Bool),
        Field(name="holiday_name", dtype=String),
        Field(name="holiday_type", dtype=String),
        # Proximity features
        Field(name="days_to_nearest_holiday", dtype=Int32),
        Field(name="days_before_holiday", dtype=Int32),
        Field(name="days_after_holiday", dtype=Int32),
        Field(name="is_pre_holiday", dtype=Bool),
        Field(name="is_post_holiday", dtype=Bool),
        # Special flags
        Field(name="is_major_shopping_day", dtype=Bool),
        Field(name="is_holiday_week", dtype=Bool),
    ],
    source=holiday_source,
    online=True,
    tags={
        "team": "data_engineering",
        "data_quality": "gold",
        "refresh_frequency": "daily",
    },
)
