"""
Google Analytics 4 Connector

Integrates with GA4 for web analytics data.
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
import logging
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class GoogleAnalyticsConfig:
    """GA4 connection configuration."""
    property_id: str
    credentials_path: Optional[str] = None


class GoogleAnalyticsConnector:
    """
    Google Analytics 4 Connector.

    Features:
    - Run reports
    - Realtime data
    - User metrics
    - Conversion tracking

    Example:
        connector = GoogleAnalyticsConnector(config)
        report = connector.run_report(
            dimensions=["date"],
            metrics=["sessions", "activeUsers"],
            start_date="2024-01-01",
            end_date="2024-01-31"
        )
    """

    def __init__(self, config: GoogleAnalyticsConfig):
        self.config = config
        self._client = None

        try:
            from google.analytics.data_v1beta import BetaAnalyticsDataClient
            from google.oauth2 import service_account

            if config.credentials_path:
                credentials = service_account.Credentials.from_service_account_file(
                    config.credentials_path
                )
                self._client = BetaAnalyticsDataClient(credentials=credentials)
            else:
                self._client = BetaAnalyticsDataClient()

        except ImportError:
            logger.warning("google-analytics-data not installed")
        except Exception as e:
            logger.error(f"Failed to connect to GA4: {e}")

    def run_report(
        self,
        dimensions: List[str],
        metrics: List[str],
        start_date: str,
        end_date: str,
        dimension_filter: Optional[Dict] = None,
    ) -> pd.DataFrame:
        """
        Run a GA4 report.

        Args:
            dimensions: Dimension names (e.g., ["date", "country"])
            metrics: Metric names (e.g., ["sessions", "activeUsers"])
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            dimension_filter: Optional dimension filter

        Returns:
            DataFrame with report data
        """
        if not self._client:
            return self._mock_report(dimensions, metrics, start_date, end_date)

        try:
            from google.analytics.data_v1beta.types import (
                RunReportRequest,
                DateRange,
                Dimension,
                Metric,
            )

            request = RunReportRequest(
                property=f"properties/{self.config.property_id}",
                date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
                dimensions=[Dimension(name=d) for d in dimensions],
                metrics=[Metric(name=m) for m in metrics],
            )

            response = self._client.run_report(request)

            # Parse response
            rows = []
            for row in response.rows:
                row_data = {}
                for i, dim in enumerate(dimensions):
                    row_data[dim] = row.dimension_values[i].value
                for i, met in enumerate(metrics):
                    row_data[met] = float(row.metric_values[i].value)
                rows.append(row_data)

            return pd.DataFrame(rows)

        except Exception as e:
            logger.error(f"Report failed: {e}")
            return self._mock_report(dimensions, metrics, start_date, end_date)

    def _mock_report(
        self,
        dimensions: List[str],
        metrics: List[str],
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """Generate mock report data."""
        import random
        from datetime import datetime, timedelta

        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        days = (end - start).days + 1

        data = []
        for i in range(days):
            date = start + timedelta(days=i)
            row = {}

            for dim in dimensions:
                if dim == "date":
                    row[dim] = date.strftime("%Y%m%d")
                elif dim == "country":
                    row[dim] = random.choice(["United States", "United Kingdom", "Canada"])
                elif dim == "deviceCategory":
                    row[dim] = random.choice(["desktop", "mobile", "tablet"])
                elif dim == "sessionSource":
                    row[dim] = random.choice(["google", "direct", "facebook"])
                else:
                    row[dim] = f"value_{i}"

            for met in metrics:
                if met in ["sessions", "activeUsers", "newUsers"]:
                    row[met] = random.randint(100, 1000)
                elif met == "screenPageViews":
                    row[met] = random.randint(200, 2000)
                elif met in ["engagementRate", "bounceRate"]:
                    row[met] = random.uniform(0.3, 0.8)
                elif met == "averageSessionDuration":
                    row[met] = random.uniform(60, 300)
                elif met == "conversions":
                    row[met] = random.randint(5, 50)
                else:
                    row[met] = random.randint(10, 100)

            data.append(row)

        return pd.DataFrame(data)

    def get_realtime_report(
        self,
        dimensions: List[str] = None,
        metrics: List[str] = None,
    ) -> pd.DataFrame:
        """
        Get realtime report.

        Args:
            dimensions: Dimension names
            metrics: Metric names

        Returns:
            DataFrame with realtime data
        """
        dimensions = dimensions or ["country"]
        metrics = metrics or ["activeUsers"]

        if not self._client:
            return self._mock_realtime(dimensions, metrics)

        try:
            from google.analytics.data_v1beta.types import (
                RunRealtimeReportRequest,
                Dimension,
                Metric,
            )

            request = RunRealtimeReportRequest(
                property=f"properties/{self.config.property_id}",
                dimensions=[Dimension(name=d) for d in dimensions],
                metrics=[Metric(name=m) for m in metrics],
            )

            response = self._client.run_realtime_report(request)

            rows = []
            for row in response.rows:
                row_data = {}
                for i, dim in enumerate(dimensions):
                    row_data[dim] = row.dimension_values[i].value
                for i, met in enumerate(metrics):
                    row_data[met] = float(row.metric_values[i].value)
                rows.append(row_data)

            return pd.DataFrame(rows)

        except Exception as e:
            logger.error(f"Realtime report failed: {e}")
            return self._mock_realtime(dimensions, metrics)

    def _mock_realtime(
        self,
        dimensions: List[str],
        metrics: List[str],
    ) -> pd.DataFrame:
        """Generate mock realtime data."""
        import random

        countries = ["United States", "United Kingdom", "Germany", "France", "Canada"]
        data = []

        for country in countries:
            row = {}
            for dim in dimensions:
                if dim == "country":
                    row[dim] = country
                else:
                    row[dim] = f"value"

            for met in metrics:
                row[met] = random.randint(10, 100)

            data.append(row)

        return pd.DataFrame(data)

    def get_traffic_sources(
        self,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """Get traffic sources report."""
        return self.run_report(
            dimensions=["sessionSource", "sessionMedium"],
            metrics=["sessions", "activeUsers", "conversions"],
            start_date=start_date,
            end_date=end_date,
        )

    def get_page_report(
        self,
        start_date: str,
        end_date: str,
        limit: int = 20,
    ) -> pd.DataFrame:
        """Get top pages report."""
        df = self.run_report(
            dimensions=["pagePath"],
            metrics=["screenPageViews", "averageSessionDuration", "bounceRate"],
            start_date=start_date,
            end_date=end_date,
        )
        return df.head(limit)

    def get_conversions(
        self,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """Get conversions by source."""
        return self.run_report(
            dimensions=["date", "sessionSource"],
            metrics=["conversions", "totalRevenue"],
            start_date=start_date,
            end_date=end_date,
        )
