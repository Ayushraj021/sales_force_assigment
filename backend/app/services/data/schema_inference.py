"""
Schema Inference Service

Automatic schema detection and inference for data files:
- Column type detection (numeric, categorical, datetime, boolean, etc.)
- Semantic type detection (email, phone, currency, percentage, etc.)
- Date format detection and parsing
- Encoding detection
- Delimiter detection for CSV files
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union
from enum import Enum
import pandas as pd
import numpy as np
import re
from datetime import datetime
import chardet
from io import BytesIO, StringIO


class DataType(str, Enum):
    """Detected data types"""
    INTEGER = "integer"
    FLOAT = "float"
    STRING = "string"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    DATE = "date"
    TIME = "time"
    CATEGORICAL = "categorical"
    TEXT = "text"  # Long text
    UNKNOWN = "unknown"


class SemanticType(str, Enum):
    """Semantic meaning of columns"""
    ID = "id"
    NAME = "name"
    EMAIL = "email"
    PHONE = "phone"
    ADDRESS = "address"
    CITY = "city"
    STATE = "state"
    COUNTRY = "country"
    POSTAL_CODE = "postal_code"
    URL = "url"
    IP_ADDRESS = "ip_address"
    CURRENCY = "currency"
    PERCENTAGE = "percentage"
    DATE = "date"
    TIMESTAMP = "timestamp"
    LATITUDE = "latitude"
    LONGITUDE = "longitude"
    QUANTITY = "quantity"
    PRICE = "price"
    REVENUE = "revenue"
    COST = "cost"
    COUNT = "count"
    RATIO = "ratio"
    SCORE = "score"
    RATING = "rating"
    CATEGORY = "category"
    STATUS = "status"
    FLAG = "flag"
    DESCRIPTION = "description"
    COMMENT = "comment"
    GENERIC = "generic"


@dataclass
class ColumnSchema:
    """Inferred schema for a single column"""
    name: str
    data_type: DataType
    semantic_type: SemanticType
    nullable: bool
    unique: bool
    sample_values: List[Any]
    statistics: Dict[str, Any]
    format_pattern: Optional[str] = None
    recommended_transformations: List[str] = field(default_factory=list)
    confidence: float = 1.0  # Confidence in type detection (0-1)


@dataclass
class InferredSchema:
    """Complete inferred schema for a dataset"""
    columns: List[ColumnSchema]
    row_count: int
    detected_delimiter: Optional[str]
    detected_encoding: str
    has_header: bool
    date_columns: List[str]
    numeric_columns: List[str]
    categorical_columns: List[str]
    id_columns: List[str]
    target_column_candidates: List[str]
    recommendations: List[str]


class SchemaInferenceService:
    """Service for automatic schema inference"""

    # Date patterns with their formats
    DATE_PATTERNS = [
        (r'^\d{4}-\d{2}-\d{2}$', '%Y-%m-%d'),
        (r'^\d{4}/\d{2}/\d{2}$', '%Y/%m/%d'),
        (r'^\d{2}-\d{2}-\d{4}$', '%d-%m-%Y'),
        (r'^\d{2}/\d{2}/\d{4}$', '%m/%d/%Y'),
        (r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', '%Y-%m-%dT%H:%M:%S'),
        (r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', '%Y-%m-%d %H:%M:%S'),
        (r'^\d{2}/\d{2}/\d{4} \d{2}:\d{2}', '%m/%d/%Y %H:%M'),
        (r'^\d{4}\d{2}\d{2}$', '%Y%m%d'),
    ]

    # Regex patterns for semantic types
    SEMANTIC_PATTERNS = {
        SemanticType.EMAIL: r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$',
        SemanticType.PHONE: r'^[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}$',
        SemanticType.URL: r'^https?://[^\s]+$',
        SemanticType.IP_ADDRESS: r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$',
        SemanticType.POSTAL_CODE: r'^\d{5}(-\d{4})?$|^[A-Z]\d[A-Z] ?\d[A-Z]\d$',
        SemanticType.LATITUDE: r'^-?([1-8]?\d(?:\.\d+)?|90(?:\.0+)?)$',
        SemanticType.LONGITUDE: r'^-?((?:1[0-7]|[1-9])?\d(?:\.\d+)?|180(?:\.0+)?)$',
    }

    # Column name patterns for semantic detection
    NAME_PATTERNS = {
        SemanticType.ID: ['id', 'key', 'uuid', 'guid', 'identifier', 'code'],
        SemanticType.NAME: ['name', 'title', 'label'],
        SemanticType.EMAIL: ['email', 'e-mail', 'mail'],
        SemanticType.PHONE: ['phone', 'tel', 'mobile', 'cell', 'fax'],
        SemanticType.ADDRESS: ['address', 'street', 'addr'],
        SemanticType.CITY: ['city', 'town', 'municipality'],
        SemanticType.STATE: ['state', 'province', 'region'],
        SemanticType.COUNTRY: ['country', 'nation'],
        SemanticType.POSTAL_CODE: ['zip', 'postal', 'postcode'],
        SemanticType.URL: ['url', 'link', 'website', 'href'],
        SemanticType.DATE: ['date', 'day', 'created', 'updated', 'modified', 'timestamp'],
        SemanticType.PRICE: ['price', 'cost', 'amount', 'fee', 'charge'],
        SemanticType.REVENUE: ['revenue', 'sales', 'income', 'earnings'],
        SemanticType.QUANTITY: ['qty', 'quantity', 'count', 'number', 'num', 'total'],
        SemanticType.PERCENTAGE: ['percent', 'pct', 'rate', 'ratio'],
        SemanticType.CATEGORY: ['category', 'type', 'class', 'group', 'segment'],
        SemanticType.STATUS: ['status', 'state', 'stage', 'phase'],
        SemanticType.DESCRIPTION: ['description', 'desc', 'details', 'notes', 'comment'],
        SemanticType.RATING: ['rating', 'score', 'rank', 'grade'],
    }

    def __init__(self):
        pass

    def infer_schema(
        self,
        data: Union[pd.DataFrame, bytes, str],
        sample_size: int = 10000,
        file_type: Optional[str] = None,
    ) -> InferredSchema:
        """
        Infer schema from data

        Args:
            data: DataFrame, file bytes, or file path
            sample_size: Number of rows to sample for inference
            file_type: File type hint (csv, excel, parquet, json)

        Returns:
            InferredSchema with complete type information
        """
        # Load data
        df, metadata = self._load_data(data, file_type)

        if df.empty:
            return self._empty_schema(metadata)

        # Sample for large datasets
        if len(df) > sample_size:
            df_sample = df.sample(n=sample_size, random_state=42)
        else:
            df_sample = df

        # Infer column schemas
        column_schemas = []
        date_columns = []
        numeric_columns = []
        categorical_columns = []
        id_columns = []

        for col in df.columns:
            col_schema = self._infer_column_schema(df_sample[col], col)
            column_schemas.append(col_schema)

            # Categorize columns
            if col_schema.data_type in [DataType.DATE, DataType.DATETIME]:
                date_columns.append(col)
            elif col_schema.data_type in [DataType.INTEGER, DataType.FLOAT]:
                numeric_columns.append(col)
            elif col_schema.data_type == DataType.CATEGORICAL:
                categorical_columns.append(col)

            if col_schema.semantic_type == SemanticType.ID:
                id_columns.append(col)

        # Detect target column candidates
        target_candidates = self._detect_target_candidates(df_sample, column_schemas)

        # Generate recommendations
        recommendations = self._generate_recommendations(column_schemas, df_sample)

        return InferredSchema(
            columns=column_schemas,
            row_count=len(df),
            detected_delimiter=metadata.get('delimiter'),
            detected_encoding=metadata.get('encoding', 'utf-8'),
            has_header=metadata.get('has_header', True),
            date_columns=date_columns,
            numeric_columns=numeric_columns,
            categorical_columns=categorical_columns,
            id_columns=id_columns,
            target_column_candidates=target_candidates,
            recommendations=recommendations,
        )

    def _load_data(
        self,
        data: Union[pd.DataFrame, bytes, str],
        file_type: Optional[str]
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Load data from various sources"""
        metadata = {}

        if isinstance(data, pd.DataFrame):
            return data, metadata

        if isinstance(data, bytes):
            # Detect encoding
            detected = chardet.detect(data)
            encoding = detected.get('encoding', 'utf-8')
            metadata['encoding'] = encoding

            # Detect delimiter for CSV
            if file_type in [None, 'csv']:
                delimiter = self._detect_delimiter(data.decode(encoding, errors='replace'))
                metadata['delimiter'] = delimiter

                try:
                    df = pd.read_csv(
                        BytesIO(data),
                        encoding=encoding,
                        delimiter=delimiter,
                        on_bad_lines='skip'
                    )
                    metadata['has_header'] = self._detect_header(df)
                    return df, metadata
                except Exception:
                    pass

            # Try other formats
            if file_type in [None, 'excel', 'xlsx', 'xls']:
                try:
                    df = pd.read_excel(BytesIO(data))
                    return df, metadata
                except Exception:
                    pass

            if file_type in [None, 'parquet']:
                try:
                    df = pd.read_parquet(BytesIO(data))
                    return df, metadata
                except Exception:
                    pass

            if file_type in [None, 'json']:
                try:
                    df = pd.read_json(BytesIO(data))
                    return df, metadata
                except Exception:
                    pass

        elif isinstance(data, str):
            # File path
            if data.endswith('.csv'):
                df = pd.read_csv(data)
            elif data.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(data)
            elif data.endswith('.parquet'):
                df = pd.read_parquet(data)
            elif data.endswith('.json'):
                df = pd.read_json(data)
            else:
                raise ValueError(f"Unsupported file format: {data}")

            return df, metadata

        return pd.DataFrame(), metadata

    def _detect_delimiter(self, text: str, sample_lines: int = 20) -> str:
        """Detect CSV delimiter"""
        lines = text.split('\n')[:sample_lines]
        delimiters = [',', ';', '\t', '|']

        delimiter_counts = {}
        for delimiter in delimiters:
            counts = [line.count(delimiter) for line in lines if line.strip()]
            if counts:
                # Check for consistency
                avg = np.mean(counts)
                std = np.std(counts)
                if std < avg * 0.2 and avg > 0:  # Low variance and non-zero
                    delimiter_counts[delimiter] = avg

        if delimiter_counts:
            return max(delimiter_counts, key=delimiter_counts.get)
        return ','

    def _detect_header(self, df: pd.DataFrame) -> bool:
        """Detect if DataFrame has a header row"""
        if df.empty:
            return True

        # Check if first row looks like data (all numeric columns have numeric values)
        first_row = df.iloc[0]

        numeric_like_header = 0
        for col in df.columns:
            if df[col].dtype in ['int64', 'float64']:
                continue
            # If column header looks like a value, might not have header
            try:
                float(col)
                numeric_like_header += 1
            except (ValueError, TypeError):
                pass

        return numeric_like_header < len(df.columns) / 2

    def _infer_column_schema(self, series: pd.Series, column_name: str) -> ColumnSchema:
        """Infer schema for a single column"""
        # Basic statistics
        non_null = series.dropna()
        nullable = series.isnull().any()
        unique = series.nunique() == len(series)

        # Get sample values
        sample_values = non_null.head(5).tolist() if len(non_null) > 0 else []

        # Infer data type
        data_type, confidence, format_pattern = self._infer_data_type(series, column_name)

        # Infer semantic type
        semantic_type = self._infer_semantic_type(series, column_name, data_type)

        # Calculate statistics based on type
        statistics = self._calculate_statistics(series, data_type)

        # Generate transformation recommendations
        transformations = self._recommend_transformations(series, data_type, semantic_type)

        return ColumnSchema(
            name=column_name,
            data_type=data_type,
            semantic_type=semantic_type,
            nullable=nullable,
            unique=unique,
            sample_values=sample_values,
            statistics=statistics,
            format_pattern=format_pattern,
            recommended_transformations=transformations,
            confidence=confidence,
        )

    def _infer_data_type(
        self,
        series: pd.Series,
        column_name: str
    ) -> Tuple[DataType, float, Optional[str]]:
        """Infer the data type of a column"""
        if series.empty or series.isnull().all():
            return DataType.UNKNOWN, 0.0, None

        non_null = series.dropna()
        sample = non_null.sample(min(1000, len(non_null)), random_state=42) if len(non_null) > 1000 else non_null

        # Check pandas dtype first
        if pd.api.types.is_datetime64_any_dtype(series):
            return DataType.DATETIME, 1.0, None

        if pd.api.types.is_integer_dtype(series):
            return DataType.INTEGER, 1.0, None

        if pd.api.types.is_float_dtype(series):
            return DataType.FLOAT, 1.0, None

        if pd.api.types.is_bool_dtype(series):
            return DataType.BOOLEAN, 1.0, None

        # For object dtype, try to infer
        if series.dtype == 'object':
            # Try datetime
            date_type, confidence, format_pattern = self._try_parse_datetime(sample)
            if date_type:
                return date_type, confidence, format_pattern

            # Try numeric
            numeric_type, confidence = self._try_parse_numeric(sample)
            if numeric_type:
                return numeric_type, confidence, None

            # Try boolean
            if self._is_boolean(sample):
                return DataType.BOOLEAN, 0.9, None

            # Check if categorical (low cardinality)
            cardinality_ratio = series.nunique() / len(series)
            if cardinality_ratio < 0.05 and series.nunique() < 100:
                return DataType.CATEGORICAL, 0.9, None

            # Check if long text
            if sample.str.len().mean() > 100:
                return DataType.TEXT, 0.8, None

            return DataType.STRING, 0.7, None

        return DataType.UNKNOWN, 0.5, None

    def _try_parse_datetime(self, sample: pd.Series) -> Tuple[Optional[DataType], float, Optional[str]]:
        """Try to parse series as datetime"""
        for pattern, fmt in self.DATE_PATTERNS:
            matches = sample.astype(str).str.match(pattern)
            match_ratio = matches.mean()

            if match_ratio > 0.8:
                # Determine if date or datetime
                if 'T' in fmt or ':' in fmt:
                    return DataType.DATETIME, match_ratio, fmt
                return DataType.DATE, match_ratio, fmt

        # Try pandas datetime parsing
        try:
            parsed = pd.to_datetime(sample, errors='coerce', infer_datetime_format=True)
            valid_ratio = parsed.notna().mean()
            if valid_ratio > 0.8:
                return DataType.DATETIME, valid_ratio, None
        except Exception:
            pass

        return None, 0.0, None

    def _try_parse_numeric(self, sample: pd.Series) -> Tuple[Optional[DataType], float]:
        """Try to parse series as numeric"""
        try:
            # Remove currency symbols and commas
            cleaned = sample.astype(str).str.replace(r'[$€£¥,]', '', regex=True)
            parsed = pd.to_numeric(cleaned, errors='coerce')
            valid_ratio = parsed.notna().mean()

            if valid_ratio > 0.8:
                # Check if integer or float
                valid_values = parsed.dropna()
                if (valid_values == valid_values.astype(int)).all():
                    return DataType.INTEGER, valid_ratio
                return DataType.FLOAT, valid_ratio
        except Exception:
            pass

        return None, 0.0

    def _is_boolean(self, sample: pd.Series) -> bool:
        """Check if series represents boolean values"""
        boolean_values = {
            'true', 'false', 'yes', 'no', 'y', 'n', '1', '0',
            't', 'f', 'on', 'off', 'enabled', 'disabled'
        }

        unique_values = set(sample.astype(str).str.lower().unique())
        return len(unique_values) <= 2 and unique_values.issubset(boolean_values)

    def _infer_semantic_type(
        self,
        series: pd.Series,
        column_name: str,
        data_type: DataType
    ) -> SemanticType:
        """Infer the semantic meaning of a column"""
        col_lower = column_name.lower()

        # Check column name patterns
        for semantic_type, patterns in self.NAME_PATTERNS.items():
            if any(p in col_lower for p in patterns):
                return semantic_type

        # Check value patterns for string columns
        if data_type == DataType.STRING and not series.empty:
            sample = series.dropna().head(100)
            for semantic_type, pattern in self.SEMANTIC_PATTERNS.items():
                matches = sample.astype(str).str.match(pattern).mean()
                if matches > 0.8:
                    return semantic_type

        # Type-based defaults
        if data_type == DataType.BOOLEAN:
            return SemanticType.FLAG

        if data_type in [DataType.DATE, DataType.DATETIME]:
            return SemanticType.DATE

        if data_type == DataType.CATEGORICAL:
            return SemanticType.CATEGORY

        return SemanticType.GENERIC

    def _calculate_statistics(self, series: pd.Series, data_type: DataType) -> Dict[str, Any]:
        """Calculate statistics based on data type"""
        stats = {
            'count': len(series),
            'null_count': int(series.isnull().sum()),
            'unique_count': int(series.nunique()),
        }

        non_null = series.dropna()

        if data_type in [DataType.INTEGER, DataType.FLOAT]:
            numeric = pd.to_numeric(non_null, errors='coerce').dropna()
            if len(numeric) > 0:
                stats.update({
                    'mean': round(float(numeric.mean()), 4),
                    'std': round(float(numeric.std()), 4),
                    'min': float(numeric.min()),
                    'max': float(numeric.max()),
                    'median': float(numeric.median()),
                    'q25': float(numeric.quantile(0.25)),
                    'q75': float(numeric.quantile(0.75)),
                })

        elif data_type in [DataType.STRING, DataType.TEXT, DataType.CATEGORICAL]:
            if len(non_null) > 0:
                lengths = non_null.astype(str).str.len()
                stats.update({
                    'min_length': int(lengths.min()),
                    'max_length': int(lengths.max()),
                    'avg_length': round(float(lengths.mean()), 2),
                    'top_values': non_null.value_counts().head(5).to_dict(),
                })

        elif data_type in [DataType.DATE, DataType.DATETIME]:
            try:
                dates = pd.to_datetime(non_null, errors='coerce').dropna()
                if len(dates) > 0:
                    stats.update({
                        'min_date': str(dates.min()),
                        'max_date': str(dates.max()),
                        'date_range_days': int((dates.max() - dates.min()).days),
                    })
            except Exception:
                pass

        return stats

    def _recommend_transformations(
        self,
        series: pd.Series,
        data_type: DataType,
        semantic_type: SemanticType
    ) -> List[str]:
        """Recommend transformations for the column"""
        recommendations = []

        # Missing value handling
        if series.isnull().any():
            null_pct = series.isnull().mean() * 100
            if null_pct < 5:
                recommendations.append(f"DROP_NULLS (only {null_pct:.1f}% missing)")
            elif data_type in [DataType.INTEGER, DataType.FLOAT]:
                recommendations.append("IMPUTE_MEDIAN or IMPUTE_MEAN")
            elif data_type == DataType.CATEGORICAL:
                recommendations.append("IMPUTE_MODE or IMPUTE_UNKNOWN")
            else:
                recommendations.append("IMPUTE_CONSTANT('unknown')")

        # Type-specific recommendations
        if data_type == DataType.CATEGORICAL:
            unique_ratio = series.nunique() / len(series)
            if unique_ratio < 0.01:
                recommendations.append("ONE_HOT_ENCODE")
            else:
                recommendations.append("LABEL_ENCODE or TARGET_ENCODE")

        if data_type in [DataType.INTEGER, DataType.FLOAT]:
            recommendations.append("NORMALIZE (MinMax or StandardScaler)")

        if data_type in [DataType.DATE, DataType.DATETIME]:
            recommendations.append("EXTRACT_DATE_FEATURES (year, month, day, dayofweek)")

        if data_type == DataType.TEXT:
            recommendations.append("TEXT_VECTORIZE (TF-IDF or embeddings)")

        # Semantic-specific recommendations
        if semantic_type == SemanticType.PRICE:
            recommendations.append("LOG_TRANSFORM (if right-skewed)")

        if semantic_type in [SemanticType.LATITUDE, SemanticType.LONGITUDE]:
            recommendations.append("GEOHASH_ENCODE")

        return recommendations

    def _detect_target_candidates(
        self,
        df: pd.DataFrame,
        column_schemas: List[ColumnSchema]
    ) -> List[str]:
        """Detect likely target columns for ML"""
        candidates = []

        for schema in column_schemas:
            # Numeric targets
            if schema.semantic_type in [
                SemanticType.REVENUE, SemanticType.PRICE,
                SemanticType.QUANTITY, SemanticType.SCORE, SemanticType.RATING
            ]:
                candidates.append(schema.name)

            # Categorical targets
            if schema.semantic_type == SemanticType.STATUS:
                candidates.append(schema.name)

            # Boolean targets
            if schema.data_type == DataType.BOOLEAN:
                candidates.append(schema.name)

            # Low cardinality categorical
            if schema.data_type == DataType.CATEGORICAL:
                unique_count = schema.statistics.get('unique_count', 0)
                if 2 <= unique_count <= 20:
                    candidates.append(schema.name)

        return candidates

    def _generate_recommendations(
        self,
        column_schemas: List[ColumnSchema],
        df: pd.DataFrame
    ) -> List[str]:
        """Generate overall schema recommendations"""
        recommendations = []

        # Check for date columns
        date_cols = [s for s in column_schemas if s.data_type in [DataType.DATE, DataType.DATETIME]]
        if date_cols:
            recommendations.append(f"Set '{date_cols[0].name}' as index for time series analysis")
        else:
            recommendations.append("Consider adding a date/timestamp column for temporal analysis")

        # Check for ID columns
        id_cols = [s for s in column_schemas if s.semantic_type == SemanticType.ID]
        if not id_cols:
            recommendations.append("Consider adding a unique identifier column")

        # Check for high cardinality categoricals
        for schema in column_schemas:
            if schema.data_type == DataType.STRING:
                unique_ratio = schema.statistics.get('unique_count', 0) / df.shape[0]
                if 0.05 < unique_ratio < 0.5:
                    recommendations.append(
                        f"Column '{schema.name}' may benefit from categorical encoding"
                    )

        # Check for potential data quality issues
        null_heavy = [s for s in column_schemas if s.statistics.get('null_count', 0) / len(df) > 0.3]
        if null_heavy:
            recommendations.append(
                f"Columns with >30% missing: {', '.join(s.name for s in null_heavy)}"
            )

        return recommendations

    def _empty_schema(self, metadata: Dict[str, Any]) -> InferredSchema:
        """Return empty schema for empty data"""
        return InferredSchema(
            columns=[],
            row_count=0,
            detected_delimiter=metadata.get('delimiter'),
            detected_encoding=metadata.get('encoding', 'utf-8'),
            has_header=True,
            date_columns=[],
            numeric_columns=[],
            categorical_columns=[],
            id_columns=[],
            target_column_candidates=[],
            recommendations=['No data to analyze'],
        )


# Singleton instance
schema_inference_service = SchemaInferenceService()
