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

try:
    from .redshift import RedshiftConnector, RedshiftConfig
    __all__.extend(["RedshiftConnector", "RedshiftConfig"])
except ImportError:
    pass

try:
    from .databricks import DatabricksConnector, DatabricksConfig
    __all__.extend(["DatabricksConnector", "DatabricksConfig"])
except ImportError:
    pass

# CRM Connectors
try:
    from .salesforce import SalesforceConnector, SalesforceConfig
    __all__.extend(["SalesforceConnector", "SalesforceConfig"])
except ImportError:
    pass

try:
    from .hubspot import HubSpotConnector, HubSpotConfig
    __all__.extend(["HubSpotConnector", "HubSpotConfig"])
except ImportError:
    pass

# Analytics Connectors
try:
    from .google_analytics import GoogleAnalyticsConnector, GoogleAnalyticsConfig
    __all__.extend(["GoogleAnalyticsConnector", "GoogleAnalyticsConfig"])
except ImportError:
    pass
