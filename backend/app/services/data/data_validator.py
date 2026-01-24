"""
Data Validator

Data quality validation and schema enforcement.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable, Union
from enum import Enum
import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class RuleType(str, Enum):
    """Types of validation rules."""
    NOT_NULL = "not_null"
    UNIQUE = "unique"
    IN_RANGE = "in_range"
    IN_SET = "in_set"
    REGEX = "regex"
    CUSTOM = "custom"
    DATA_TYPE = "data_type"
    SCHEMA = "schema"


@dataclass
class ValidationRule:
    """A single validation rule."""
    name: str
    rule_type: RuleType
    column: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    severity: str = "error"  # error, warning


@dataclass
class ValidationResult:
    """Result of data validation."""
    is_valid: bool
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)
    row_count: int = 0
    column_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "statistics": self.statistics,
            "row_count": self.row_count,
            "column_count": self.column_count,
        }


class DataValidator:
    """
    Data Validation Service.

    Features:
    - Schema validation
    - Data quality checks
    - Custom validation rules
    - Detailed error reporting

    Example:
        validator = DataValidator()

        # Add rules
        validator.add_rule(ValidationRule(
            name="sales_not_null",
            rule_type=RuleType.NOT_NULL,
            column="sales"
        ))

        # Validate data
        result = validator.validate(df)

        if not result.is_valid:
            print(result.errors)
    """

    def __init__(self):
        self._rules: List[ValidationRule] = []
        self._custom_validators: Dict[str, Callable] = {}

    def add_rule(self, rule: ValidationRule) -> None:
        """Add a validation rule."""
        self._rules.append(rule)

    def add_rules(self, rules: List[ValidationRule]) -> None:
        """Add multiple validation rules."""
        self._rules.extend(rules)

    def add_custom_validator(
        self,
        name: str,
        validator: Callable[[pd.DataFrame, Dict[str, Any]], List[str]],
    ) -> None:
        """
        Add a custom validator function.

        Args:
            name: Validator name
            validator: Function that takes DataFrame and params, returns errors
        """
        self._custom_validators[name] = validator

    def validate(self, df: pd.DataFrame) -> ValidationResult:
        """
        Validate a DataFrame.

        Args:
            df: DataFrame to validate

        Returns:
            ValidationResult
        """
        errors = []
        warnings = []

        for rule in self._rules:
            rule_errors = self._apply_rule(df, rule)

            for error in rule_errors:
                error_info = {
                    "rule": rule.name,
                    "column": rule.column,
                    "message": error,
                    "rule_type": rule.rule_type.value,
                }

                if rule.severity == "error":
                    errors.append(error_info)
                else:
                    warnings.append(error_info)

        # Calculate statistics
        statistics = self._calculate_statistics(df)

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            statistics=statistics,
            row_count=len(df),
            column_count=len(df.columns),
        )

    def _apply_rule(
        self,
        df: pd.DataFrame,
        rule: ValidationRule,
    ) -> List[str]:
        """Apply a single validation rule."""
        errors = []

        if rule.column and rule.column not in df.columns:
            if rule.rule_type != RuleType.SCHEMA:
                return [f"Column '{rule.column}' not found"]

        if rule.rule_type == RuleType.NOT_NULL:
            null_count = df[rule.column].isna().sum()
            if null_count > 0:
                errors.append(
                    rule.error_message or
                    f"Column '{rule.column}' has {null_count} null values"
                )

        elif rule.rule_type == RuleType.UNIQUE:
            duplicate_count = df[rule.column].duplicated().sum()
            if duplicate_count > 0:
                errors.append(
                    rule.error_message or
                    f"Column '{rule.column}' has {duplicate_count} duplicate values"
                )

        elif rule.rule_type == RuleType.IN_RANGE:
            min_val = rule.params.get("min")
            max_val = rule.params.get("max")

            if min_val is not None:
                below_min = (df[rule.column] < min_val).sum()
                if below_min > 0:
                    errors.append(
                        f"{below_min} values in '{rule.column}' below minimum {min_val}"
                    )

            if max_val is not None:
                above_max = (df[rule.column] > max_val).sum()
                if above_max > 0:
                    errors.append(
                        f"{above_max} values in '{rule.column}' above maximum {max_val}"
                    )

        elif rule.rule_type == RuleType.IN_SET:
            allowed_values = set(rule.params.get("values", []))
            invalid_values = set(df[rule.column].dropna().unique()) - allowed_values
            if invalid_values:
                errors.append(
                    f"Invalid values in '{rule.column}': {list(invalid_values)[:5]}"
                )

        elif rule.rule_type == RuleType.REGEX:
            import re
            pattern = rule.params.get("pattern", "")
            if pattern:
                non_matching = df[rule.column].dropna().apply(
                    lambda x: not bool(re.match(pattern, str(x)))
                ).sum()
                if non_matching > 0:
                    errors.append(
                        f"{non_matching} values in '{rule.column}' don't match pattern"
                    )

        elif rule.rule_type == RuleType.DATA_TYPE:
            expected_type = rule.params.get("dtype")
            if expected_type:
                actual_type = str(df[rule.column].dtype)
                if not actual_type.startswith(expected_type):
                    errors.append(
                        f"Column '{rule.column}' has type {actual_type}, expected {expected_type}"
                    )

        elif rule.rule_type == RuleType.SCHEMA:
            required_columns = rule.params.get("required_columns", [])
            missing = set(required_columns) - set(df.columns)
            if missing:
                errors.append(f"Missing required columns: {list(missing)}")

        elif rule.rule_type == RuleType.CUSTOM:
            validator_name = rule.params.get("validator")
            if validator_name in self._custom_validators:
                custom_errors = self._custom_validators[validator_name](df, rule.params)
                errors.extend(custom_errors)

        return errors

    def _calculate_statistics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate data statistics."""
        stats = {
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "total_cells": df.size,
            "null_cells": df.isna().sum().sum(),
            "null_percentage": df.isna().sum().sum() / df.size * 100 if df.size > 0 else 0,
            "duplicate_rows": df.duplicated().sum(),
            "memory_usage_mb": df.memory_usage(deep=True).sum() / (1024 * 1024),
        }

        # Column-level statistics
        column_stats = {}
        for col in df.columns:
            col_stats = {
                "dtype": str(df[col].dtype),
                "null_count": int(df[col].isna().sum()),
                "null_percentage": float(df[col].isna().mean() * 100),
                "unique_count": int(df[col].nunique()),
            }

            if df[col].dtype in [np.float64, np.int64]:
                col_stats.update({
                    "min": float(df[col].min()) if not df[col].isna().all() else None,
                    "max": float(df[col].max()) if not df[col].isna().all() else None,
                    "mean": float(df[col].mean()) if not df[col].isna().all() else None,
                    "std": float(df[col].std()) if not df[col].isna().all() else None,
                })

            column_stats[col] = col_stats

        stats["columns"] = column_stats
        return stats

    def validate_schema(
        self,
        df: pd.DataFrame,
        schema: Dict[str, str],
    ) -> ValidationResult:
        """
        Validate DataFrame against a schema.

        Args:
            df: DataFrame to validate
            schema: Dict mapping column names to expected dtypes

        Returns:
            ValidationResult
        """
        errors = []

        # Check for missing columns
        missing_cols = set(schema.keys()) - set(df.columns)
        if missing_cols:
            errors.append({
                "rule": "schema",
                "column": None,
                "message": f"Missing columns: {list(missing_cols)}",
            })

        # Check data types
        for col, expected_dtype in schema.items():
            if col in df.columns:
                actual_dtype = str(df[col].dtype)
                if not actual_dtype.startswith(expected_dtype):
                    errors.append({
                        "rule": "schema",
                        "column": col,
                        "message": f"Type mismatch: expected {expected_dtype}, got {actual_dtype}",
                    })

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            row_count=len(df),
            column_count=len(df.columns),
        )

    def create_profile(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Create a data profile/summary.

        Args:
            df: DataFrame to profile

        Returns:
            Profile dictionary
        """
        profile = {
            "overview": {
                "rows": len(df),
                "columns": len(df.columns),
                "memory_mb": df.memory_usage(deep=True).sum() / (1024 * 1024),
                "duplicates": df.duplicated().sum(),
            },
            "columns": {},
        }

        for col in df.columns:
            col_profile = {
                "dtype": str(df[col].dtype),
                "nulls": int(df[col].isna().sum()),
                "null_pct": round(df[col].isna().mean() * 100, 2),
                "unique": int(df[col].nunique()),
                "unique_pct": round(df[col].nunique() / len(df) * 100, 2),
            }

            if df[col].dtype in [np.float64, np.int64, np.float32, np.int32]:
                col_profile.update({
                    "min": df[col].min(),
                    "max": df[col].max(),
                    "mean": round(df[col].mean(), 4),
                    "median": df[col].median(),
                    "std": round(df[col].std(), 4),
                    "zeros": int((df[col] == 0).sum()),
                    "negatives": int((df[col] < 0).sum()),
                })

            elif df[col].dtype == "object" or str(df[col].dtype).startswith("str"):
                top_values = df[col].value_counts().head(5).to_dict()
                col_profile["top_values"] = top_values

            elif str(df[col].dtype).startswith("datetime"):
                col_profile.update({
                    "min_date": str(df[col].min()),
                    "max_date": str(df[col].max()),
                })

            profile["columns"][col] = col_profile

        return profile

    def clear_rules(self) -> None:
        """Clear all validation rules."""
        self._rules.clear()
