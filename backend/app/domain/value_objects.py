"""
Domain Value Objects

Immutable value objects for the domain layer.
"""

from dataclasses import dataclass
from typing import Optional, Tuple
from datetime import date, datetime
from decimal import Decimal
import re


@dataclass(frozen=True)
class DateRange:
    """Immutable date range value object."""
    start_date: date
    end_date: date

    def __post_init__(self):
        if self.start_date > self.end_date:
            raise ValueError("start_date must be before or equal to end_date")

    @property
    def days(self) -> int:
        """Number of days in the range (inclusive)."""
        return (self.end_date - self.start_date).days + 1

    @property
    def weeks(self) -> float:
        """Number of weeks in the range."""
        return self.days / 7

    @property
    def months(self) -> float:
        """Approximate number of months in the range."""
        return self.days / 30.44

    def contains(self, d: date) -> bool:
        """Check if a date falls within the range."""
        return self.start_date <= d <= self.end_date

    def overlaps(self, other: "DateRange") -> bool:
        """Check if this range overlaps with another."""
        return self.start_date <= other.end_date and self.end_date >= other.start_date

    def intersection(self, other: "DateRange") -> Optional["DateRange"]:
        """Get the intersection with another range."""
        if not self.overlaps(other):
            return None
        return DateRange(
            start_date=max(self.start_date, other.start_date),
            end_date=min(self.end_date, other.end_date),
        )

    def to_tuple(self) -> Tuple[date, date]:
        return (self.start_date, self.end_date)

    @classmethod
    def last_n_days(cls, n: int) -> "DateRange":
        """Create a range for the last n days."""
        from datetime import timedelta
        end = date.today()
        start = end - timedelta(days=n - 1)
        return cls(start_date=start, end_date=end)

    @classmethod
    def this_month(cls) -> "DateRange":
        """Create a range for the current month."""
        today = date.today()
        start = today.replace(day=1)
        return cls(start_date=start, end_date=today)

    @classmethod
    def this_year(cls) -> "DateRange":
        """Create a range for the current year."""
        today = date.today()
        start = today.replace(month=1, day=1)
        return cls(start_date=start, end_date=today)


@dataclass(frozen=True)
class Money:
    """Immutable money value object."""
    amount: Decimal
    currency: str = "USD"

    def __post_init__(self):
        if not isinstance(self.amount, Decimal):
            object.__setattr__(self, "amount", Decimal(str(self.amount)))
        if len(self.currency) != 3:
            raise ValueError("Currency must be a 3-letter code")

    def __add__(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError(f"Cannot add {self.currency} and {other.currency}")
        return Money(amount=self.amount + other.amount, currency=self.currency)

    def __sub__(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError(f"Cannot subtract {self.currency} and {other.currency}")
        return Money(amount=self.amount - other.amount, currency=self.currency)

    def __mul__(self, factor: float) -> "Money":
        return Money(amount=self.amount * Decimal(str(factor)), currency=self.currency)

    def __truediv__(self, divisor: float) -> "Money":
        return Money(amount=self.amount / Decimal(str(divisor)), currency=self.currency)

    @property
    def is_positive(self) -> bool:
        return self.amount > 0

    @property
    def is_negative(self) -> bool:
        return self.amount < 0

    @property
    def is_zero(self) -> bool:
        return self.amount == 0

    def round_to_cents(self) -> "Money":
        """Round to 2 decimal places."""
        return Money(amount=self.amount.quantize(Decimal("0.01")), currency=self.currency)

    def format(self) -> str:
        """Format as currency string."""
        symbols = {"USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥"}
        symbol = symbols.get(self.currency, self.currency + " ")
        return f"{symbol}{self.amount:,.2f}"

    @classmethod
    def zero(cls, currency: str = "USD") -> "Money":
        return cls(amount=Decimal("0"), currency=currency)

    @classmethod
    def from_float(cls, amount: float, currency: str = "USD") -> "Money":
        return cls(amount=Decimal(str(amount)), currency=currency)


@dataclass(frozen=True)
class Percentage:
    """Immutable percentage value object."""
    value: float  # 0.5 represents 50%

    def __post_init__(self):
        if not 0 <= self.value <= 1:
            raise ValueError("Percentage must be between 0 and 1")

    @property
    def as_percent(self) -> float:
        """Get as percentage (0-100)."""
        return self.value * 100

    def format(self, decimals: int = 1) -> str:
        """Format as percentage string."""
        return f"{self.as_percent:.{decimals}f}%"

    def of(self, amount: float) -> float:
        """Calculate percentage of an amount."""
        return amount * self.value

    @classmethod
    def from_percent(cls, percent: float) -> "Percentage":
        """Create from percentage value (0-100)."""
        return cls(value=percent / 100)

    @classmethod
    def from_ratio(cls, numerator: float, denominator: float) -> "Percentage":
        """Create from ratio."""
        if denominator == 0:
            return cls(value=0)
        return cls(value=min(1, max(0, numerator / denominator)))


@dataclass(frozen=True)
class MetricValue:
    """Immutable metric value with metadata."""
    value: float
    metric_name: str
    timestamp: datetime
    unit: Optional[str] = None
    confidence: Optional[float] = None  # 0-1
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None

    @property
    def has_confidence_interval(self) -> bool:
        return self.lower_bound is not None and self.upper_bound is not None

    @property
    def interval_width(self) -> Optional[float]:
        if self.has_confidence_interval:
            return self.upper_bound - self.lower_bound
        return None

    def format(self, decimals: int = 2) -> str:
        """Format the value with unit."""
        formatted = f"{self.value:.{decimals}f}"
        if self.unit:
            formatted += f" {self.unit}"
        return formatted

    def with_confidence_interval(
        self, lower: float, upper: float, confidence: float = 0.95
    ) -> "MetricValue":
        """Create new MetricValue with confidence interval."""
        return MetricValue(
            value=self.value,
            metric_name=self.metric_name,
            timestamp=self.timestamp,
            unit=self.unit,
            confidence=confidence,
            lower_bound=lower,
            upper_bound=upper,
        )


@dataclass(frozen=True)
class EmailAddress:
    """Validated email address value object."""
    address: str

    def __post_init__(self):
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, self.address):
            raise ValueError(f"Invalid email address: {self.address}")

    @property
    def domain(self) -> str:
        return self.address.split("@")[1]

    @property
    def local_part(self) -> str:
        return self.address.split("@")[0]


@dataclass(frozen=True)
class GeoLocation:
    """Geographic location value object."""
    latitude: float
    longitude: float
    city: Optional[str] = None
    region: Optional[str] = None
    country: str = "US"

    def __post_init__(self):
        if not -90 <= self.latitude <= 90:
            raise ValueError("Latitude must be between -90 and 90")
        if not -180 <= self.longitude <= 180:
            raise ValueError("Longitude must be between -180 and 180")

    def distance_to(self, other: "GeoLocation") -> float:
        """Calculate distance in km using Haversine formula."""
        from math import radians, sin, cos, sqrt, atan2

        R = 6371  # Earth's radius in km

        lat1, lon1 = radians(self.latitude), radians(self.longitude)
        lat2, lon2 = radians(other.latitude), radians(other.longitude)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))

        return R * c

    @property
    def coordinates(self) -> Tuple[float, float]:
        return (self.latitude, self.longitude)
