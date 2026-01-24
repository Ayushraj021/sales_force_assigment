"""
Data Connectors Module

Integrations with ad platforms, data warehouses, and analytics tools.
"""

from .google_ads import (
    GoogleAdsConnector,
    GoogleAdsConfig,
    GoogleAdsMockConnector,
    CampaignData as GoogleAdsCampaignData,
)
from .meta_ads import (
    MetaAdsConnector,
    MetaAdsConfig,
    MetaAdsMockConnector,
    MetaCampaignData,
)

__all__ = [
    # Google Ads
    "GoogleAdsConnector",
    "GoogleAdsConfig",
    "GoogleAdsMockConnector",
    "GoogleAdsCampaignData",
    # Meta Ads
    "MetaAdsConnector",
    "MetaAdsConfig",
    "MetaAdsMockConnector",
    "MetaCampaignData",
]

# Optional connectors
try:
    from .snowflake import SnowflakeConnector, SnowflakeConfig
    __all__.extend(["SnowflakeConnector", "SnowflakeConfig"])
except ImportError:
    pass

try:
    from .bigquery import BigQueryConnector, BigQueryConfig
    __all__.extend(["BigQueryConnector", "BigQueryConfig"])
except ImportError:
    pass
