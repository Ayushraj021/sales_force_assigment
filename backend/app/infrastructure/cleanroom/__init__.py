"""
Data Clean Room Module

Privacy-preserving data collaboration across organizations.
"""

from .clean_room import (
    CleanRoom,
    CleanRoomConfig,
    CleanRoomQuery,
    QueryResult,
)
from .providers import (
    AWSCleanRoomProvider,
    SnowflakeCleanRoomProvider,
    GoogleAdsDataHubProvider,
)

__all__ = [
    "CleanRoom",
    "CleanRoomConfig",
    "CleanRoomQuery",
    "QueryResult",
    "AWSCleanRoomProvider",
    "SnowflakeCleanRoomProvider",
    "GoogleAdsDataHubProvider",
]
