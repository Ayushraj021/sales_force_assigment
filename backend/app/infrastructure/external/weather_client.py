"""
Weather Data Client

External weather data for demand forecasting.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import date, datetime
import logging
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class WeatherData:
    """Weather data point."""
    date: date
    location: str
    temperature_high: float
    temperature_low: float
    temperature_avg: float
    precipitation: float  # mm
    humidity: float  # percentage
    wind_speed: float  # km/h
    conditions: str  # sunny, cloudy, rainy, etc.
    uv_index: Optional[float] = None
    snow: Optional[float] = None  # cm

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date.isoformat(),
            "location": self.location,
            "temperature_high": self.temperature_high,
            "temperature_low": self.temperature_low,
            "temperature_avg": self.temperature_avg,
            "precipitation": self.precipitation,
            "humidity": self.humidity,
            "wind_speed": self.wind_speed,
            "conditions": self.conditions,
            "uv_index": self.uv_index,
            "snow": self.snow,
        }


@dataclass
class WeatherConfig:
    """Weather client configuration."""
    api_key: str
    provider: str = "openweathermap"  # openweathermap, weatherapi, visualcrossing
    units: str = "metric"  # metric, imperial
    cache_ttl_hours: int = 6


class WeatherClient:
    """
    Weather Data Client.

    Features:
    - Multiple provider support
    - Historical and forecast data
    - Location-based queries
    - Caching

    Example:
        client = WeatherClient(config)

        # Get historical weather
        data = client.get_historical("New York", start_date, end_date)

        # Get forecast
        forecast = client.get_forecast("Los Angeles", days=14)
    """

    def __init__(self, config: WeatherConfig):
        self.config = config
        self._cache: Dict[str, Any] = {}

        try:
            import requests
            self._requests = requests
        except ImportError:
            logger.warning("requests not installed")
            self._requests = None

    def get_historical(
        self,
        location: str,
        start_date: date,
        end_date: date,
    ) -> List[WeatherData]:
        """
        Get historical weather data.

        Args:
            location: City name or coordinates
            start_date: Start date
            end_date: End date

        Returns:
            List of WeatherData objects
        """
        cache_key = f"hist_{location}_{start_date}_{end_date}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        if self.config.provider == "openweathermap":
            data = self._fetch_openweathermap_historical(location, start_date, end_date)
        elif self.config.provider == "visualcrossing":
            data = self._fetch_visualcrossing(location, start_date, end_date)
        else:
            data = self._generate_mock_data(location, start_date, end_date)

        self._cache[cache_key] = data
        return data

    def get_forecast(
        self,
        location: str,
        days: int = 7,
    ) -> List[WeatherData]:
        """
        Get weather forecast.

        Args:
            location: City name or coordinates
            days: Number of days to forecast

        Returns:
            List of WeatherData objects
        """
        cache_key = f"forecast_{location}_{days}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        if self.config.provider == "openweathermap":
            data = self._fetch_openweathermap_forecast(location, days)
        else:
            # Generate mock forecast
            from datetime import timedelta
            today = date.today()
            end_date = today + timedelta(days=days)
            data = self._generate_mock_data(location, today, end_date)

        self._cache[cache_key] = data
        return data

    def _fetch_openweathermap_historical(
        self,
        location: str,
        start_date: date,
        end_date: date,
    ) -> List[WeatherData]:
        """Fetch from OpenWeatherMap API."""
        if not self._requests:
            return self._generate_mock_data(location, start_date, end_date)

        results = []
        current = start_date
        from datetime import timedelta

        while current <= end_date:
            try:
                timestamp = int(datetime.combine(current, datetime.min.time()).timestamp())
                url = f"https://api.openweathermap.org/data/2.5/onecall/timemachine"
                params = {
                    "q": location,
                    "dt": timestamp,
                    "appid": self.config.api_key,
                    "units": self.config.units,
                }
                response = self._requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    # Parse response
                    day_data = data.get("current", {})
                    results.append(WeatherData(
                        date=current,
                        location=location,
                        temperature_high=day_data.get("temp", 20),
                        temperature_low=day_data.get("temp", 15),
                        temperature_avg=day_data.get("temp", 17.5),
                        precipitation=day_data.get("rain", {}).get("1h", 0) * 24,
                        humidity=day_data.get("humidity", 50),
                        wind_speed=day_data.get("wind_speed", 10),
                        conditions=day_data.get("weather", [{}])[0].get("main", "Clear"),
                        uv_index=day_data.get("uvi"),
                    ))
            except Exception as e:
                logger.warning(f"Failed to fetch weather for {current}: {e}")

            current += timedelta(days=1)

        return results if results else self._generate_mock_data(location, start_date, end_date)

    def _fetch_openweathermap_forecast(
        self,
        location: str,
        days: int,
    ) -> List[WeatherData]:
        """Fetch forecast from OpenWeatherMap."""
        if not self._requests:
            from datetime import timedelta
            return self._generate_mock_data(
                location,
                date.today(),
                date.today() + timedelta(days=days)
            )

        try:
            url = "https://api.openweathermap.org/data/2.5/forecast"
            params = {
                "q": location,
                "appid": self.config.api_key,
                "units": self.config.units,
                "cnt": days * 8,  # 3-hour intervals
            }
            response = self._requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                # Aggregate to daily
                daily_data = {}
                for item in data.get("list", []):
                    dt = datetime.fromtimestamp(item["dt"]).date()
                    if dt not in daily_data:
                        daily_data[dt] = []
                    daily_data[dt].append(item)

                results = []
                for dt, items in sorted(daily_data.items()):
                    temps = [i["main"]["temp"] for i in items]
                    results.append(WeatherData(
                        date=dt,
                        location=location,
                        temperature_high=max(temps),
                        temperature_low=min(temps),
                        temperature_avg=sum(temps) / len(temps),
                        precipitation=sum(i.get("rain", {}).get("3h", 0) for i in items),
                        humidity=sum(i["main"]["humidity"] for i in items) / len(items),
                        wind_speed=sum(i["wind"]["speed"] for i in items) / len(items),
                        conditions=items[len(items)//2]["weather"][0]["main"],
                    ))

                return results

        except Exception as e:
            logger.warning(f"Failed to fetch forecast: {e}")

        from datetime import timedelta
        return self._generate_mock_data(location, date.today(), date.today() + timedelta(days=days))

    def _fetch_visualcrossing(
        self,
        location: str,
        start_date: date,
        end_date: date,
    ) -> List[WeatherData]:
        """Fetch from Visual Crossing API."""
        if not self._requests:
            return self._generate_mock_data(location, start_date, end_date)

        try:
            url = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{location}/{start_date}/{end_date}"
            params = {
                "key": self.config.api_key,
                "unitGroup": self.config.units,
                "include": "days",
            }
            response = self._requests.get(url, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                results = []
                for day in data.get("days", []):
                    results.append(WeatherData(
                        date=date.fromisoformat(day["datetime"]),
                        location=location,
                        temperature_high=day.get("tempmax", 20),
                        temperature_low=day.get("tempmin", 10),
                        temperature_avg=day.get("temp", 15),
                        precipitation=day.get("precip", 0),
                        humidity=day.get("humidity", 50),
                        wind_speed=day.get("windspeed", 10),
                        conditions=day.get("conditions", "Clear"),
                        uv_index=day.get("uvindex"),
                        snow=day.get("snow"),
                    ))
                return results

        except Exception as e:
            logger.warning(f"Failed to fetch from Visual Crossing: {e}")

        return self._generate_mock_data(location, start_date, end_date)

    def _generate_mock_data(
        self,
        location: str,
        start_date: date,
        end_date: date,
    ) -> List[WeatherData]:
        """Generate mock weather data."""
        import random
        from datetime import timedelta

        results = []
        current = start_date
        conditions_list = ["Clear", "Cloudy", "Partly Cloudy", "Rainy", "Overcast"]

        while current <= end_date:
            # Seasonal variation
            day_of_year = current.timetuple().tm_yday
            seasonal_factor = 10 * (1 + 0.5 * (1 - abs(day_of_year - 182) / 182))

            base_temp = 15 + seasonal_factor + random.gauss(0, 3)
            temp_range = random.uniform(5, 15)

            results.append(WeatherData(
                date=current,
                location=location,
                temperature_high=base_temp + temp_range / 2,
                temperature_low=base_temp - temp_range / 2,
                temperature_avg=base_temp,
                precipitation=max(0, random.gauss(2, 5)),
                humidity=random.uniform(30, 90),
                wind_speed=random.uniform(0, 30),
                conditions=random.choice(conditions_list),
                uv_index=random.uniform(0, 11),
            ))
            current += timedelta(days=1)

        return results

    def to_dataframe(self, data: List[WeatherData]) -> pd.DataFrame:
        """Convert weather data to DataFrame."""
        return pd.DataFrame([d.to_dict() for d in data])

    def clear_cache(self) -> None:
        """Clear the cache."""
        self._cache.clear()
