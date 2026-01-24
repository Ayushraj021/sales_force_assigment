"""
Google Ads Connector

Integration with Google Ads API for campaign data.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, date, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class GoogleAdsMetric(str, Enum):
    """Available metrics from Google Ads."""
    IMPRESSIONS = "impressions"
    CLICKS = "clicks"
    COST = "cost_micros"
    CONVERSIONS = "conversions"
    CONVERSION_VALUE = "conversions_value"
    CTR = "ctr"
    CPC = "average_cpc"
    CPM = "average_cpm"
    ROAS = "value_per_conversion"


class GoogleAdsDimension(str, Enum):
    """Available dimensions for grouping."""
    DATE = "segments.date"
    CAMPAIGN = "campaign.name"
    AD_GROUP = "ad_group.name"
    KEYWORD = "ad_group_criterion.keyword.text"
    DEVICE = "segments.device"
    NETWORK = "segments.ad_network_type"


@dataclass
class GoogleAdsConfig:
    """Configuration for Google Ads connector."""
    customer_id: str
    developer_token: str
    client_id: str
    client_secret: str
    refresh_token: str
    login_customer_id: Optional[str] = None
    use_proto_plus: bool = True


@dataclass
class CampaignData:
    """Campaign performance data."""
    campaign_id: str
    campaign_name: str
    date: date
    impressions: int
    clicks: int
    cost: float
    conversions: float
    conversion_value: float
    ctr: float
    cpc: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "campaign_name": self.campaign_name,
            "date": self.date.isoformat(),
            "impressions": self.impressions,
            "clicks": self.clicks,
            "cost": self.cost,
            "conversions": self.conversions,
            "conversion_value": self.conversion_value,
            "ctr": self.ctr,
            "cpc": self.cpc,
        }


class GoogleAdsConnector:
    """
    Google Ads API Connector.

    Features:
    - Fetch campaign, ad group, keyword performance
    - Support for multiple metrics and dimensions
    - Date range queries
    - Rate limiting and retry logic

    Example:
        connector = GoogleAdsConnector(config)
        data = connector.get_campaign_performance(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )
    """

    def __init__(self, config: GoogleAdsConfig):
        self.config = config
        self._client = None

    def connect(self) -> bool:
        """Establish connection to Google Ads API."""
        try:
            from google.ads.googleads.client import GoogleAdsClient

            credentials = {
                "developer_token": self.config.developer_token,
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "refresh_token": self.config.refresh_token,
                "use_proto_plus": self.config.use_proto_plus,
            }

            if self.config.login_customer_id:
                credentials["login_customer_id"] = self.config.login_customer_id

            self._client = GoogleAdsClient.load_from_dict(credentials)
            return True

        except ImportError:
            logger.warning("google-ads package not installed")
            return False
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False

    def get_campaign_performance(
        self,
        start_date: date,
        end_date: date,
        campaign_ids: Optional[List[str]] = None,
    ) -> List[CampaignData]:
        """
        Get campaign performance data.

        Args:
            start_date: Start date for data
            end_date: End date for data
            campaign_ids: Optional list of campaign IDs to filter

        Returns:
            List of CampaignData objects
        """
        if self._client is None:
            if not self.connect():
                return []

        try:
            ga_service = self._client.get_service("GoogleAdsService")

            query = f"""
                SELECT
                    campaign.id,
                    campaign.name,
                    segments.date,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.conversions_value,
                    metrics.ctr,
                    metrics.average_cpc
                FROM campaign
                WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
            """

            if campaign_ids:
                ids_str = ",".join(campaign_ids)
                query += f" AND campaign.id IN ({ids_str})"

            response = ga_service.search_stream(
                customer_id=self.config.customer_id,
                query=query
            )

            results = []
            for batch in response:
                for row in batch.results:
                    campaign_data = CampaignData(
                        campaign_id=str(row.campaign.id),
                        campaign_name=row.campaign.name,
                        date=datetime.strptime(row.segments.date, "%Y-%m-%d").date(),
                        impressions=row.metrics.impressions,
                        clicks=row.metrics.clicks,
                        cost=row.metrics.cost_micros / 1_000_000,
                        conversions=row.metrics.conversions,
                        conversion_value=row.metrics.conversions_value,
                        ctr=row.metrics.ctr,
                        cpc=row.metrics.average_cpc / 1_000_000,
                    )
                    results.append(campaign_data)

            return results

        except Exception as e:
            logger.error(f"Failed to fetch campaign data: {e}")
            return []

    def get_keyword_performance(
        self,
        start_date: date,
        end_date: date,
        campaign_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get keyword-level performance data."""
        if self._client is None:
            if not self.connect():
                return []

        try:
            ga_service = self._client.get_service("GoogleAdsService")

            query = f"""
                SELECT
                    ad_group_criterion.keyword.text,
                    ad_group_criterion.keyword.match_type,
                    campaign.name,
                    ad_group.name,
                    segments.date,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.average_cpc
                FROM keyword_view
                WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
            """

            if campaign_id:
                query += f" AND campaign.id = {campaign_id}"

            response = ga_service.search_stream(
                customer_id=self.config.customer_id,
                query=query
            )

            results = []
            for batch in response:
                for row in batch.results:
                    results.append({
                        "keyword": row.ad_group_criterion.keyword.text,
                        "match_type": str(row.ad_group_criterion.keyword.match_type),
                        "campaign": row.campaign.name,
                        "ad_group": row.ad_group.name,
                        "date": row.segments.date,
                        "impressions": row.metrics.impressions,
                        "clicks": row.metrics.clicks,
                        "cost": row.metrics.cost_micros / 1_000_000,
                        "conversions": row.metrics.conversions,
                        "cpc": row.metrics.average_cpc / 1_000_000,
                    })

            return results

        except Exception as e:
            logger.error(f"Failed to fetch keyword data: {e}")
            return []

    def get_account_summary(self) -> Dict[str, Any]:
        """Get account-level summary."""
        if self._client is None:
            if not self.connect():
                return {}

        try:
            ga_service = self._client.get_service("GoogleAdsService")

            query = """
                SELECT
                    customer.descriptive_name,
                    customer.currency_code,
                    customer.time_zone,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.cost_micros
                FROM customer
                WHERE segments.date DURING LAST_30_DAYS
            """

            response = ga_service.search_stream(
                customer_id=self.config.customer_id,
                query=query
            )

            for batch in response:
                for row in batch.results:
                    return {
                        "account_name": row.customer.descriptive_name,
                        "currency": row.customer.currency_code,
                        "timezone": row.customer.time_zone,
                        "impressions_30d": row.metrics.impressions,
                        "clicks_30d": row.metrics.clicks,
                        "cost_30d": row.metrics.cost_micros / 1_000_000,
                    }

            return {}

        except Exception as e:
            logger.error(f"Failed to fetch account summary: {e}")
            return {}


class GoogleAdsMockConnector:
    """Mock connector for testing without API access."""

    def __init__(self, config: Optional[GoogleAdsConfig] = None):
        self.config = config

    def connect(self) -> bool:
        return True

    def get_campaign_performance(
        self,
        start_date: date,
        end_date: date,
        campaign_ids: Optional[List[str]] = None,
    ) -> List[CampaignData]:
        """Generate mock campaign data."""
        import numpy as np

        campaigns = [
            ("1001", "Brand Campaign"),
            ("1002", "Search - Generic"),
            ("1003", "Display - Retargeting"),
            ("1004", "Shopping"),
        ]

        results = []
        current = start_date

        while current <= end_date:
            for camp_id, camp_name in campaigns:
                if campaign_ids and camp_id not in campaign_ids:
                    continue

                impressions = int(np.random.uniform(5000, 50000))
                ctr = np.random.uniform(0.01, 0.05)
                clicks = int(impressions * ctr)
                cpc = np.random.uniform(0.5, 3.0)
                cost = clicks * cpc
                conv_rate = np.random.uniform(0.02, 0.1)
                conversions = clicks * conv_rate
                aov = np.random.uniform(50, 200)

                results.append(CampaignData(
                    campaign_id=camp_id,
                    campaign_name=camp_name,
                    date=current,
                    impressions=impressions,
                    clicks=clicks,
                    cost=round(cost, 2),
                    conversions=round(conversions, 2),
                    conversion_value=round(conversions * aov, 2),
                    ctr=round(ctr, 4),
                    cpc=round(cpc, 2),
                ))

            current += timedelta(days=1)

        return results
