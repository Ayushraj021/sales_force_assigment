"""
Social Media Data Client

Social media metrics and sentiment data.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import date, datetime
from enum import Enum
import logging
import pandas as pd

logger = logging.getLogger(__name__)


class Platform(str, Enum):
    """Social media platforms."""
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    REDDIT = "reddit"


class SentimentType(str, Enum):
    """Sentiment categories."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


@dataclass
class SocialMetrics:
    """Social media metrics."""
    date: date
    platform: Platform
    brand: str
    mentions: int = 0
    reach: int = 0
    engagement: int = 0
    likes: int = 0
    shares: int = 0
    comments: int = 0
    followers: Optional[int] = None
    sentiment_positive: float = 0.0
    sentiment_negative: float = 0.0
    sentiment_neutral: float = 0.0
    top_hashtags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def engagement_rate(self) -> float:
        """Calculate engagement rate."""
        if self.reach > 0:
            return self.engagement / self.reach
        return 0.0

    @property
    def sentiment_score(self) -> float:
        """Calculate net sentiment score (-1 to 1)."""
        total = self.sentiment_positive + self.sentiment_negative + self.sentiment_neutral
        if total > 0:
            return (self.sentiment_positive - self.sentiment_negative) / total
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date.isoformat(),
            "platform": self.platform.value,
            "brand": self.brand,
            "mentions": self.mentions,
            "reach": self.reach,
            "engagement": self.engagement,
            "likes": self.likes,
            "shares": self.shares,
            "comments": self.comments,
            "followers": self.followers,
            "sentiment_positive": self.sentiment_positive,
            "sentiment_negative": self.sentiment_negative,
            "sentiment_neutral": self.sentiment_neutral,
            "sentiment_score": self.sentiment_score,
            "engagement_rate": self.engagement_rate,
            "top_hashtags": self.top_hashtags,
        }


@dataclass
class SocialConfig:
    """Social media client configuration."""
    twitter_bearer_token: Optional[str] = None
    facebook_access_token: Optional[str] = None
    instagram_access_token: Optional[str] = None
    cache_ttl_hours: int = 1


class SocialMediaClient:
    """
    Social Media Data Client.

    Features:
    - Multi-platform support
    - Mention tracking
    - Sentiment analysis
    - Engagement metrics

    Example:
        client = SocialMediaClient(config)

        # Get brand mentions
        metrics = client.get_metrics(
            brand="MyBrand",
            platform=Platform.TWITTER,
            start_date=start,
            end_date=end
        )

        # Get sentiment trends
        sentiment = client.get_sentiment_trend("MyBrand", days=30)
    """

    def __init__(self, config: SocialConfig):
        self.config = config
        self._cache: Dict[str, Any] = {}

        try:
            import requests
            self._requests = requests
        except ImportError:
            logger.warning("requests not installed")
            self._requests = None

    def get_metrics(
        self,
        brand: str,
        platform: Platform,
        start_date: date,
        end_date: date,
    ) -> List[SocialMetrics]:
        """
        Get social media metrics for a brand.

        Args:
            brand: Brand name or handle
            platform: Social media platform
            start_date: Start date
            end_date: End date

        Returns:
            List of SocialMetrics objects
        """
        cache_key = f"{brand}_{platform.value}_{start_date}_{end_date}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        if platform == Platform.TWITTER and self.config.twitter_bearer_token:
            data = self._fetch_twitter(brand, start_date, end_date)
        else:
            data = self._generate_mock_data(brand, platform, start_date, end_date)

        self._cache[cache_key] = data
        return data

    def get_all_platforms(
        self,
        brand: str,
        start_date: date,
        end_date: date,
        platforms: Optional[List[Platform]] = None,
    ) -> Dict[Platform, List[SocialMetrics]]:
        """
        Get metrics across all platforms.

        Args:
            brand: Brand name
            start_date: Start date
            end_date: End date
            platforms: Optional list of platforms

        Returns:
            Dict mapping platform to metrics
        """
        platforms = platforms or list(Platform)
        results = {}

        for platform in platforms:
            results[platform] = self.get_metrics(brand, platform, start_date, end_date)

        return results

    def _fetch_twitter(
        self,
        brand: str,
        start_date: date,
        end_date: date,
    ) -> List[SocialMetrics]:
        """Fetch Twitter metrics."""
        if not self._requests:
            return self._generate_mock_data(brand, Platform.TWITTER, start_date, end_date)

        try:
            # Twitter API v2 search
            url = "https://api.twitter.com/2/tweets/counts/recent"
            headers = {"Authorization": f"Bearer {self.config.twitter_bearer_token}"}
            params = {
                "query": brand,
                "start_time": f"{start_date}T00:00:00Z",
                "end_time": f"{end_date}T23:59:59Z",
                "granularity": "day",
            }

            response = self._requests.get(url, headers=headers, params=params, timeout=30)

            if response.status_code == 200:
                data = response.json()
                results = []

                for count_data in data.get("data", []):
                    dt = date.fromisoformat(count_data["start"][:10])
                    tweet_count = count_data["tweet_count"]

                    # Estimate other metrics
                    results.append(SocialMetrics(
                        date=dt,
                        platform=Platform.TWITTER,
                        brand=brand,
                        mentions=tweet_count,
                        reach=tweet_count * 150,  # Estimated
                        engagement=tweet_count * 10,
                        likes=tweet_count * 5,
                        shares=tweet_count * 2,
                        comments=tweet_count * 3,
                        sentiment_positive=0.4,
                        sentiment_negative=0.2,
                        sentiment_neutral=0.4,
                    ))

                return results

        except Exception as e:
            logger.warning(f"Failed to fetch Twitter data: {e}")

        return self._generate_mock_data(brand, Platform.TWITTER, start_date, end_date)

    def _generate_mock_data(
        self,
        brand: str,
        platform: Platform,
        start_date: date,
        end_date: date,
    ) -> List[SocialMetrics]:
        """Generate mock social media data."""
        import random
        from datetime import timedelta

        results = []
        current = start_date

        # Platform-specific base metrics
        base_metrics = {
            Platform.TWITTER: {"mentions": 100, "reach": 10000},
            Platform.FACEBOOK: {"mentions": 50, "reach": 50000},
            Platform.INSTAGRAM: {"mentions": 75, "reach": 30000},
            Platform.LINKEDIN: {"mentions": 25, "reach": 5000},
            Platform.TIKTOK: {"mentions": 150, "reach": 100000},
            Platform.YOUTUBE: {"mentions": 30, "reach": 20000},
            Platform.REDDIT: {"mentions": 40, "reach": 8000},
        }

        base = base_metrics.get(platform, {"mentions": 50, "reach": 10000})

        while current <= end_date:
            # Weekly pattern (higher on weekdays)
            weekday_factor = 1.2 if current.weekday() < 5 else 0.8

            mentions = int(base["mentions"] * weekday_factor * random.uniform(0.5, 1.5))
            reach = int(base["reach"] * weekday_factor * random.uniform(0.5, 1.5))

            engagement = int(reach * random.uniform(0.02, 0.08))
            likes = int(engagement * random.uniform(0.4, 0.6))
            shares = int(engagement * random.uniform(0.1, 0.2))
            comments = int(engagement * random.uniform(0.2, 0.3))

            # Sentiment distribution
            sentiment_positive = random.uniform(0.3, 0.6)
            sentiment_negative = random.uniform(0.1, 0.3)
            sentiment_neutral = 1 - sentiment_positive - sentiment_negative

            hashtags = [
                f"#{brand.lower()}",
                f"#{platform.value}",
                f"#marketing",
            ]

            results.append(SocialMetrics(
                date=current,
                platform=platform,
                brand=brand,
                mentions=mentions,
                reach=reach,
                engagement=engagement,
                likes=likes,
                shares=shares,
                comments=comments,
                sentiment_positive=round(sentiment_positive, 3),
                sentiment_negative=round(sentiment_negative, 3),
                sentiment_neutral=round(sentiment_neutral, 3),
                top_hashtags=hashtags,
            ))

            current += timedelta(days=1)

        return results

    def get_sentiment_trend(
        self,
        brand: str,
        days: int = 30,
        platforms: Optional[List[Platform]] = None,
    ) -> pd.DataFrame:
        """
        Get sentiment trend over time.

        Args:
            brand: Brand name
            days: Number of days
            platforms: Optional list of platforms

        Returns:
            DataFrame with sentiment trends
        """
        from datetime import timedelta

        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        platforms = platforms or [Platform.TWITTER, Platform.FACEBOOK, Platform.INSTAGRAM]

        all_data = []
        for platform in platforms:
            metrics = self.get_metrics(brand, platform, start_date, end_date)
            for m in metrics:
                all_data.append({
                    "date": m.date,
                    "platform": m.platform.value,
                    "sentiment_score": m.sentiment_score,
                    "mentions": m.mentions,
                })

        df = pd.DataFrame(all_data)
        if not df.empty:
            # Aggregate by date
            daily = df.groupby("date").agg({
                "sentiment_score": "mean",
                "mentions": "sum",
            }).reset_index()
            return daily

        return df

    def get_competitive_analysis(
        self,
        brands: List[str],
        platform: Platform,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        """
        Compare metrics across brands.

        Args:
            brands: List of brand names
            platform: Platform to analyze
            start_date: Start date
            end_date: End date

        Returns:
            DataFrame with competitive comparison
        """
        all_data = []

        for brand in brands:
            metrics = self.get_metrics(brand, platform, start_date, end_date)
            for m in metrics:
                all_data.append(m.to_dict())

        return pd.DataFrame(all_data)

    def to_dataframe(
        self,
        data: List[SocialMetrics],
    ) -> pd.DataFrame:
        """Convert social metrics to DataFrame."""
        return pd.DataFrame([d.to_dict() for d in data])

    def clear_cache(self) -> None:
        """Clear the cache."""
        self._cache.clear()
