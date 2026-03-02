"""
Data Transformers

Common data transformation functions for ETL.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class TransformConfig:
    """Transformation configuration."""
    date_format: str = "%Y-%m-%d"
    null_strategy: str = "fill"  # drop, fill, interpolate
    outlier_method: str = "clip"  # clip, remove, keep


class DataTransformer:
    """
    Data Transformation Utilities.

    Example:
        transformer = DataTransformer()
        df = transformer.normalize(df, columns=["spend", "revenue"])
        df = transformer.encode_categorical(df, columns=["channel"])
    """

    def __init__(self, config: Optional[TransformConfig] = None):
        self.config = config or TransformConfig()
        self._scalers: Dict[str, tuple] = {}

    def normalize(
        self,
        df: pd.DataFrame,
        columns: List[str],
        method: str = "minmax",  # minmax, zscore, robust
    ) -> pd.DataFrame:
        """Normalize numeric columns."""
        df = df.copy()

        for col in columns:
            if col not in df.columns:
                continue

            values = df[col].values

            if method == "minmax":
                min_val, max_val = values.min(), values.max()
                df[col] = (values - min_val) / (max_val - min_val + 1e-10)
                self._scalers[col] = (min_val, max_val)

            elif method == "zscore":
                mean_val, std_val = values.mean(), values.std()
                df[col] = (values - mean_val) / (std_val + 1e-10)
                self._scalers[col] = (mean_val, std_val)

            elif method == "robust":
                median = np.median(values)
                iqr = np.percentile(values, 75) - np.percentile(values, 25)
                df[col] = (values - median) / (iqr + 1e-10)
                self._scalers[col] = (median, iqr)

        return df

    def denormalize(
        self,
        df: pd.DataFrame,
        columns: List[str],
        method: str = "minmax",
    ) -> pd.DataFrame:
        """Reverse normalization."""
        df = df.copy()

        for col in columns:
            if col not in df.columns or col not in self._scalers:
                continue

            values = df[col].values
            params = self._scalers[col]

            if method == "minmax":
                df[col] = values * (params[1] - params[0]) + params[0]
            elif method == "zscore":
                df[col] = values * params[1] + params[0]
            elif method == "robust":
                df[col] = values * params[1] + params[0]

        return df

    def encode_categorical(
        self,
        df: pd.DataFrame,
        columns: List[str],
        method: str = "onehot",  # onehot, label, target
    ) -> pd.DataFrame:
        """Encode categorical columns."""
        df = df.copy()

        for col in columns:
            if col not in df.columns:
                continue

            if method == "onehot":
                dummies = pd.get_dummies(df[col], prefix=col, drop_first=True)
                df = pd.concat([df.drop(col, axis=1), dummies], axis=1)

            elif method == "label":
                df[col] = pd.Categorical(df[col]).codes

        return df

    def handle_missing(
        self,
        df: pd.DataFrame,
        columns: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """Handle missing values."""
        df = df.copy()
        columns = columns or df.columns.tolist()

        for col in columns:
            if col not in df.columns or not df[col].isna().any():
                continue

            if self.config.null_strategy == "drop":
                df = df.dropna(subset=[col])
            elif self.config.null_strategy == "fill":
                if df[col].dtype in [np.float64, np.int64]:
                    df[col] = df[col].fillna(df[col].median())
                else:
                    mode = df[col].mode()
                    df[col] = df[col].fillna(mode.iloc[0] if len(mode) > 0 else "unknown")
            elif self.config.null_strategy == "interpolate":
                df[col] = df[col].interpolate(method="linear")

        return df

    def handle_outliers(
        self,
        df: pd.DataFrame,
        columns: List[str],
        threshold: float = 3.0,
    ) -> pd.DataFrame:
        """Handle outliers using z-score."""
        df = df.copy()

        for col in columns:
            if col not in df.columns or df[col].dtype not in [np.float64, np.int64]:
                continue

            mean = df[col].mean()
            std = df[col].std()

            if self.config.outlier_method == "clip":
                lower = mean - threshold * std
                upper = mean + threshold * std
                df[col] = df[col].clip(lower, upper)
            elif self.config.outlier_method == "remove":
                z_scores = np.abs((df[col] - mean) / std)
                df = df[z_scores <= threshold]

        return df

    def aggregate_time_series(
        self,
        df: pd.DataFrame,
        date_col: str,
        value_cols: List[str],
        freq: str = "W",  # D, W, M, Q, Y
        agg_func: str = "sum",
    ) -> pd.DataFrame:
        """Aggregate time series data."""
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.set_index(date_col)

        agg_dict = {col: agg_func for col in value_cols if col in df.columns}
        result = df.resample(freq).agg(agg_dict).reset_index()

        return result

    def create_features(
        self,
        df: pd.DataFrame,
        date_col: str,
    ) -> pd.DataFrame:
        """Create time-based features."""
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col])

        df["year"] = df[date_col].dt.year
        df["month"] = df[date_col].dt.month
        df["week"] = df[date_col].dt.isocalendar().week
        df["day_of_week"] = df[date_col].dt.dayofweek
        df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)

        return df
