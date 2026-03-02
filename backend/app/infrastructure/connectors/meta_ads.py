"""
Meta (Facebook/Instagram) Ads Connector

Integration with Meta Marketing API.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, date, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class MetaAdsMetric(str, Enum):
    """Available metrics from Meta Ads."""
    IMPRESSIONS = "impressions"
    CLICKS = "clicks"
    SPEND = "spend"
    REACH = "reach"
    FREQUENCY = "frequency"
    CPM = "cpm"
    CPC = "cpc"
    CTR = "ctr"
    CONVERSIONS = "actions"
    CONVERSION_VALUE = "action_values"
    ROAS = "purchase_roas"


class MetaAdsLevel(str, Enum):
    """Reporting levels."""
    ACCOUNT = "account"
    CAMPAIGN = "campaign"
    ADSET = "adset"
    AD = "ad"


@dataclass
class MetaAdsConfig:
    """Configuration for Meta Ads connector."""
    app_id: str
    app_secret: str
    access_token: str
    ad_account_id: str


@dataclass
class MetaCampaignData:
    """Campaign performance data from Meta."""
    campaign_id: str
    campaign_name: str
    objective: str
    date_start: date
    date_stop: date
    impressions: int
    clicks: int
    spend: float
    reach: int
    cpm: float
    cpc: float
    ctr: float
    conversions: Dict[str, int] = field(default_factory=dict)
    conversion_value: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "campaign_name": self.campaign_name,
            "objective": self.objective,
            "date_start": self.date_start.isoformat(),
            "date_stop": self.date_stop.isoformat(),
            "impressions": self.impressions,
            "clicks": self.clicks,
            "spend": self.spend,
            "reach": self.reach,
            "cpm": self.cpm,
            "cpc": self.cpc,
            "ctr": self.ctr,
            "conversions": self.conversions,
            "conversion_value": self.conversion_value,
        }


class MetaAdsConnector:
    """
    Meta (Facebook/Instagram) Ads Connector.

    Features:
    - Campaign, ad set, and ad level reporting
    - Conversion tracking with custom events
    - Audience insights
    - Creative performance

    Example:
        connector = MetaAdsConnector(config)
        data = connector.get_campaign_insights(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )
    """

    def __init__(self, config: MetaAdsConfig):
        self.config = config
        self._api = None

    def connect(self) -> bool:
        """Initialize Meta Ads API connection."""
        try:
            from facebook_business.api import FacebookAdsApi
            from facebook_business.adobjects.adaccount import AdAccount

            FacebookAdsApi.init(
                self.config.app_id,
                self.config.app_secret,
                self.config.access_token,
            )

            self._api = AdAccount(f"act_{self.config.ad_account_id}")
            return True

        except ImportError:
            logger.warning("facebook-business package not installed")
            return False
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False

    def get_campaign_insights(
        self,
        start_date: date,
        end_date: date,
        campaign_ids: Optional[List[str]] = None,
        breakdowns: Optional[List[str]] = None,
    ) -> List[MetaCampaignData]:
        """
        Get campaign-level insights.

        Args:
            start_date: Start date
            end_date: End date
            campaign_ids: Optional campaign ID filter
            breakdowns: Optional breakdowns (age, gender, device, etc.)

        Returns:
            List of MetaCampaignData
        """
        if self._api is None:
            if not self.connect():
                return []

        try:
            from facebook_business.adobjects.adaccount import AdAccount

            fields = [
                "campaign_id",
                "campaign_name",
                "objective",
                "impressions",
                "clicks",
                "spend",
                "reach",
                "cpm",
                "cpc",
                "ctr",
                "actions",
                "action_values",
            ]

            params = {
                "time_range": {
                    "since": start_date.isoformat(),
                    "until": end_date.isoformat(),
                },
                "level": "campaign",
            }

            if campaign_ids:
                params["filtering"] = [
                    {"field": "campaign.id", "operator": "IN", "value": campaign_ids}
                ]

            if breakdowns:
                params["breakdowns"] = breakdowns

            insights = self._api.get_insights(fields=fields, params=params)

            results = []
            for insight in insights:
                # Parse actions (conversions)
                conversions = {}
                if "actions" in insight:
                    for action in insight["actions"]:
                        conversions[action["action_type"]] = int(action["value"])

                # Parse conversion value
                conv_value = 0.0
                if "action_values" in insight:
                    for action in insight["action_values"]:
                        if action["action_type"] == "purchase":
                            conv_value = float(action["value"])

                results.append(MetaCampaignData(
                    campaign_id=insight["campaign_id"],
                    campaign_name=insight["campaign_name"],
                    objective=insight.get("objective", ""),
                    date_start=start_date,
                    date_stop=end_date,
                    impressions=int(insight.get("impressions", 0)),
                    clicks=int(insight.get("clicks", 0)),
                    spend=float(insight.get("spend", 0)),
                    reach=int(insight.get("reach", 0)),
                    cpm=float(insight.get("cpm", 0)),
                    cpc=float(insight.get("cpc", 0)) if insight.get("cpc") else 0,
                    ctr=float(insight.get("ctr", 0)),
                    conversions=conversions,
                    conversion_value=conv_value,
                ))

            return results

        except Exception as e:
            logger.error(f"Failed to fetch campaign insights: {e}")
            return []

    def get_adset_insights(
        self,
        start_date: date,
        end_date: date,
        campaign_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get ad set level insights."""
        if self._api is None:
            if not self.connect():
                return []

        try:
            fields = [
                "adset_id",
                "adset_name",
                "campaign_id",
                "impressions",
                "clicks",
                "spend",
                "reach",
                "cpm",
                "cpc",
                "ctr",
            ]

            params = {
                "time_range": {
                    "since": start_date.isoformat(),
                    "until": end_date.isoformat(),
                },
                "level": "adset",
            }

            if campaign_id:
                params["filtering"] = [
                    {"field": "campaign.id", "operator": "EQUAL", "value": campaign_id}
                ]

            insights = self._api.get_insights(fields=fields, params=params)

            return [dict(insight) for insight in insights]

        except Exception as e:
            logger.error(f"Failed to fetch adset insights: {e}")
            return []

    def get_audience_insights(
        self,
        campaign_id: str,
        start_date: date,
        end_date: date,
    ) -> Dict[str, Any]:
        """Get audience breakdown for a campaign."""
        if self._api is None:
            if not self.connect():
                return {}

        try:
            fields = ["impressions", "clicks", "spend", "reach"]

            results = {}

            # Age breakdown
            params = {
                "time_range": {
                    "since": start_date.isoformat(),
                    "until": end_date.isoformat(),
                },
                "level": "campaign",
                "breakdowns": ["age"],
                "filtering": [
                    {"field": "campaign.id", "operator": "EQUAL", "value": campaign_id}
                ],
            }

            insights = self._api.get_insights(fields=fields, params=params)
            results["by_age"] = [dict(i) for i in insights]

            # Gender breakdown
            params["breakdowns"] = ["gender"]
            insights = self._api.get_insights(fields=fields, params=params)
            results["by_gender"] = [dict(i) for i in insights]

            # Device breakdown
            params["breakdowns"] = ["device_platform"]
            insights = self._api.get_insights(fields=fields, params=params)
            results["by_device"] = [dict(i) for i in insights]

            return results

        except Exception as e:
            logger.error(f"Failed to fetch audience insights: {e}")
            return {}


class MetaAdsMockConnector:
    """Mock connector for testing."""

    def __init__(self, config: Optional[MetaAdsConfig] = None):
        self.config = config

    def connect(self) -> bool:
        return True

    def get_campaign_insights(
        self,
        start_date: date,
        end_date: date,
        campaign_ids: Optional[List[str]] = None,
        breakdowns: Optional[List[str]] = None,
    ) -> List[MetaCampaignData]:
        """Generate mock campaign data."""
        import numpy as np

        campaigns = [
            ("fb_001", "Awareness - Brand", "BRAND_AWARENESS"),
            ("fb_002", "Conversions - Retargeting", "CONVERSIONS"),
            ("fb_003", "Traffic - Blog", "LINK_CLICKS"),
            ("fb_004", "Sales - Catalog", "PRODUCT_CATALOG_SALES"),
        ]

        results = []

        for camp_id, camp_name, objective in campaigns:
            if campaign_ids and camp_id not in campaign_ids:
                continue

            impressions = int(np.random.uniform(100000, 500000))
            reach = int(impressions * np.random.uniform(0.6, 0.9))
            ctr = np.random.uniform(0.005, 0.03)
            clicks = int(impressions * ctr)
            cpm = np.random.uniform(5, 15)
            spend = (impressions / 1000) * cpm
            cpc = spend / clicks if clicks > 0 else 0

            conversions = {}
            conv_value = 0.0
            if objective == "CONVERSIONS":
                conversions = {
                    "purchase": int(clicks * np.random.uniform(0.02, 0.08)),
                    "add_to_cart": int(clicks * np.random.uniform(0.05, 0.15)),
                    "view_content": int(clicks * np.random.uniform(0.3, 0.6)),
                }
                conv_value = conversions.get("purchase", 0) * np.random.uniform(50, 150)

            results.append(MetaCampaignData(
                campaign_id=camp_id,
                campaign_name=camp_name,
                objective=objective,
                date_start=start_date,
                date_stop=end_date,
                impressions=impressions,
                clicks=clicks,
                spend=round(spend, 2),
                reach=reach,
                cpm=round(cpm, 2),
                cpc=round(cpc, 2),
                ctr=round(ctr, 4),
                conversions=conversions,
                conversion_value=round(conv_value, 2),
            ))

        return results
