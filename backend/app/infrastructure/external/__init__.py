"""
External Services Module

Clients for external APIs and services.
"""

from .weather_client import WeatherClient, WeatherData
from .economic_client import EconomicDataClient, EconomicIndicator
from .social_client import SocialMediaClient, SocialMetrics

__all__ = [
    "WeatherClient",
    "WeatherData",
    "EconomicDataClient",
    "EconomicIndicator",
    "SocialMediaClient",
    "SocialMetrics",
]
