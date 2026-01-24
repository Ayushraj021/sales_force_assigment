"""
Economic Data Client

External economic indicators for demand forecasting.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import date
from enum import Enum
import logging
import pandas as pd

logger = logging.getLogger(__name__)


class IndicatorType(str, Enum):
    """Types of economic indicators."""
    GDP = "gdp"
    UNEMPLOYMENT = "unemployment"
    INFLATION = "inflation"
    CPI = "cpi"
    CONSUMER_CONFIDENCE = "consumer_confidence"
    RETAIL_SALES = "retail_sales"
    HOUSING_STARTS = "housing_starts"
    INTEREST_RATE = "interest_rate"
    EXCHANGE_RATE = "exchange_rate"
    STOCK_INDEX = "stock_index"


@dataclass
class EconomicIndicator:
    """Economic indicator data point."""
    indicator_type: IndicatorType
    date: date
    value: float
    country: str = "US"
    unit: str = ""
    period: str = "monthly"  # daily, weekly, monthly, quarterly, annual
    source: str = ""
    seasonally_adjusted: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "indicator_type": self.indicator_type.value,
            "date": self.date.isoformat(),
            "value": self.value,
            "country": self.country,
            "unit": self.unit,
            "period": self.period,
            "source": self.source,
            "seasonally_adjusted": self.seasonally_adjusted,
        }


@dataclass
class EconomicConfig:
    """Economic data client configuration."""
    fred_api_key: Optional[str] = None  # Federal Reserve Economic Data
    alpha_vantage_key: Optional[str] = None  # Alpha Vantage
    cache_ttl_hours: int = 24


class EconomicDataClient:
    """
    Economic Data Client.

    Features:
    - FRED API integration
    - Multiple indicator support
    - Country-specific data
    - Caching

    Example:
        client = EconomicDataClient(config)

        # Get CPI data
        cpi = client.get_indicator(IndicatorType.CPI, start_date, end_date)

        # Get multiple indicators
        data = client.get_indicators(
            [IndicatorType.GDP, IndicatorType.UNEMPLOYMENT],
            start_date,
            end_date
        )
    """

    # FRED series IDs for common indicators
    FRED_SERIES = {
        IndicatorType.GDP: "GDP",
        IndicatorType.UNEMPLOYMENT: "UNRATE",
        IndicatorType.INFLATION: "T10YIE",
        IndicatorType.CPI: "CPIAUCSL",
        IndicatorType.CONSUMER_CONFIDENCE: "UMCSENT",
        IndicatorType.RETAIL_SALES: "RSXFS",
        IndicatorType.HOUSING_STARTS: "HOUST",
        IndicatorType.INTEREST_RATE: "FEDFUNDS",
    }

    def __init__(self, config: EconomicConfig):
        self.config = config
        self._cache: Dict[str, Any] = {}

        try:
            import requests
            self._requests = requests
        except ImportError:
            logger.warning("requests not installed")
            self._requests = None

    def get_indicator(
        self,
        indicator_type: IndicatorType,
        start_date: date,
        end_date: date,
        country: str = "US",
    ) -> List[EconomicIndicator]:
        """
        Get a single economic indicator.

        Args:
            indicator_type: Type of indicator
            start_date: Start date
            end_date: End date
            country: Country code

        Returns:
            List of EconomicIndicator objects
        """
        cache_key = f"{indicator_type.value}_{start_date}_{end_date}_{country}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        if self.config.fred_api_key and country == "US":
            data = self._fetch_fred(indicator_type, start_date, end_date)
        else:
            data = self._generate_mock_data(indicator_type, start_date, end_date, country)

        self._cache[cache_key] = data
        return data

    def get_indicators(
        self,
        indicators: List[IndicatorType],
        start_date: date,
        end_date: date,
        country: str = "US",
    ) -> Dict[IndicatorType, List[EconomicIndicator]]:
        """
        Get multiple economic indicators.

        Args:
            indicators: List of indicator types
            start_date: Start date
            end_date: End date
            country: Country code

        Returns:
            Dict mapping indicator type to data
        """
        results = {}
        for indicator in indicators:
            results[indicator] = self.get_indicator(indicator, start_date, end_date, country)
        return results

    def _fetch_fred(
        self,
        indicator_type: IndicatorType,
        start_date: date,
        end_date: date,
    ) -> List[EconomicIndicator]:
        """Fetch from FRED API."""
        if not self._requests:
            return self._generate_mock_data(indicator_type, start_date, end_date, "US")

        series_id = self.FRED_SERIES.get(indicator_type)
        if not series_id:
            return self._generate_mock_data(indicator_type, start_date, end_date, "US")

        try:
            url = "https://api.stlouisfed.org/fred/series/observations"
            params = {
                "series_id": series_id,
                "api_key": self.config.fred_api_key,
                "file_type": "json",
                "observation_start": start_date.isoformat(),
                "observation_end": end_date.isoformat(),
            }
            response = self._requests.get(url, params=params, timeout=30)

            if response.status_code == 200:
                data = response.json()
                results = []
                for obs in data.get("observations", []):
                    try:
                        value = float(obs["value"])
                        results.append(EconomicIndicator(
                            indicator_type=indicator_type,
                            date=date.fromisoformat(obs["date"]),
                            value=value,
                            country="US",
                            source="FRED",
                            unit=self._get_unit(indicator_type),
                        ))
                    except (ValueError, KeyError):
                        continue
                return results

        except Exception as e:
            logger.warning(f"Failed to fetch from FRED: {e}")

        return self._generate_mock_data(indicator_type, start_date, end_date, "US")

    def _get_unit(self, indicator_type: IndicatorType) -> str:
        """Get unit for indicator type."""
        units = {
            IndicatorType.GDP: "Billions USD",
            IndicatorType.UNEMPLOYMENT: "%",
            IndicatorType.INFLATION: "%",
            IndicatorType.CPI: "Index",
            IndicatorType.CONSUMER_CONFIDENCE: "Index",
            IndicatorType.RETAIL_SALES: "Millions USD",
            IndicatorType.INTEREST_RATE: "%",
            IndicatorType.EXCHANGE_RATE: "USD",
        }
        return units.get(indicator_type, "")

    def _generate_mock_data(
        self,
        indicator_type: IndicatorType,
        start_date: date,
        end_date: date,
        country: str,
    ) -> List[EconomicIndicator]:
        """Generate mock economic data."""
        import random
        from datetime import timedelta

        results = []

        # Base values for different indicators
        base_values = {
            IndicatorType.GDP: 25000,
            IndicatorType.UNEMPLOYMENT: 4.0,
            IndicatorType.INFLATION: 2.5,
            IndicatorType.CPI: 300,
            IndicatorType.CONSUMER_CONFIDENCE: 100,
            IndicatorType.RETAIL_SALES: 600000,
            IndicatorType.HOUSING_STARTS: 1500,
            IndicatorType.INTEREST_RATE: 5.0,
            IndicatorType.EXCHANGE_RATE: 1.0,
            IndicatorType.STOCK_INDEX: 4500,
        }

        base = base_values.get(indicator_type, 100)
        volatility = base * 0.02  # 2% volatility

        # Monthly data
        current = start_date.replace(day=1)
        value = base

        while current <= end_date:
            # Random walk with mean reversion
            value = value + random.gauss(0, volatility) + 0.1 * (base - value)

            results.append(EconomicIndicator(
                indicator_type=indicator_type,
                date=current,
                value=round(value, 2),
                country=country,
                unit=self._get_unit(indicator_type),
                source="Mock",
            ))

            # Move to next month
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)

        return results

    def get_exchange_rate(
        self,
        base_currency: str,
        target_currency: str,
        start_date: date,
        end_date: date,
    ) -> List[EconomicIndicator]:
        """
        Get exchange rate data.

        Args:
            base_currency: Base currency code (e.g., "USD")
            target_currency: Target currency code (e.g., "EUR")
            start_date: Start date
            end_date: End date

        Returns:
            List of exchange rate data
        """
        if self.config.alpha_vantage_key and self._requests:
            return self._fetch_exchange_rate(base_currency, target_currency, start_date, end_date)

        return self._generate_exchange_rate_mock(base_currency, target_currency, start_date, end_date)

    def _fetch_exchange_rate(
        self,
        base: str,
        target: str,
        start_date: date,
        end_date: date,
    ) -> List[EconomicIndicator]:
        """Fetch exchange rate from Alpha Vantage."""
        try:
            url = "https://www.alphavantage.co/query"
            params = {
                "function": "FX_DAILY",
                "from_symbol": base,
                "to_symbol": target,
                "apikey": self.config.alpha_vantage_key,
                "outputsize": "full",
            }
            response = self._requests.get(url, params=params, timeout=30)

            if response.status_code == 200:
                data = response.json()
                time_series = data.get("Time Series FX (Daily)", {})

                results = []
                for date_str, values in time_series.items():
                    d = date.fromisoformat(date_str)
                    if start_date <= d <= end_date:
                        results.append(EconomicIndicator(
                            indicator_type=IndicatorType.EXCHANGE_RATE,
                            date=d,
                            value=float(values["4. close"]),
                            country=f"{base}/{target}",
                            unit=target,
                            period="daily",
                            source="Alpha Vantage",
                        ))

                return sorted(results, key=lambda x: x.date)

        except Exception as e:
            logger.warning(f"Failed to fetch exchange rate: {e}")

        return self._generate_exchange_rate_mock(base, target, start_date, end_date)

    def _generate_exchange_rate_mock(
        self,
        base: str,
        target: str,
        start_date: date,
        end_date: date,
    ) -> List[EconomicIndicator]:
        """Generate mock exchange rate data."""
        import random
        from datetime import timedelta

        # Base rates
        base_rates = {
            ("USD", "EUR"): 0.92,
            ("USD", "GBP"): 0.79,
            ("USD", "JPY"): 150.0,
            ("EUR", "USD"): 1.09,
        }

        base_rate = base_rates.get((base, target), 1.0)
        results = []
        current = start_date
        rate = base_rate

        while current <= end_date:
            rate = rate * (1 + random.gauss(0, 0.005))  # 0.5% daily volatility

            results.append(EconomicIndicator(
                indicator_type=IndicatorType.EXCHANGE_RATE,
                date=current,
                value=round(rate, 4),
                country=f"{base}/{target}",
                unit=target,
                period="daily",
                source="Mock",
            ))

            current += timedelta(days=1)

        return results

    def to_dataframe(
        self,
        data: List[EconomicIndicator],
    ) -> pd.DataFrame:
        """Convert economic data to DataFrame."""
        return pd.DataFrame([d.to_dict() for d in data])

    def clear_cache(self) -> None:
        """Clear the cache."""
        self._cache.clear()
