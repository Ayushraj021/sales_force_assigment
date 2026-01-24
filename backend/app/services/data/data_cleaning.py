"""
Advanced Data Cleaning Service

Comprehensive data cleaning and standardization:
- Fuzzy deduplication with similarity matching
- String standardization (case, whitespace, special chars)
- Value normalization and mapping
- Outlier handling
- Missing value imputation strategies
- Data type coercion
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Callable, Set
from enum import Enum
import pandas as pd
import numpy as np
from collections import defaultdict
import re
from difflib import SequenceMatcher
import unicodedata


class CleaningAction(str, Enum):
    """Types of cleaning actions"""
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


class ImputationStrategy(str, Enum):
    """Missing value imputation strategies"""
    DROP = "drop"
    MEAN = "mean"
    MEDIAN = "median"
    MODE = "mode"
    CONSTANT = "constant"
    FORWARD_FILL = "forward_fill"
    BACKWARD_FILL = "backward_fill"
    INTERPOLATE = "interpolate"
    KNN = "knn"


class OutlierStrategy(str, Enum):
    """Outlier handling strategies"""
    KEEP = "keep"
    REMOVE = "remove"
    CAP = "cap"  # Winsorize
    REPLACE_MEAN = "replace_mean"
    REPLACE_MEDIAN = "replace_median"


@dataclass
class CleaningResult:
    """Result of a cleaning operation"""
    action: CleaningAction
    column: Optional[str]
    rows_affected: int
    details: Dict[str, Any]
    before_sample: List[Any]
    after_sample: List[Any]


@dataclass
class CleaningReport:
    """Complete cleaning report"""
    original_rows: int
    final_rows: int
    original_columns: int
    final_columns: int
    actions_performed: List[CleaningResult]
    total_changes: int
    warnings: List[str]
    recommendations: List[str]


@dataclass
class DuplicateGroup:
    """Group of potential duplicate records"""
    group_id: int
    records: List[Dict[str, Any]]
    indices: List[int]
    similarity_score: float
    match_columns: List[str]


class DataCleaningService:
    """Service for advanced data cleaning operations"""

    # Common null representations
    NULL_VALUES = {
        '', 'null', 'none', 'na', 'n/a', 'nan', 'nil', '-', '--',
        'missing', 'unknown', 'undefined', '#n/a', '#na', '#null',
        'not available', 'not applicable'
    }

    def __init__(self):
        self.cleaning_history: List[CleaningResult] = []

    def clean_dataframe(
        self,
        df: pd.DataFrame,
        config: Optional[Dict[str, Any]] = None
    ) -> Tuple[pd.DataFrame, CleaningReport]:
        """
        Apply comprehensive cleaning to a DataFrame

        Args:
            df: Input DataFrame
            config: Cleaning configuration options

        Returns:
            Tuple of cleaned DataFrame and cleaning report
        """
        config = config or {}
        df_clean = df.copy()
        self.cleaning_history = []

        original_rows = len(df)
        original_columns = len(df.columns)

        # 1. Standardize null values
        if config.get('standardize_nulls', True):
            df_clean = self.standardize_nulls(df_clean)

        # 2. Trim whitespace
        if config.get('trim_whitespace', True):
            df_clean = self.trim_whitespace(df_clean)

        # 3. Normalize case (if specified)
        case_columns = config.get('normalize_case_columns', [])
        case_style = config.get('case_style', 'lower')
        for col in case_columns:
            if col in df_clean.columns:
                df_clean = self.normalize_case(df_clean, col, case_style)

        # 4. Remove exact duplicates
        if config.get('remove_duplicates', True):
            subset = config.get('duplicate_subset')
            df_clean = self.remove_duplicates(df_clean, subset=subset)

        # 5. Handle outliers
        outlier_config = config.get('outlier_config', {})
        for col, strategy in outlier_config.items():
            if col in df_clean.columns and df_clean[col].dtype in ['int64', 'float64']:
                df_clean = self.handle_outliers(
                    df_clean, col,
                    strategy=OutlierStrategy(strategy.get('strategy', 'keep')),
                    threshold=strategy.get('threshold', 3.0)
                )

        # 6. Impute missing values
        impute_config = config.get('impute_config', {})
        for col, strategy_config in impute_config.items():
            if col in df_clean.columns:
                df_clean = self.impute_missing(
                    df_clean, col,
                    strategy=ImputationStrategy(strategy_config.get('strategy', 'median')),
                    fill_value=strategy_config.get('fill_value')
                )

        # 7. Normalize specific formats
        if config.get('normalize_phones', False):
            phone_cols = config.get('phone_columns', [])
            for col in phone_cols:
                if col in df_clean.columns:
                    df_clean = self.normalize_phone(df_clean, col)

        if config.get('normalize_emails', False):
            email_cols = config.get('email_columns', [])
            for col in email_cols:
                if col in df_clean.columns:
                    df_clean = self.normalize_email(df_clean, col)

        # Generate report
        report = CleaningReport(
            original_rows=original_rows,
            final_rows=len(df_clean),
            original_columns=original_columns,
            final_columns=len(df_clean.columns),
            actions_performed=self.cleaning_history,
            total_changes=sum(a.rows_affected for a in self.cleaning_history),
            warnings=self._generate_warnings(df_clean),
            recommendations=self._generate_recommendations(df_clean, config),
        )

        return df_clean, report

    def standardize_nulls(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert various null representations to actual NaN"""
        df_clean = df.copy()
        rows_affected = 0

        for col in df_clean.select_dtypes(include=['object']).columns:
            mask = df_clean[col].astype(str).str.lower().str.strip().isin(self.NULL_VALUES)
            affected = mask.sum()
            if affected > 0:
                before_sample = df_clean.loc[mask, col].head(5).tolist()
                df_clean.loc[mask, col] = np.nan
                rows_affected += affected

                self.cleaning_history.append(CleaningResult(
                    action=CleaningAction.STANDARDIZE_NULLS,
                    column=col,
                    rows_affected=affected,
                    details={'null_values_found': list(set(before_sample))},
                    before_sample=before_sample,
                    after_sample=[np.nan] * len(before_sample),
                ))

        return df_clean

    def trim_whitespace(self, df: pd.DataFrame) -> pd.DataFrame:
        """Trim leading/trailing whitespace from string columns"""
        df_clean = df.copy()

        for col in df_clean.select_dtypes(include=['object']).columns:
            original = df_clean[col].copy()
            df_clean[col] = df_clean[col].astype(str).str.strip()
            df_clean.loc[df_clean[col] == 'nan', col] = np.nan

            # Count changes
            mask = (original.fillna('') != df_clean[col].fillna(''))
            affected = mask.sum()

            if affected > 0:
                self.cleaning_history.append(CleaningResult(
                    action=CleaningAction.TRIM_WHITESPACE,
                    column=col,
                    rows_affected=affected,
                    details={},
                    before_sample=original[mask].head(5).tolist(),
                    after_sample=df_clean.loc[mask, col].head(5).tolist(),
                ))

        return df_clean

    def normalize_case(
        self,
        df: pd.DataFrame,
        column: str,
        style: str = 'lower'
    ) -> pd.DataFrame:
        """Normalize text case in a column"""
        if column not in df.columns:
            return df

        df_clean = df.copy()
        original = df_clean[column].copy()

        if style == 'lower':
            df_clean[column] = df_clean[column].astype(str).str.lower()
        elif style == 'upper':
            df_clean[column] = df_clean[column].astype(str).str.upper()
        elif style == 'title':
            df_clean[column] = df_clean[column].astype(str).str.title()
        elif style == 'capitalize':
            df_clean[column] = df_clean[column].astype(str).str.capitalize()

        # Preserve nulls
        df_clean.loc[original.isna(), column] = np.nan

        mask = (original.fillna('') != df_clean[column].fillna(''))
        affected = mask.sum()

        if affected > 0:
            self.cleaning_history.append(CleaningResult(
                action=CleaningAction.NORMALIZE_CASE,
                column=column,
                rows_affected=affected,
                details={'style': style},
                before_sample=original[mask].head(5).tolist(),
                after_sample=df_clean.loc[mask, column].head(5).tolist(),
            ))

        return df_clean

    def remove_special_chars(
        self,
        df: pd.DataFrame,
        column: str,
        keep_chars: str = '',
        replacement: str = ''
    ) -> pd.DataFrame:
        """Remove special characters from a column"""
        if column not in df.columns:
            return df

        df_clean = df.copy()
        original = df_clean[column].copy()

        # Build pattern
        pattern = f'[^a-zA-Z0-9\\s{re.escape(keep_chars)}]'
        df_clean[column] = df_clean[column].astype(str).str.replace(
            pattern, replacement, regex=True
        )

        mask = (original.fillna('') != df_clean[column].fillna(''))
        affected = mask.sum()

        if affected > 0:
            self.cleaning_history.append(CleaningResult(
                action=CleaningAction.REMOVE_SPECIAL_CHARS,
                column=column,
                rows_affected=affected,
                details={'keep_chars': keep_chars, 'replacement': replacement},
                before_sample=original[mask].head(5).tolist(),
                after_sample=df_clean.loc[mask, column].head(5).tolist(),
            ))

        return df_clean

    def remove_duplicates(
        self,
        df: pd.DataFrame,
        subset: Optional[List[str]] = None,
        keep: str = 'first'
    ) -> pd.DataFrame:
        """Remove exact duplicate rows"""
        df_clean = df.copy()
        original_len = len(df_clean)

        duplicate_mask = df_clean.duplicated(subset=subset, keep=False)
        duplicates_sample = df_clean[duplicate_mask].head(5).to_dict('records')

        df_clean = df_clean.drop_duplicates(subset=subset, keep=keep)
        removed = original_len - len(df_clean)

        if removed > 0:
            self.cleaning_history.append(CleaningResult(
                action=CleaningAction.REMOVE_DUPLICATES,
                column=None,
                rows_affected=removed,
                details={'subset': subset, 'keep': keep},
                before_sample=duplicates_sample,
                after_sample=[],
            ))

        return df_clean

    def fuzzy_deduplicate(
        self,
        df: pd.DataFrame,
        columns: List[str],
        threshold: float = 0.85,
        keep: str = 'first'
    ) -> Tuple[pd.DataFrame, List[DuplicateGroup]]:
        """
        Find and optionally remove fuzzy duplicates

        Args:
            df: Input DataFrame
            columns: Columns to use for fuzzy matching
            threshold: Similarity threshold (0-1)
            keep: Which duplicate to keep ('first', 'last', 'none')

        Returns:
            Tuple of cleaned DataFrame and list of duplicate groups
        """
        df_clean = df.copy()
        duplicate_groups: List[DuplicateGroup] = []

        # Create combined string for comparison
        df_clean['_fuzzy_key'] = df_clean[columns].astype(str).agg(' '.join, axis=1)

        # Find similar records
        processed: Set[int] = set()
        group_id = 0

        for i, row in df_clean.iterrows():
            if i in processed:
                continue

            similar_indices = [i]
            base_key = row['_fuzzy_key']

            for j, other_row in df_clean.iloc[i+1:].iterrows():
                if j in processed:
                    continue

                similarity = self._calculate_similarity(base_key, other_row['_fuzzy_key'])

                if similarity >= threshold:
                    similar_indices.append(j)
                    processed.add(j)

            if len(similar_indices) > 1:
                group_records = df_clean.loc[similar_indices, columns].to_dict('records')
                duplicate_groups.append(DuplicateGroup(
                    group_id=group_id,
                    records=group_records,
                    indices=similar_indices,
                    similarity_score=threshold,
                    match_columns=columns,
                ))
                group_id += 1
                processed.update(similar_indices)

        # Remove duplicates based on keep strategy
        indices_to_remove = []
        for group in duplicate_groups:
            if keep == 'first':
                indices_to_remove.extend(group.indices[1:])
            elif keep == 'last':
                indices_to_remove.extend(group.indices[:-1])
            elif keep == 'none':
                indices_to_remove.extend(group.indices)

        df_clean = df_clean.drop(indices_to_remove)
        df_clean = df_clean.drop('_fuzzy_key', axis=1)

        self.cleaning_history.append(CleaningResult(
            action=CleaningAction.FUZZY_DEDUPLICATE,
            column=None,
            rows_affected=len(indices_to_remove),
            details={
                'columns': columns,
                'threshold': threshold,
                'groups_found': len(duplicate_groups),
            },
            before_sample=[g.records[0] for g in duplicate_groups[:5]],
            after_sample=[],
        ))

        return df_clean, duplicate_groups

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate string similarity using SequenceMatcher"""
        if not str1 or not str2:
            return 0.0
        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

    def impute_missing(
        self,
        df: pd.DataFrame,
        column: str,
        strategy: ImputationStrategy = ImputationStrategy.MEDIAN,
        fill_value: Any = None
    ) -> pd.DataFrame:
        """Impute missing values in a column"""
        if column not in df.columns:
            return df

        df_clean = df.copy()
        missing_mask = df_clean[column].isna()
        missing_count = missing_mask.sum()

        if missing_count == 0:
            return df_clean

        before_sample = df_clean.loc[missing_mask, column].head(5).tolist()

        if strategy == ImputationStrategy.DROP:
            df_clean = df_clean.dropna(subset=[column])
            after_sample = []
        elif strategy == ImputationStrategy.MEAN:
            fill = df_clean[column].mean()
            df_clean[column] = df_clean[column].fillna(fill)
            after_sample = [fill] * min(5, missing_count)
        elif strategy == ImputationStrategy.MEDIAN:
            fill = df_clean[column].median()
            df_clean[column] = df_clean[column].fillna(fill)
            after_sample = [fill] * min(5, missing_count)
        elif strategy == ImputationStrategy.MODE:
            fill = df_clean[column].mode().iloc[0] if len(df_clean[column].mode()) > 0 else None
            df_clean[column] = df_clean[column].fillna(fill)
            after_sample = [fill] * min(5, missing_count)
        elif strategy == ImputationStrategy.CONSTANT:
            df_clean[column] = df_clean[column].fillna(fill_value)
            after_sample = [fill_value] * min(5, missing_count)
        elif strategy == ImputationStrategy.FORWARD_FILL:
            df_clean[column] = df_clean[column].ffill()
            after_sample = df_clean.loc[missing_mask, column].head(5).tolist()
        elif strategy == ImputationStrategy.BACKWARD_FILL:
            df_clean[column] = df_clean[column].bfill()
            after_sample = df_clean.loc[missing_mask, column].head(5).tolist()
        elif strategy == ImputationStrategy.INTERPOLATE:
            df_clean[column] = df_clean[column].interpolate()
            after_sample = df_clean.loc[missing_mask, column].head(5).tolist()
        else:
            after_sample = before_sample

        self.cleaning_history.append(CleaningResult(
            action=CleaningAction.IMPUTE_MISSING,
            column=column,
            rows_affected=missing_count,
            details={'strategy': strategy.value, 'fill_value': fill_value},
            before_sample=before_sample,
            after_sample=after_sample,
        ))

        return df_clean

    def handle_outliers(
        self,
        df: pd.DataFrame,
        column: str,
        strategy: OutlierStrategy = OutlierStrategy.CAP,
        threshold: float = 3.0,
        method: str = 'zscore'
    ) -> pd.DataFrame:
        """Handle outliers in a numeric column"""
        if column not in df.columns or df[column].dtype not in ['int64', 'float64']:
            return df

        df_clean = df.copy()
        series = df_clean[column]

        # Detect outliers
        if method == 'zscore':
            z_scores = np.abs((series - series.mean()) / series.std())
            outlier_mask = z_scores > threshold
        elif method == 'iqr':
            Q1 = series.quantile(0.25)
            Q3 = series.quantile(0.75)
            IQR = Q3 - Q1
            outlier_mask = (series < Q1 - threshold * IQR) | (series > Q3 + threshold * IQR)
        else:
            return df_clean

        outlier_count = outlier_mask.sum()

        if outlier_count == 0:
            return df_clean

        before_sample = df_clean.loc[outlier_mask, column].head(5).tolist()

        if strategy == OutlierStrategy.REMOVE:
            df_clean = df_clean[~outlier_mask]
            after_sample = []
        elif strategy == OutlierStrategy.CAP:
            if method == 'zscore':
                lower = series.mean() - threshold * series.std()
                upper = series.mean() + threshold * series.std()
            else:
                Q1 = series.quantile(0.25)
                Q3 = series.quantile(0.75)
                IQR = Q3 - Q1
                lower = Q1 - threshold * IQR
                upper = Q3 + threshold * IQR

            df_clean[column] = df_clean[column].clip(lower=lower, upper=upper)
            after_sample = df_clean.loc[outlier_mask, column].head(5).tolist()
        elif strategy == OutlierStrategy.REPLACE_MEAN:
            df_clean.loc[outlier_mask, column] = series.mean()
            after_sample = [series.mean()] * min(5, outlier_count)
        elif strategy == OutlierStrategy.REPLACE_MEDIAN:
            df_clean.loc[outlier_mask, column] = series.median()
            after_sample = [series.median()] * min(5, outlier_count)
        else:
            after_sample = before_sample

        self.cleaning_history.append(CleaningResult(
            action=CleaningAction.HANDLE_OUTLIERS,
            column=column,
            rows_affected=outlier_count,
            details={'strategy': strategy.value, 'threshold': threshold, 'method': method},
            before_sample=before_sample,
            after_sample=after_sample,
        ))

        return df_clean

    def normalize_phone(self, df: pd.DataFrame, column: str) -> pd.DataFrame:
        """Normalize phone numbers to a standard format"""
        if column not in df.columns:
            return df

        df_clean = df.copy()
        original = df_clean[column].copy()

        def clean_phone(phone):
            if pd.isna(phone):
                return phone
            # Remove all non-numeric characters except +
            cleaned = re.sub(r'[^\d+]', '', str(phone))
            # Format as +X-XXX-XXX-XXXX if 10+ digits
            if len(cleaned) >= 10:
                digits = re.sub(r'\D', '', cleaned)
                if len(digits) == 10:
                    return f"+1-{digits[:3]}-{digits[3:6]}-{digits[6:]}"
                elif len(digits) == 11 and digits[0] == '1':
                    return f"+1-{digits[1:4]}-{digits[4:7]}-{digits[7:]}"
                elif len(digits) > 10:
                    return f"+{digits[:-10]}-{digits[-10:-7]}-{digits[-7:-4]}-{digits[-4:]}"
            return cleaned

        df_clean[column] = df_clean[column].apply(clean_phone)

        mask = (original.fillna('') != df_clean[column].fillna(''))
        affected = mask.sum()

        if affected > 0:
            self.cleaning_history.append(CleaningResult(
                action=CleaningAction.NORMALIZE_PHONE,
                column=column,
                rows_affected=affected,
                details={},
                before_sample=original[mask].head(5).tolist(),
                after_sample=df_clean.loc[mask, column].head(5).tolist(),
            ))

        return df_clean

    def normalize_email(self, df: pd.DataFrame, column: str) -> pd.DataFrame:
        """Normalize email addresses"""
        if column not in df.columns:
            return df

        df_clean = df.copy()
        original = df_clean[column].copy()

        def clean_email(email):
            if pd.isna(email):
                return email
            # Lowercase and strip
            cleaned = str(email).lower().strip()
            # Remove spaces
            cleaned = re.sub(r'\s+', '', cleaned)
            return cleaned

        df_clean[column] = df_clean[column].apply(clean_email)

        mask = (original.fillna('') != df_clean[column].fillna(''))
        affected = mask.sum()

        if affected > 0:
            self.cleaning_history.append(CleaningResult(
                action=CleaningAction.NORMALIZE_EMAIL,
                column=column,
                rows_affected=affected,
                details={},
                before_sample=original[mask].head(5).tolist(),
                after_sample=df_clean.loc[mask, column].head(5).tolist(),
            ))

        return df_clean

    def map_values(
        self,
        df: pd.DataFrame,
        column: str,
        mapping: Dict[str, str],
        default: Optional[str] = None
    ) -> pd.DataFrame:
        """Map values in a column using a mapping dictionary"""
        if column not in df.columns:
            return df

        df_clean = df.copy()
        original = df_clean[column].copy()

        if default is not None:
            df_clean[column] = df_clean[column].map(mapping).fillna(default)
        else:
            df_clean[column] = df_clean[column].map(lambda x: mapping.get(x, x))

        mask = (original.fillna('') != df_clean[column].fillna(''))
        affected = mask.sum()

        if affected > 0:
            self.cleaning_history.append(CleaningResult(
                action=CleaningAction.MAP_VALUES,
                column=column,
                rows_affected=affected,
                details={'mapping_size': len(mapping)},
                before_sample=original[mask].head(5).tolist(),
                after_sample=df_clean.loc[mask, column].head(5).tolist(),
            ))

        return df_clean

    def fix_encoding(self, df: pd.DataFrame, column: str) -> pd.DataFrame:
        """Fix encoding issues in text column"""
        if column not in df.columns:
            return df

        df_clean = df.copy()
        original = df_clean[column].copy()

        def fix_text(text):
            if pd.isna(text):
                return text
            try:
                # Normalize unicode
                normalized = unicodedata.normalize('NFKC', str(text))
                # Fix common encoding issues
                normalized = normalized.encode('utf-8', errors='ignore').decode('utf-8')
                return normalized
            except Exception:
                return text

        df_clean[column] = df_clean[column].apply(fix_text)

        mask = (original.fillna('') != df_clean[column].fillna(''))
        affected = mask.sum()

        if affected > 0:
            self.cleaning_history.append(CleaningResult(
                action=CleaningAction.FIX_ENCODING,
                column=column,
                rows_affected=affected,
                details={},
                before_sample=original[mask].head(5).tolist(),
                after_sample=df_clean.loc[mask, column].head(5).tolist(),
            ))

        return df_clean

    def _generate_warnings(self, df: pd.DataFrame) -> List[str]:
        """Generate warnings about potential data issues"""
        warnings = []

        # Check for remaining nulls
        null_cols = df.columns[df.isnull().any()].tolist()
        if null_cols:
            warnings.append(f"Columns still have missing values: {', '.join(null_cols)}")

        # Check for high cardinality
        for col in df.select_dtypes(include=['object']).columns:
            unique_ratio = df[col].nunique() / len(df)
            if unique_ratio > 0.9:
                warnings.append(f"Column '{col}' has very high cardinality ({df[col].nunique()} unique values)")

        return warnings

    def _generate_recommendations(self, df: pd.DataFrame, config: Dict[str, Any]) -> List[str]:
        """Generate recommendations for further cleaning"""
        recommendations = []

        # Check for columns that might need cleaning
        for col in df.select_dtypes(include=['object']).columns:
            # Check for inconsistent casing
            sample = df[col].dropna().head(100)
            if len(sample) > 0:
                has_upper = sample.str.match(r'^[A-Z]').any()
                has_lower = sample.str.match(r'^[a-z]').any()
                if has_upper and has_lower and col not in config.get('normalize_case_columns', []):
                    recommendations.append(f"Consider normalizing case for column '{col}'")

        # Check for potential date columns
        for col in df.select_dtypes(include=['object']).columns:
            sample = df[col].dropna().head(10)
            date_pattern = r'\d{2,4}[-/]\d{1,2}[-/]\d{1,4}'
            if sample.astype(str).str.match(date_pattern).any():
                recommendations.append(f"Column '{col}' may contain dates - consider parsing")

        return recommendations


# Singleton instance
data_cleaning_service = DataCleaningService()
