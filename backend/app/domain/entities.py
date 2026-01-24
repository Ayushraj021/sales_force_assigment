"""
Domain Entities

Core business entities for marketing analytics.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, date
from enum import Enum
import uuid


class ChannelType(str, Enum):
    """Marketing channel types."""
    PAID_SEARCH = "paid_search"
    PAID_SOCIAL = "paid_social"
    DISPLAY = "display"
    VIDEO = "video"
    EMAIL = "email"
    AFFILIATE = "affiliate"
    ORGANIC_SEARCH = "organic_search"
    ORGANIC_SOCIAL = "organic_social"
    DIRECT = "direct"
    REFERRAL = "referral"
    TV = "tv"
    RADIO = "radio"
    PRINT = "print"
    OOH = "out_of_home"


class CampaignStatus(str, Enum):
    """Campaign status."""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ForecastStatus(str, Enum):
    """Forecast status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Channel:
    """Marketing channel entity."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    channel_type: ChannelType = ChannelType.PAID_SEARCH
    platform: Optional[str] = None  # e.g., "Google", "Meta", "TikTok"
    is_active: bool = True
    cost_model: str = "cpc"  # cpc, cpm, cpa, flat
    default_adstock_decay: float = 0.7
    default_saturation_lambda: float = 0.001
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "channel_type": self.channel_type.value,
            "platform": self.platform,
            "is_active": self.is_active,
            "cost_model": self.cost_model,
            "default_adstock_decay": self.default_adstock_decay,
            "default_saturation_lambda": self.default_saturation_lambda,
            "metadata": self.metadata,
        }


@dataclass
class Campaign:
    """Marketing campaign entity."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    channel_id: str = ""
    status: CampaignStatus = CampaignStatus.DRAFT
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget: float = 0.0
    daily_budget: Optional[float] = None
    target_audience: Optional[str] = None
    objective: str = "awareness"  # awareness, consideration, conversion
    kpis: Dict[str, float] = field(default_factory=dict)
    creatives: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    organization_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def is_active(self) -> bool:
        return self.status == CampaignStatus.ACTIVE

    @property
    def duration_days(self) -> Optional[int]:
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "channel_id": self.channel_id,
            "status": self.status.value,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "budget": self.budget,
            "daily_budget": self.daily_budget,
            "target_audience": self.target_audience,
            "objective": self.objective,
            "kpis": self.kpis,
        }


@dataclass
class MarketingData:
    """Marketing performance data point."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    date: date = field(default_factory=date.today)
    channel_id: str = ""
    campaign_id: Optional[str] = None
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    spend: float = 0.0
    revenue: float = 0.0
    reach: Optional[int] = None
    frequency: Optional[float] = None
    video_views: Optional[int] = None
    engagement: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def ctr(self) -> float:
        """Click-through rate."""
        return self.clicks / self.impressions if self.impressions > 0 else 0.0

    @property
    def cvr(self) -> float:
        """Conversion rate."""
        return self.conversions / self.clicks if self.clicks > 0 else 0.0

    @property
    def cpc(self) -> float:
        """Cost per click."""
        return self.spend / self.clicks if self.clicks > 0 else 0.0

    @property
    def cpa(self) -> float:
        """Cost per acquisition."""
        return self.spend / self.conversions if self.conversions > 0 else 0.0

    @property
    def roas(self) -> float:
        """Return on ad spend."""
        return self.revenue / self.spend if self.spend > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "date": self.date.isoformat(),
            "channel_id": self.channel_id,
            "campaign_id": self.campaign_id,
            "impressions": self.impressions,
            "clicks": self.clicks,
            "conversions": self.conversions,
            "spend": self.spend,
            "revenue": self.revenue,
            "ctr": self.ctr,
            "cvr": self.cvr,
            "cpc": self.cpc,
            "cpa": self.cpa,
            "roas": self.roas,
        }


@dataclass
class TimeSeries:
    """Time series data entity."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    metric: str = "sales"
    granularity: str = "daily"  # hourly, daily, weekly, monthly
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    values: List[float] = field(default_factory=list)
    dates: List[date] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def length(self) -> int:
        return len(self.values)

    @property
    def mean(self) -> float:
        return sum(self.values) / len(self.values) if self.values else 0.0

    @property
    def std(self) -> float:
        if not self.values:
            return 0.0
        mean = self.mean
        variance = sum((x - mean) ** 2 for x in self.values) / len(self.values)
        return variance ** 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "metric": self.metric,
            "granularity": self.granularity,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "length": self.length,
            "mean": self.mean,
            "std": self.std,
        }


@dataclass
class Forecast:
    """Forecast entity."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    model_type: str = "prophet"  # prophet, arima, ensemble, neural
    status: ForecastStatus = ForecastStatus.PENDING
    target_metric: str = "sales"
    horizon: int = 30  # Forecast horizon in days
    confidence_level: float = 0.95
    actual_values: List[float] = field(default_factory=list)
    predicted_values: List[float] = field(default_factory=list)
    lower_bounds: List[float] = field(default_factory=list)
    upper_bounds: List[float] = field(default_factory=list)
    dates: List[date] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)  # mape, rmse, etc.
    model_params: Dict[str, Any] = field(default_factory=dict)
    organization_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    @property
    def mape(self) -> Optional[float]:
        return self.metrics.get("mape")

    @property
    def rmse(self) -> Optional[float]:
        return self.metrics.get("rmse")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "model_type": self.model_type,
            "status": self.status.value,
            "target_metric": self.target_metric,
            "horizon": self.horizon,
            "confidence_level": self.confidence_level,
            "metrics": self.metrics,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
