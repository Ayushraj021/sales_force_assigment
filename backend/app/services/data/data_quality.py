"""
Data Quality Scoring Service

Comprehensive data quality assessment with scoring metrics for:
- Completeness: Missing value analysis
- Accuracy: Data type conformance, range validation
- Consistency: Duplicate detection, format consistency
- Timeliness: Data freshness analysis
- Uniqueness: Duplicate and near-duplicate detection
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import re
from collections import Counter


class QualityDimension(str, Enum):
    """Data quality dimensions"""
    COMPLETENESS = "completeness"
    ACCURACY = "accuracy"
    CONSISTENCY = "consistency"
    TIMELINESS = "timeliness"
    UNIQUENESS = "uniqueness"
    VALIDITY = "validity"


@dataclass
class ColumnQualityScore:
    """Quality score for a single column"""
    column_name: str
    completeness_score: float  # 0-100
    accuracy_score: float  # 0-100
    consistency_score: float  # 0-100
    validity_score: float  # 0-100
    overall_score: float  # 0-100
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DataQualityReport:
    """Comprehensive data quality report"""
    overall_score: float  # 0-100
    grade: str  # A, B, C, D, F
    dimension_scores: Dict[str, float]
    column_scores: List[ColumnQualityScore]
    summary: Dict[str, Any]
    issues: List[Dict[str, Any]]
    recommendations: List[str]
    profiling_stats: Dict[str, Any]
    created_at: str


class DataQualityService:
    """Service for comprehensive data quality assessment"""

    # Grade thresholds
    GRADE_THRESHOLDS = {
        'A': 90,
        'B': 80,
        'C': 70,
        'D': 60,
        'F': 0
    }

    # Dimension weights for overall score
    DIMENSION_WEIGHTS = {
        QualityDimension.COMPLETENESS: 0.25,
        QualityDimension.ACCURACY: 0.20,
        QualityDimension.CONSISTENCY: 0.20,
        QualityDimension.VALIDITY: 0.20,
        QualityDimension.UNIQUENESS: 0.15,
    }

    def __init__(self):
        self.date_patterns = [
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
            r'\d{2}/\d{2}/\d{4}',  # MM/DD/YYYY
            r'\d{2}-\d{2}-\d{4}',  # DD-MM-YYYY
            r'\d{4}/\d{2}/\d{2}',  # YYYY/MM/DD
        ]
        self.email_pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        self.phone_pattern = r'^[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}$'

    def assess_quality(
        self,
        df: pd.DataFrame,
        date_column: Optional[str] = None,
        expected_schema: Optional[Dict[str, str]] = None,
        freshness_threshold_days: int = 7,
    ) -> DataQualityReport:
        """
        Perform comprehensive data quality assessment

        Args:
            df: DataFrame to assess
            date_column: Column containing dates for timeliness check
            expected_schema: Expected column types {column_name: dtype}
            freshness_threshold_days: Days threshold for data freshness

        Returns:
            DataQualityReport with detailed quality metrics
        """
        if df.empty:
            return self._empty_report()

        # Calculate dimension scores
        completeness_score = self._assess_completeness(df)
        accuracy_score = self._assess_accuracy(df, expected_schema)
        consistency_score = self._assess_consistency(df)
        validity_score = self._assess_validity(df)
        uniqueness_score = self._assess_uniqueness(df)
        timeliness_score = self._assess_timeliness(df, date_column, freshness_threshold_days)

        dimension_scores = {
            QualityDimension.COMPLETENESS.value: completeness_score,
            QualityDimension.ACCURACY.value: accuracy_score,
            QualityDimension.CONSISTENCY.value: consistency_score,
            QualityDimension.VALIDITY.value: validity_score,
            QualityDimension.UNIQUENESS.value: uniqueness_score,
            QualityDimension.TIMELINESS.value: timeliness_score,
        }

        # Calculate overall score (weighted average)
        overall_score = (
            completeness_score * self.DIMENSION_WEIGHTS[QualityDimension.COMPLETENESS] +
            accuracy_score * self.DIMENSION_WEIGHTS[QualityDimension.ACCURACY] +
            consistency_score * self.DIMENSION_WEIGHTS[QualityDimension.CONSISTENCY] +
            validity_score * self.DIMENSION_WEIGHTS[QualityDimension.VALIDITY] +
            uniqueness_score * self.DIMENSION_WEIGHTS[QualityDimension.UNIQUENESS]
        )

        # Calculate column-level scores
        column_scores = self._assess_columns(df)

        # Collect issues and recommendations
        issues = self._collect_issues(df, dimension_scores)
        recommendations = self._generate_recommendations(df, dimension_scores, issues)

        # Generate profiling statistics
        profiling_stats = self._generate_profiling_stats(df)

        # Calculate grade
        grade = self._calculate_grade(overall_score)

        # Generate summary
        summary = {
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'total_cells': df.size,
            'missing_cells': df.isnull().sum().sum(),
            'missing_percentage': (df.isnull().sum().sum() / df.size) * 100,
            'duplicate_rows': df.duplicated().sum(),
            'memory_usage_mb': df.memory_usage(deep=True).sum() / (1024 * 1024),
            'numeric_columns': len(df.select_dtypes(include=[np.number]).columns),
            'categorical_columns': len(df.select_dtypes(include=['object', 'category']).columns),
            'datetime_columns': len(df.select_dtypes(include=['datetime64']).columns),
        }

        return DataQualityReport(
            overall_score=round(overall_score, 2),
            grade=grade,
            dimension_scores={k: round(v, 2) for k, v in dimension_scores.items()},
            column_scores=column_scores,
            summary=summary,
            issues=issues,
            recommendations=recommendations,
            profiling_stats=profiling_stats,
            created_at=datetime.utcnow().isoformat(),
        )

    def _assess_completeness(self, df: pd.DataFrame) -> float:
        """Assess data completeness (missing values)"""
        if df.empty:
            return 0.0

        total_cells = df.size
        missing_cells = df.isnull().sum().sum()

        # Also count empty strings as missing
        empty_strings = (df == '').sum().sum() if df.select_dtypes(include=['object']).shape[1] > 0 else 0

        completeness = ((total_cells - missing_cells - empty_strings) / total_cells) * 100
        return max(0, min(100, completeness))

    def _assess_accuracy(self, df: pd.DataFrame, expected_schema: Optional[Dict[str, str]] = None) -> float:
        """Assess data accuracy (type conformance, valid values)"""
        if df.empty:
            return 0.0

        scores = []

        for col in df.columns:
            col_score = 100.0
            series = df[col].dropna()

            if len(series) == 0:
                scores.append(50.0)  # Neutral score for empty columns
                continue

            # Check for expected schema conformance
            if expected_schema and col in expected_schema:
                expected_type = expected_schema[col]
                try:
                    if expected_type in ['int', 'int64', 'integer']:
                        valid = pd.to_numeric(series, errors='coerce').notna().mean() * 100
                    elif expected_type in ['float', 'float64', 'number']:
                        valid = pd.to_numeric(series, errors='coerce').notna().mean() * 100
                    elif expected_type in ['date', 'datetime']:
                        valid = pd.to_datetime(series, errors='coerce').notna().mean() * 100
                    else:
                        valid = 100.0
                    col_score = valid
                except Exception:
                    col_score = 50.0
            else:
                # Auto-detect and validate
                if df[col].dtype in ['int64', 'float64']:
                    # Check for unreasonable values (extreme outliers)
                    if series.std() > 0:
                        z_scores = np.abs((series - series.mean()) / series.std())
                        extreme_outliers = (z_scores > 5).mean()
                        col_score = (1 - extreme_outliers) * 100
                elif df[col].dtype == 'object':
                    # Check for mixed types in string column
                    type_counts = series.apply(type).value_counts()
                    dominant_type_ratio = type_counts.iloc[0] / len(series) if len(type_counts) > 0 else 1
                    col_score = dominant_type_ratio * 100

            scores.append(col_score)

        return np.mean(scores) if scores else 0.0

    def _assess_consistency(self, df: pd.DataFrame) -> float:
        """Assess data consistency (format uniformity, standardization)"""
        if df.empty:
            return 0.0

        scores = []

        for col in df.columns:
            series = df[col].dropna()
            if len(series) == 0:
                scores.append(100.0)
                continue

            col_score = 100.0

            if df[col].dtype == 'object':
                # Check case consistency
                if series.str.match(r'^[A-Z]').any() and series.str.match(r'^[a-z]').any():
                    upper_ratio = series.str.match(r'^[A-Z]').mean()
                    col_score -= abs(0.5 - upper_ratio) * 20  # Penalize mixed case

                # Check whitespace consistency
                has_leading_space = series.str.match(r'^\s').any()
                has_trailing_space = series.str.match(r'\s$').any()
                if has_leading_space or has_trailing_space:
                    col_score -= 10

                # Check for consistent formatting (dates, phones, etc.)
                unique_formats = self._detect_format_variations(series)
                if unique_formats > 1:
                    col_score -= min(30, unique_formats * 5)

            scores.append(max(0, col_score))

        return np.mean(scores) if scores else 0.0

    def _assess_validity(self, df: pd.DataFrame) -> float:
        """Assess data validity (values within expected ranges/formats)"""
        if df.empty:
            return 0.0

        scores = []

        for col in df.columns:
            series = df[col].dropna()
            if len(series) == 0:
                scores.append(100.0)
                continue

            col_score = 100.0

            # Numeric validation
            if df[col].dtype in ['int64', 'float64']:
                # Check for negative values where positives expected (heuristic)
                if series.min() < 0 and 'count' in col.lower() or 'amount' in col.lower():
                    negative_ratio = (series < 0).mean()
                    col_score -= negative_ratio * 50

                # Check for zeros where they might be invalid
                if 'price' in col.lower() or 'revenue' in col.lower():
                    zero_ratio = (series == 0).mean()
                    if zero_ratio > 0.5:
                        col_score -= 20

            # String validation
            elif df[col].dtype == 'object':
                # Check for email validity
                if 'email' in col.lower():
                    valid_emails = series.str.match(self.email_pattern, na=False).mean()
                    col_score = valid_emails * 100

                # Check for phone validity
                elif 'phone' in col.lower() or 'tel' in col.lower():
                    valid_phones = series.str.match(self.phone_pattern, na=False).mean()
                    col_score = valid_phones * 100

            scores.append(max(0, col_score))

        return np.mean(scores) if scores else 0.0

    def _assess_uniqueness(self, df: pd.DataFrame) -> float:
        """Assess data uniqueness (duplicate detection)"""
        if df.empty or len(df) == 0:
            return 100.0

        # Row-level duplicates
        duplicate_ratio = df.duplicated().mean()
        row_uniqueness = (1 - duplicate_ratio) * 100

        # Check potential key columns for uniqueness
        potential_keys = [col for col in df.columns if 'id' in col.lower() or 'key' in col.lower()]
        key_uniqueness_scores = []

        for col in potential_keys:
            if df[col].dtype == 'object' or df[col].dtype in ['int64', 'float64']:
                unique_ratio = df[col].nunique() / len(df)
                key_uniqueness_scores.append(unique_ratio * 100)

        if key_uniqueness_scores:
            return (row_uniqueness + np.mean(key_uniqueness_scores)) / 2

        return row_uniqueness

    def _assess_timeliness(
        self,
        df: pd.DataFrame,
        date_column: Optional[str],
        threshold_days: int
    ) -> float:
        """Assess data timeliness (freshness)"""
        if df.empty:
            return 0.0

        # Find date column if not specified
        if not date_column:
            date_columns = df.select_dtypes(include=['datetime64']).columns.tolist()
            if not date_columns:
                # Try to find date-like columns
                for col in df.columns:
                    if 'date' in col.lower() or 'time' in col.lower():
                        try:
                            pd.to_datetime(df[col])
                            date_column = col
                            break
                        except Exception:
                            continue
            else:
                date_column = date_columns[0]

        if not date_column or date_column not in df.columns:
            return 100.0  # Cannot assess, assume fresh

        try:
            dates = pd.to_datetime(df[date_column], errors='coerce')
            max_date = dates.max()

            if pd.isna(max_date):
                return 50.0

            days_old = (datetime.now() - max_date).days

            if days_old <= threshold_days:
                return 100.0
            elif days_old <= threshold_days * 2:
                return 80.0
            elif days_old <= threshold_days * 4:
                return 60.0
            elif days_old <= threshold_days * 8:
                return 40.0
            else:
                return 20.0
        except Exception:
            return 50.0

    def _assess_columns(self, df: pd.DataFrame) -> List[ColumnQualityScore]:
        """Assess quality for each column individually"""
        column_scores = []

        for col in df.columns:
            series = df[col]

            # Completeness
            completeness = (1 - series.isnull().mean()) * 100

            # Accuracy (type consistency)
            if series.dtype == 'object':
                type_counts = series.dropna().apply(type).value_counts()
                accuracy = (type_counts.iloc[0] / len(series.dropna()) * 100) if len(type_counts) > 0 else 100
            else:
                accuracy = 100.0

            # Consistency (format uniformity)
            consistency = 100.0
            if series.dtype == 'object':
                non_null = series.dropna()
                if len(non_null) > 0:
                    # Check length variance
                    lengths = non_null.str.len()
                    if lengths.std() > lengths.mean() * 0.5:
                        consistency -= 20

            # Validity
            validity = 100.0
            if series.dtype in ['int64', 'float64']:
                # Check for outliers
                if series.std() > 0:
                    z_scores = np.abs((series - series.mean()) / series.std())
                    outlier_ratio = (z_scores > 3).mean()
                    validity = (1 - outlier_ratio) * 100

            # Overall
            overall = (completeness + accuracy + consistency + validity) / 4

            # Issues
            issues = []
            if completeness < 90:
                issues.append(f"{100-completeness:.1f}% missing values")
            if accuracy < 90:
                issues.append("Mixed data types detected")
            if consistency < 90:
                issues.append("Inconsistent formatting")
            if validity < 90:
                issues.append("Potential outliers or invalid values")

            # Recommendations
            recommendations = []
            if completeness < 90:
                recommendations.append("Consider imputation or filtering missing values")
            if accuracy < 90:
                recommendations.append("Standardize data types")
            if consistency < 90:
                recommendations.append("Apply formatting standardization")

            # Statistics
            stats = {
                'dtype': str(series.dtype),
                'null_count': int(series.isnull().sum()),
                'null_percentage': round(series.isnull().mean() * 100, 2),
                'unique_count': int(series.nunique()),
                'unique_percentage': round(series.nunique() / len(series) * 100, 2),
            }

            if series.dtype in ['int64', 'float64']:
                stats.update({
                    'mean': round(series.mean(), 4) if not series.isnull().all() else None,
                    'std': round(series.std(), 4) if not series.isnull().all() else None,
                    'min': round(series.min(), 4) if not series.isnull().all() else None,
                    'max': round(series.max(), 4) if not series.isnull().all() else None,
                    'median': round(series.median(), 4) if not series.isnull().all() else None,
                })
            elif series.dtype == 'object':
                value_counts = series.value_counts()
                stats.update({
                    'most_common': value_counts.index[0] if len(value_counts) > 0 else None,
                    'most_common_count': int(value_counts.iloc[0]) if len(value_counts) > 0 else 0,
                    'avg_length': round(series.dropna().str.len().mean(), 2) if len(series.dropna()) > 0 else 0,
                })

            column_scores.append(ColumnQualityScore(
                column_name=col,
                completeness_score=round(completeness, 2),
                accuracy_score=round(accuracy, 2),
                consistency_score=round(consistency, 2),
                validity_score=round(validity, 2),
                overall_score=round(overall, 2),
                issues=issues,
                recommendations=recommendations,
                statistics=stats,
            ))

        return column_scores

    def _detect_format_variations(self, series: pd.Series) -> int:
        """Detect number of different formats in a string column"""
        if len(series) == 0:
            return 1

        # Sample for performance
        sample = series.sample(min(1000, len(series)), random_state=42) if len(series) > 1000 else series

        formats = set()
        for val in sample:
            if pd.isna(val):
                continue
            val_str = str(val)

            # Detect format pattern
            pattern = re.sub(r'[A-Za-z]+', 'A', val_str)
            pattern = re.sub(r'\d+', 'N', pattern)
            formats.add(pattern)

        return len(formats)

    def _collect_issues(self, df: pd.DataFrame, dimension_scores: Dict[str, float]) -> List[Dict[str, Any]]:
        """Collect all data quality issues"""
        issues = []

        # Completeness issues
        if dimension_scores[QualityDimension.COMPLETENESS.value] < 90:
            for col in df.columns:
                null_pct = df[col].isnull().mean() * 100
                if null_pct > 10:
                    issues.append({
                        'dimension': QualityDimension.COMPLETENESS.value,
                        'severity': 'high' if null_pct > 50 else 'medium' if null_pct > 20 else 'low',
                        'column': col,
                        'message': f"Column '{col}' has {null_pct:.1f}% missing values",
                        'metric_value': null_pct,
                    })

        # Uniqueness issues
        if dimension_scores[QualityDimension.UNIQUENESS.value] < 90:
            dup_count = df.duplicated().sum()
            if dup_count > 0:
                issues.append({
                    'dimension': QualityDimension.UNIQUENESS.value,
                    'severity': 'high' if dup_count > len(df) * 0.1 else 'medium',
                    'column': None,
                    'message': f"Found {dup_count} duplicate rows ({dup_count/len(df)*100:.1f}%)",
                    'metric_value': dup_count,
                })

        # Consistency issues
        for col in df.select_dtypes(include=['object']).columns:
            series = df[col].dropna()
            if len(series) > 0:
                # Check for leading/trailing whitespace
                whitespace_count = series.str.match(r'^\s|\s$').sum()
                if whitespace_count > 0:
                    issues.append({
                        'dimension': QualityDimension.CONSISTENCY.value,
                        'severity': 'low',
                        'column': col,
                        'message': f"Column '{col}' has {whitespace_count} values with leading/trailing whitespace",
                        'metric_value': whitespace_count,
                    })

        return issues

    def _generate_recommendations(
        self,
        df: pd.DataFrame,
        dimension_scores: Dict[str, float],
        issues: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []

        if dimension_scores[QualityDimension.COMPLETENESS.value] < 90:
            recommendations.append("Consider imputing missing values using mean/median for numeric columns or mode for categorical columns")
            recommendations.append("Review data collection process to reduce missing values at source")

        if dimension_scores[QualityDimension.UNIQUENESS.value] < 95:
            recommendations.append("Remove duplicate rows using deduplication with appropriate key columns")
            recommendations.append("Investigate source of duplicates in data pipeline")

        if dimension_scores[QualityDimension.CONSISTENCY.value] < 90:
            recommendations.append("Standardize text formatting (trim whitespace, consistent casing)")
            recommendations.append("Apply consistent date/time formatting across all date columns")

        if dimension_scores[QualityDimension.ACCURACY.value] < 90:
            recommendations.append("Validate numeric ranges and fix outliers")
            recommendations.append("Ensure data types match expected schema")

        if dimension_scores[QualityDimension.VALIDITY.value] < 90:
            recommendations.append("Validate email, phone, and other formatted fields")
            recommendations.append("Apply business rules validation")

        return recommendations

    def _generate_profiling_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate comprehensive profiling statistics"""
        stats = {
            'row_count': len(df),
            'column_count': len(df.columns),
            'memory_usage_bytes': int(df.memory_usage(deep=True).sum()),
            'dtypes': df.dtypes.astype(str).to_dict(),
            'columns': {},
        }

        for col in df.columns:
            series = df[col]
            col_stats = {
                'dtype': str(series.dtype),
                'null_count': int(series.isnull().sum()),
                'null_percentage': round(series.isnull().mean() * 100, 2),
                'unique_count': int(series.nunique()),
                'unique_percentage': round(series.nunique() / len(series) * 100, 2) if len(series) > 0 else 0,
            }

            if series.dtype in ['int64', 'float64']:
                col_stats.update({
                    'mean': float(series.mean()) if not series.isnull().all() else None,
                    'std': float(series.std()) if not series.isnull().all() else None,
                    'min': float(series.min()) if not series.isnull().all() else None,
                    'max': float(series.max()) if not series.isnull().all() else None,
                    'median': float(series.median()) if not series.isnull().all() else None,
                    'q1': float(series.quantile(0.25)) if not series.isnull().all() else None,
                    'q3': float(series.quantile(0.75)) if not series.isnull().all() else None,
                    'skewness': float(series.skew()) if not series.isnull().all() else None,
                    'kurtosis': float(series.kurtosis()) if not series.isnull().all() else None,
                    'zeros_count': int((series == 0).sum()),
                    'negative_count': int((series < 0).sum()),
                })
            elif series.dtype == 'object':
                value_counts = series.value_counts().head(10)
                col_stats.update({
                    'top_values': value_counts.to_dict(),
                    'avg_length': float(series.dropna().str.len().mean()) if len(series.dropna()) > 0 else 0,
                    'min_length': int(series.dropna().str.len().min()) if len(series.dropna()) > 0 else 0,
                    'max_length': int(series.dropna().str.len().max()) if len(series.dropna()) > 0 else 0,
                    'empty_strings': int((series == '').sum()),
                })
            elif pd.api.types.is_datetime64_any_dtype(series):
                col_stats.update({
                    'min_date': str(series.min()) if not series.isnull().all() else None,
                    'max_date': str(series.max()) if not series.isnull().all() else None,
                    'date_range_days': int((series.max() - series.min()).days) if not series.isnull().all() else None,
                })

            stats['columns'][col] = col_stats

        return stats

    def _calculate_grade(self, score: float) -> str:
        """Calculate letter grade from score"""
        for grade, threshold in self.GRADE_THRESHOLDS.items():
            if score >= threshold:
                return grade
        return 'F'

    def _empty_report(self) -> DataQualityReport:
        """Return empty report for empty DataFrame"""
        return DataQualityReport(
            overall_score=0.0,
            grade='F',
            dimension_scores={dim.value: 0.0 for dim in QualityDimension},
            column_scores=[],
            summary={'total_rows': 0, 'total_columns': 0},
            issues=[{'dimension': 'completeness', 'severity': 'high', 'message': 'Empty dataset'}],
            recommendations=['Provide data to assess quality'],
            profiling_stats={},
            created_at=datetime.utcnow().isoformat(),
        )


# Singleton instance
data_quality_service = DataQualityService()
