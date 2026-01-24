"""
Test Fixtures Package

Real marketing data for testing ML/DL models:
- real_mmm_data.csv: Weekly marketing mix data (sales + channel spends)
- real_daily_sales.csv: Daily sales time series
- real_geo_data.csv: Geographic experiment data
- real_journey_data.csv: Customer journey/touchpoint data
"""

from pathlib import Path
import pandas as pd
from typing import Optional

FIXTURES_DIR = Path(__file__).parent


def get_fixture_path(filename: str) -> Path:
    """Get the full path to a fixture file."""
    return FIXTURES_DIR / filename


def read_fixture(filename: str) -> str:
    """Read a fixture file and return its contents."""
    with open(get_fixture_path(filename), "r") as f:
        return f.read()


def load_mmm_data() -> pd.DataFrame:
    """
    Load real Marketing Mix Model data.

    Returns a DataFrame with columns:
    - date: Weekly date
    - sales: Revenue/sales
    - tv_spend, digital_spend, radio_spend, etc.: Channel spends
    - price: Product price
    - seasonality: Seasonality factor
    - promotion: Promotion indicator
    - holiday: Holiday indicator
    """
    csv_path = FIXTURES_DIR / "real_mmm_data.csv"
    if csv_path.exists():
        return pd.read_csv(csv_path, parse_dates=["date"])
    # Fallback to sample data
    csv_path = FIXTURES_DIR / "sample_mmm_data.csv"
    return pd.read_csv(csv_path, parse_dates=["date"])


def load_daily_sales() -> Optional[pd.DataFrame]:
    """
    Load real daily sales time series data.

    Returns a DataFrame with columns:
    - date: Daily date
    - daily_sales: Revenue
    - units_sold: Number of units
    - avg_order_value: AOV
    - visitors: Site visitors
    - conversion_rate: Conversion rate
    - promo_active: Promotion indicator
    - day_of_week: Day of week (0=Monday)
    - is_holiday: Holiday indicator
    """
    csv_path = FIXTURES_DIR / "real_daily_sales.csv"
    if csv_path.exists():
        return pd.read_csv(csv_path, parse_dates=["date"])
    return None


def load_geo_data() -> Optional[pd.DataFrame]:
    """
    Load real geographic experiment data.

    Returns a DataFrame with columns:
    - date: Date
    - region: Geographic region name
    - sales: Regional sales
    - marketing_spend: Marketing spend in region
    - is_test_region: Whether region is in test group
    - population: Region population
    - median_income: Median household income
    - competitor_presence: Competitor market share
    """
    csv_path = FIXTURES_DIR / "real_geo_data.csv"
    if csv_path.exists():
        return pd.read_csv(csv_path, parse_dates=["date"])
    return None


def load_journey_data() -> Optional[pd.DataFrame]:
    """
    Load real customer journey data.

    Returns a DataFrame with columns:
    - journey_id: Unique journey identifier
    - customer_id: Customer identifier
    - touchpoint_timestamp: Timestamp of touchpoint
    - channel: Marketing channel
    - campaign: Campaign name
    - conversion: Whether this touchpoint led to conversion
    - conversion_value: Value of conversion (if any)
    - device: Device type
    - session_duration: Session duration in seconds
    - page_views: Number of page views
    """
    csv_path = FIXTURES_DIR / "real_journey_data.csv"
    if csv_path.exists():
        return pd.read_csv(csv_path, parse_dates=["touchpoint_timestamp"])
    return None


def load_sample_mmm() -> pd.DataFrame:
    """Load original sample MMM data (smaller dataset)."""
    return pd.read_csv(FIXTURES_DIR / "sample_mmm_data.csv", parse_dates=["date"])


# Data summary functions
def describe_datasets():
    """Print summary of available fixture datasets."""
    print("Available Test Fixture Datasets")
    print("=" * 50)

    # MMM Data
    mmm_df = load_mmm_data()
    print(f"\n1. MMM Data: {len(mmm_df)} rows")
    print(f"   Date range: {mmm_df['date'].min()} to {mmm_df['date'].max()}")
    print(f"   Columns: {list(mmm_df.columns)}")

    # Daily Sales
    daily_df = load_daily_sales()
    if daily_df is not None:
        print(f"\n2. Daily Sales: {len(daily_df)} rows")
        print(f"   Date range: {daily_df['date'].min()} to {daily_df['date'].max()}")
    else:
        print("\n2. Daily Sales: Not available")

    # Geo Data
    geo_df = load_geo_data()
    if geo_df is not None:
        print(f"\n3. Geo Data: {len(geo_df)} rows")
        print(f"   Regions: {geo_df['region'].nunique()}")
        print(f"   Date range: {geo_df['date'].min()} to {geo_df['date'].max()}")
    else:
        print("\n3. Geo Data: Not available")

    # Journey Data
    journey_df = load_journey_data()
    if journey_df is not None:
        print(f"\n4. Journey Data: {len(journey_df)} touchpoints")
        print(f"   Journeys: {journey_df['journey_id'].nunique()}")
        print(f"   Channels: {journey_df['channel'].nunique()}")
    else:
        print("\n4. Journey Data: Not available")


if __name__ == "__main__":
    describe_datasets()
