"""
GraphQL Types for Data Preprocessing Services

Types for:
- Data Quality Assessment
- Schema Inference
- Data Cleaning
- Feature Selection
"""

import strawberry
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum
from strawberry.scalars import JSON


# ============================================================================
# Data Quality Types
# ============================================================================

@strawberry.enum
class QualityDimension(Enum):
    COMPLETENESS = "completeness"
    ACCURACY = "accuracy"
    CONSISTENCY = "consistency"
    TIMELINESS = "timeliness"
    UNIQUENESS = "uniqueness"
    VALIDITY = "validity"


@strawberry.type
class ColumnQualityScoreType:
    column_name: str
    completeness_score: float
    accuracy_score: float
    consistency_score: float
    validity_score: float
    overall_score: float
    issues: List[str]
    recommendations: List[str]
    statistics: JSON


@strawberry.type
class QualityIssueType:
    dimension: str
    severity: str
    column: Optional[str]
    message: str
    metric_value: float


@strawberry.type
class DataQualityReportType:
    overall_score: float
    grade: str
    dimension_scores: JSON
    column_scores: List[ColumnQualityScoreType]
    summary: JSON
    issues: List[QualityIssueType]
    recommendations: List[str]
    profiling_stats: JSON
    created_at: str


# ============================================================================
# Schema Inference Types
# ============================================================================

@strawberry.enum
class InferredDataType(Enum):
    INTEGER = "integer"
    FLOAT = "float"
    STRING = "string"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    DATE = "date"
    TIME = "time"
    CATEGORICAL = "categorical"
    TEXT = "text"
    UNKNOWN = "unknown"


@strawberry.enum
class SemanticType(Enum):
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


@strawberry.type
class ColumnSchemaType:
    name: str
    data_type: InferredDataType
    semantic_type: SemanticType
    nullable: bool
    unique: bool
    sample_values: List[str]
    statistics: JSON
    format_pattern: Optional[str]
    recommended_transformations: List[str]
    confidence: float


@strawberry.type
class InferredSchemaType:
    columns: List[ColumnSchemaType]
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


# ============================================================================
# Data Cleaning Types
# ============================================================================

@strawberry.enum
class CleaningActionType(Enum):
    TRIM_WHITESPACE = "trim_whitespace"
    NORMALIZE_CASE = "normalize_case"
    REMOVE_SPECIAL_CHARS = "remove_special_chars"
    STANDARDIZE_NULLS = "standardize_nulls"
    FIX_ENCODING = "fix_encoding"
    REMOVE_DUPLICATES = "remove_duplicates"
    FUZZY_DEDUPLICATE = "fuzzy_deduplicate"
    IMPUTE_MISSING = "impute_missing"
    HANDLE_OUTLIERS = "handle_outliers"
    COERCE_TYPE = "coerce_type"
    MAP_VALUES = "map_values"
    NORMALIZE_DATES = "normalize_dates"
    NORMALIZE_PHONE = "normalize_phone"
    NORMALIZE_EMAIL = "normalize_email"


@strawberry.enum
class ImputationStrategyType(Enum):
    DROP = "drop"
    MEAN = "mean"
    MEDIAN = "median"
    MODE = "mode"
    CONSTANT = "constant"
    FORWARD_FILL = "forward_fill"
    BACKWARD_FILL = "backward_fill"
    INTERPOLATE = "interpolate"


@strawberry.enum
class OutlierStrategyType(Enum):
    KEEP = "keep"
    REMOVE = "remove"
    CAP = "cap"
    REPLACE_MEAN = "replace_mean"
    REPLACE_MEDIAN = "replace_median"


@strawberry.type
class CleaningResultType:
    action: str
    column: Optional[str]
    rows_affected: int
    details: JSON
    before_sample: List[str]
    after_sample: List[str]


@strawberry.type
class CleaningReportType:
    original_rows: int
    final_rows: int
    original_columns: int
    final_columns: int
    actions_performed: List[CleaningResultType]
    total_changes: int
    warnings: List[str]
    recommendations: List[str]


@strawberry.type
class DuplicateGroupType:
    group_id: int
    records: JSON
    indices: List[int]
    similarity_score: float
    match_columns: List[str]


@strawberry.type
class FuzzyDeduplicationResultType:
    rows_removed: int
    duplicate_groups: List[DuplicateGroupType]
    report: CleaningReportType


# ============================================================================
# Feature Selection Types
# ============================================================================

@strawberry.enum
class SelectionMethodType(Enum):
    VARIANCE_THRESHOLD = "variance_threshold"
    CORRELATION_FILTER = "correlation_filter"
    MUTUAL_INFORMATION = "mutual_information"
    ANOVA_F_TEST = "anova_f_test"
    CHI_SQUARE = "chi_square"
    IMPORTANCE_BASED = "importance_based"
    RFE = "recursive_feature_elimination"
    COMBINED = "combined"


@strawberry.type
class FeatureScoreType:
    name: str
    score: float
    rank: int
    selected: bool
    method: str
    statistics: JSON
    correlations: JSON
    recommendation: str


@strawberry.type
class CorrelationPairType:
    feature1: str
    feature2: str
    correlation: float
    p_value: Optional[float]
    method: str
    is_significant: bool


@strawberry.type
class FeatureSelectionResultType:
    selected_features: List[str]
    removed_features: List[str]
    feature_scores: List[FeatureScoreType]
    correlation_matrix: JSON
    high_correlations: List[CorrelationPairType]
    multicollinear_groups: List[List[str]]
    recommendations: List[str]
    summary: JSON


@strawberry.type
class CorrelationHeatmapType:
    columns: List[str]
    data: List[List[float]]
    annotations: List[List[str]]


@strawberry.type
class FeatureImportanceType:
    feature_scores: List[FeatureScoreType]
    method: str
    target_column: str


# ============================================================================
# Input Types
# ============================================================================

@strawberry.input
class DataQualityInput:
    dataset_id: strawberry.ID
    date_column: Optional[str] = None
    expected_schema: Optional[JSON] = None
    freshness_threshold_days: int = 7


@strawberry.input
class SchemaInferenceInput:
    dataset_id: strawberry.ID
    sample_size: int = 10000


@strawberry.input
class OutlierConfigInput:
    column: str
    strategy: OutlierStrategyType
    threshold: float = 3.0


@strawberry.input
class ImputeConfigInput:
    column: str
    strategy: ImputationStrategyType
    fill_value: Optional[str] = None


@strawberry.input
class DataCleaningInput:
    dataset_id: strawberry.ID
    standardize_nulls: bool = True
    trim_whitespace: bool = True
    remove_duplicates: bool = True
    duplicate_subset: Optional[List[str]] = None
    normalize_case_columns: Optional[List[str]] = None
    case_style: str = "lower"
    outlier_configs: Optional[List[OutlierConfigInput]] = None
    impute_configs: Optional[List[ImputeConfigInput]] = None
    normalize_phones: bool = False
    phone_columns: Optional[List[str]] = None
    normalize_emails: bool = False
    email_columns: Optional[List[str]] = None


@strawberry.input
class FuzzyDeduplicationInput:
    dataset_id: strawberry.ID
    columns: List[str]
    threshold: float = 0.85
    keep: str = "first"


@strawberry.input
class FeatureSelectionInput:
    dataset_id: strawberry.ID
    target_column: Optional[str] = None
    method: SelectionMethodType = SelectionMethodType.COMBINED
    correlation_method: str = "pearson"
    correlation_threshold: float = 0.8
    variance_threshold: float = 0.01
    max_features: Optional[int] = None


@strawberry.input
class FeatureImportanceInput:
    dataset_id: strawberry.ID
    target_column: str
    method: str = "random_forest"


@strawberry.input
class CorrelationHeatmapInput:
    dataset_id: strawberry.ID
    columns: Optional[List[str]] = None
    method: str = "pearson"
