"""
Data Service

Core data management and transformation service.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union
from datetime import date, datetime
from enum import Enum
import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class DataSourceType(str, Enum):
    """Types of data sources."""
    CSV = "csv"
    DATABASE = "database"
    API = "api"
    WAREHOUSE = "warehouse"
    STREAMING = "streaming"


@dataclass
class DataSource:
    """Data source configuration."""
    name: str
    source_type: DataSourceType
    connection_string: Optional[str] = None
    file_path: Optional[str] = None
    api_endpoint: Optional[str] = None
    credentials: Dict[str, str] = field(default_factory=dict)
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DataConfig:
    """Data service configuration."""
    default_date_column: str = "date"
    default_value_column: str = "value"
    date_format: str = "%Y-%m-%d"
    missing_value_strategy: str = "interpolate"  # drop, fill, interpolate
    outlier_threshold: float = 3.0  # Standard deviations


class DataService:
    """
    Data Management Service.

    Features:
    - Data loading from multiple sources
    - Data transformation
    - Missing value handling
    - Outlier detection
    - Feature engineering

    Example:
        service = DataService()

        # Load data
        df = service.load_data(source)

        # Prepare for modeling
        prepared = service.prepare_for_modeling(
            df,
            target_col="sales",
            feature_cols=["spend", "impressions"]
        )
    """

    def __init__(self, config: Optional[DataConfig] = None):
        self.config = config or DataConfig()
        self._cache: Dict[str, pd.DataFrame] = {}

    def load_data(
        self,
        source: Union[DataSource, str, pd.DataFrame],
        **kwargs,
    ) -> pd.DataFrame:
        """
        Load data from source.

        Args:
            source: Data source or file path
            **kwargs: Additional loading parameters

        Returns:
            DataFrame
        """
        if isinstance(source, pd.DataFrame):
            return source.copy()

        if isinstance(source, str):
            # Assume file path
            if source.endswith(".csv"):
                return pd.read_csv(source, **kwargs)
            elif source.endswith((".xls", ".xlsx")):
                return pd.read_excel(source, **kwargs)
            elif source.endswith(".parquet"):
                return pd.read_parquet(source, **kwargs)
            elif source.endswith(".json"):
                return pd.read_json(source, **kwargs)
            else:
                raise ValueError(f"Unsupported file format: {source}")

        if isinstance(source, DataSource):
            return self._load_from_source(source, **kwargs)

        raise ValueError(f"Invalid source type: {type(source)}")

    def _load_from_source(
        self,
        source: DataSource,
        **kwargs,
    ) -> pd.DataFrame:
        """Load data from DataSource."""
        if source.source_type == DataSourceType.CSV:
            return pd.read_csv(source.file_path, **kwargs)

        elif source.source_type == DataSourceType.DATABASE:
            import sqlalchemy
            engine = sqlalchemy.create_engine(source.connection_string)
            query = source.options.get("query", f"SELECT * FROM {source.name}")
            return pd.read_sql(query, engine)

        elif source.source_type == DataSourceType.API:
            import requests
            response = requests.get(
                source.api_endpoint,
                headers=source.credentials,
                **source.options,
            )
            response.raise_for_status()
            return pd.DataFrame(response.json())

        else:
            raise ValueError(f"Unsupported source type: {source.source_type}")

    def prepare_for_modeling(
        self,
        df: pd.DataFrame,
        target_col: str,
        feature_cols: List[str],
        date_col: Optional[str] = None,
    ) -> Dict[str, np.ndarray]:
        """
        Prepare data for modeling.

        Args:
            df: Input DataFrame
            target_col: Target column name
            feature_cols: Feature column names
            date_col: Date column (optional)

        Returns:
            Dict with X, y arrays
        """
        df = df.copy()

        # Handle dates
        date_col = date_col or self.config.default_date_column
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col])
            df = df.sort_values(date_col)

        # Handle missing values
        df = self.handle_missing_values(df, feature_cols + [target_col])

        # Extract features and target
        X = df[feature_cols].values
        y = df[target_col].values

        result = {"X": X, "y": y}

        if date_col in df.columns:
            result["dates"] = df[date_col].values

        return result

    def handle_missing_values(
        self,
        df: pd.DataFrame,
        columns: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Handle missing values.

        Args:
            df: Input DataFrame
            columns: Columns to process

        Returns:
            DataFrame with handled missing values
        """
        df = df.copy()
        columns = columns or df.columns.tolist()

        for col in columns:
            if col not in df.columns:
                continue

            if df[col].isna().any():
                if self.config.missing_value_strategy == "drop":
                    df = df.dropna(subset=[col])

                elif self.config.missing_value_strategy == "fill":
                    if df[col].dtype in [np.float64, np.int64]:
                        df[col] = df[col].fillna(df[col].median())
                    else:
                        df[col] = df[col].fillna(df[col].mode().iloc[0] if not df[col].mode().empty else "unknown")

                elif self.config.missing_value_strategy == "interpolate":
                    if df[col].dtype in [np.float64, np.int64]:
                        df[col] = df[col].interpolate(method="linear")
                    else:
                        df[col] = df[col].ffill().bfill()

        return df

    def detect_outliers(
        self,
        df: pd.DataFrame,
        columns: List[str],
        method: str = "zscore",  # zscore, iqr
    ) -> pd.DataFrame:
        """
        Detect outliers in data.

        Args:
            df: Input DataFrame
            columns: Columns to check
            method: Detection method

        Returns:
            DataFrame with outlier flags
        """
        df = df.copy()

        for col in columns:
            if col not in df.columns or df[col].dtype not in [np.float64, np.int64]:
                continue

            if method == "zscore":
                z_scores = np.abs((df[col] - df[col].mean()) / df[col].std())
                df[f"{col}_outlier"] = z_scores > self.config.outlier_threshold

            elif method == "iqr":
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower = Q1 - 1.5 * IQR
                upper = Q3 + 1.5 * IQR
                df[f"{col}_outlier"] = (df[col] < lower) | (df[col] > upper)

        return df

    def create_time_features(
        self,
        df: pd.DataFrame,
        date_col: str,
    ) -> pd.DataFrame:
        """
        Create time-based features.

        Args:
            df: Input DataFrame
            date_col: Date column name

        Returns:
            DataFrame with time features
        """
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col])

        # Basic time features
        df["year"] = df[date_col].dt.year
        df["month"] = df[date_col].dt.month
        df["week"] = df[date_col].dt.isocalendar().week
        df["day_of_week"] = df[date_col].dt.dayofweek
        df["day_of_month"] = df[date_col].dt.day
        df["day_of_year"] = df[date_col].dt.dayofyear
        df["quarter"] = df[date_col].dt.quarter

        # Cyclic encoding
        df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
        df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
        df["day_of_week_sin"] = np.sin(2 * np.pi * df["day_of_week"] / 7)
        df["day_of_week_cos"] = np.cos(2 * np.pi * df["day_of_week"] / 7)

        # Boolean features
        df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
        df["is_month_start"] = df[date_col].dt.is_month_start.astype(int)
        df["is_month_end"] = df[date_col].dt.is_month_end.astype(int)

        return df

    def create_lag_features(
        self,
        df: pd.DataFrame,
        columns: List[str],
        lags: List[int],
    ) -> pd.DataFrame:
        """
        Create lag features.

        Args:
            df: Input DataFrame
            columns: Columns to create lags for
            lags: Lag periods

        Returns:
            DataFrame with lag features
        """
        df = df.copy()

        for col in columns:
            if col not in df.columns:
                continue

            for lag in lags:
                df[f"{col}_lag_{lag}"] = df[col].shift(lag)

        return df

    def create_rolling_features(
        self,
        df: pd.DataFrame,
        columns: List[str],
        windows: List[int],
        functions: List[str] = ["mean", "std", "min", "max"],
    ) -> pd.DataFrame:
        """
        Create rolling window features.

        Args:
            df: Input DataFrame
            columns: Columns to process
            windows: Window sizes
            functions: Aggregation functions

        Returns:
            DataFrame with rolling features
        """
        df = df.copy()

        for col in columns:
            if col not in df.columns:
                continue

            for window in windows:
                rolling = df[col].rolling(window=window, min_periods=1)

                if "mean" in functions:
                    df[f"{col}_rolling_{window}_mean"] = rolling.mean()
                if "std" in functions:
                    df[f"{col}_rolling_{window}_std"] = rolling.std()
                if "min" in functions:
                    df[f"{col}_rolling_{window}_min"] = rolling.min()
                if "max" in functions:
                    df[f"{col}_rolling_{window}_max"] = rolling.max()
                if "sum" in functions:
                    df[f"{col}_rolling_{window}_sum"] = rolling.sum()

        return df

    def aggregate_data(
        self,
        df: pd.DataFrame,
        group_cols: List[str],
        agg_cols: Dict[str, List[str]],
    ) -> pd.DataFrame:
        """
        Aggregate data.

        Args:
            df: Input DataFrame
            group_cols: Columns to group by
            agg_cols: Dict mapping columns to aggregation functions

        Returns:
            Aggregated DataFrame
        """
        agg_dict = {}
        for col, funcs in agg_cols.items():
            for func in funcs:
                agg_dict[(col, func)] = (col, func)

        result = df.groupby(group_cols).agg(**{
            f"{col}_{func}": pd.NamedAgg(column=col, aggfunc=func)
            for col, funcs in agg_cols.items()
            for func in funcs
        }).reset_index()

        return result

    def split_data(
        self,
        df: pd.DataFrame,
        test_size: float = 0.2,
        date_col: Optional[str] = None,
    ) -> Dict[str, pd.DataFrame]:
        """
        Split data into train/test sets.

        Args:
            df: Input DataFrame
            test_size: Test set proportion
            date_col: Date column for time-based split

        Returns:
            Dict with train and test DataFrames
        """
        if date_col and date_col in df.columns:
            # Time-based split
            df = df.sort_values(date_col)
            split_idx = int(len(df) * (1 - test_size))
            train = df.iloc[:split_idx].copy()
            test = df.iloc[split_idx:].copy()
        else:
            # Random split
            indices = np.random.permutation(len(df))
            split_idx = int(len(df) * (1 - test_size))
            train = df.iloc[indices[:split_idx]].copy()
            test = df.iloc[indices[split_idx:]].copy()

        return {"train": train, "test": test}

    def cache_data(self, key: str, df: pd.DataFrame) -> None:
        """Cache data for later use."""
        self._cache[key] = df.copy()

    def get_cached_data(self, key: str) -> Optional[pd.DataFrame]:
        """Get cached data."""
        return self._cache.get(key)

    def clear_cache(self) -> None:
        """Clear data cache."""
        self._cache.clear()
