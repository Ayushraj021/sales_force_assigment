"""
Row-Level Security (RLS)

Fine-grained data access control at the row level.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable, TypeVar, Generic, Union
from enum import Enum
from datetime import datetime
import logging
import operator

logger = logging.getLogger(__name__)

T = TypeVar("T")


class PolicyAction(str, Enum):
    """RLS policy actions."""
    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    ALL = "ALL"


class PolicyOperator(str, Enum):
    """Comparison operators for conditions."""
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    GREATER_THAN = "gt"
    GREATER_THAN_OR_EQUALS = "gte"
    LESS_THAN = "lt"
    LESS_THAN_OR_EQUALS = "lte"
    IN = "in"
    NOT_IN = "not_in"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"


@dataclass
class PolicyCondition:
    """A single condition in a policy."""
    column: str
    operator: PolicyOperator
    value: Any  # Can be a literal value or a context reference like "$user.organization_id"
    case_sensitive: bool = True


@dataclass
class PolicyRule:
    """A row-level security policy rule."""
    name: str
    table: str
    actions: List[PolicyAction]
    conditions: List[PolicyCondition]
    description: Optional[str] = None
    priority: int = 0
    enabled: bool = True
    roles: Optional[List[str]] = None  # If set, only applies to these roles


@dataclass
class SecurityContext:
    """Context for evaluating RLS policies."""
    user_id: str
    organization_id: str
    roles: List[str]
    tenant_id: Optional[str] = None
    department: Optional[str] = None
    region: Optional[str] = None
    custom_attributes: Dict[str, Any] = field(default_factory=dict)

    def get_attribute(self, path: str) -> Any:
        """Get attribute by dot-notation path."""
        if path.startswith("$user."):
            attr = path[6:]
            if hasattr(self, attr):
                return getattr(self, attr)
            return self.custom_attributes.get(attr)
        return None


@dataclass
class FilterResult:
    """Result of applying RLS filters."""
    sql_where: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    applied_policies: List[str] = field(default_factory=list)


class RLSManager:
    """
    Row-Level Security Manager.

    Features:
    - Policy-based row filtering
    - Multi-tenant isolation
    - Attribute-based access control
    - SQL WHERE clause generation
    - In-memory filtering

    Example:
        rls = RLSManager()
        rls.add_policy(PolicyRule(
            name="org_isolation",
            table="forecasts",
            actions=[PolicyAction.ALL],
            conditions=[
                PolicyCondition(
                    column="organization_id",
                    operator=PolicyOperator.EQUALS,
                    value="$user.organization_id"
                )
            ]
        ))

        # Get SQL filter
        result = rls.get_sql_filter("forecasts", PolicyAction.SELECT, context)
        query = f"SELECT * FROM forecasts WHERE {result.sql_where}"

        # Or filter in-memory
        filtered_data = rls.filter_rows(data, "forecasts", PolicyAction.SELECT, context)
    """

    OPERATOR_MAP = {
        PolicyOperator.EQUALS: operator.eq,
        PolicyOperator.NOT_EQUALS: operator.ne,
        PolicyOperator.GREATER_THAN: operator.gt,
        PolicyOperator.GREATER_THAN_OR_EQUALS: operator.ge,
        PolicyOperator.LESS_THAN: operator.lt,
        PolicyOperator.LESS_THAN_OR_EQUALS: operator.le,
    }

    SQL_OPERATOR_MAP = {
        PolicyOperator.EQUALS: "=",
        PolicyOperator.NOT_EQUALS: "!=",
        PolicyOperator.GREATER_THAN: ">",
        PolicyOperator.GREATER_THAN_OR_EQUALS: ">=",
        PolicyOperator.LESS_THAN: "<",
        PolicyOperator.LESS_THAN_OR_EQUALS: "<=",
        PolicyOperator.IN: "IN",
        PolicyOperator.NOT_IN: "NOT IN",
        PolicyOperator.CONTAINS: "LIKE",
        PolicyOperator.STARTS_WITH: "LIKE",
        PolicyOperator.ENDS_WITH: "LIKE",
        PolicyOperator.IS_NULL: "IS NULL",
        PolicyOperator.IS_NOT_NULL: "IS NOT NULL",
    }

    def __init__(self):
        self._policies: Dict[str, List[PolicyRule]] = {}

    def add_policy(self, policy: PolicyRule) -> None:
        """Add a row-level security policy."""
        if policy.table not in self._policies:
            self._policies[policy.table] = []

        # Remove existing policy with same name
        self._policies[policy.table] = [
            p for p in self._policies[policy.table] if p.name != policy.name
        ]

        self._policies[policy.table].append(policy)

        # Sort by priority
        self._policies[policy.table].sort(key=lambda p: p.priority, reverse=True)

        logger.debug(f"Added RLS policy: {policy.name} for table {policy.table}")

    def remove_policy(self, table: str, name: str) -> bool:
        """Remove a policy by name."""
        if table not in self._policies:
            return False

        original_count = len(self._policies[table])
        self._policies[table] = [p for p in self._policies[table] if p.name != name]

        return len(self._policies[table]) < original_count

    def get_policies(self, table: str) -> List[PolicyRule]:
        """Get all policies for a table."""
        return self._policies.get(table, [])

    def get_applicable_policies(
        self,
        table: str,
        action: PolicyAction,
        context: SecurityContext,
    ) -> List[PolicyRule]:
        """Get policies applicable to the action and context."""
        policies = self._policies.get(table, [])

        applicable = []
        for policy in policies:
            if not policy.enabled:
                continue

            # Check action
            if PolicyAction.ALL not in policy.actions and action not in policy.actions:
                continue

            # Check roles
            if policy.roles:
                if not any(role in policy.roles for role in context.roles):
                    continue

            applicable.append(policy)

        return applicable

    def get_sql_filter(
        self,
        table: str,
        action: PolicyAction,
        context: SecurityContext,
    ) -> FilterResult:
        """
        Generate SQL WHERE clause for RLS.

        Args:
            table: Table name
            action: Query action
            context: Security context

        Returns:
            FilterResult with SQL and parameters
        """
        policies = self.get_applicable_policies(table, action, context)

        if not policies:
            return FilterResult(sql_where="1=1")

        conditions = []
        parameters = {}
        applied_policies = []

        for policy in policies:
            policy_conditions = []

            for idx, cond in enumerate(policy.conditions):
                param_name = f"{policy.name}_{idx}"
                value = self._resolve_value(cond.value, context)

                sql_op = self.SQL_OPERATOR_MAP.get(cond.operator)
                if not sql_op:
                    continue

                if cond.operator == PolicyOperator.IS_NULL:
                    policy_conditions.append(f"{cond.column} IS NULL")
                elif cond.operator == PolicyOperator.IS_NOT_NULL:
                    policy_conditions.append(f"{cond.column} IS NOT NULL")
                elif cond.operator in (PolicyOperator.IN, PolicyOperator.NOT_IN):
                    if isinstance(value, (list, tuple)):
                        placeholders = ", ".join([f":{param_name}_{i}" for i in range(len(value))])
                        policy_conditions.append(f"{cond.column} {sql_op} ({placeholders})")
                        for i, v in enumerate(value):
                            parameters[f"{param_name}_{i}"] = v
                    else:
                        policy_conditions.append(f"{cond.column} {sql_op} (:{param_name})")
                        parameters[param_name] = value
                elif cond.operator == PolicyOperator.CONTAINS:
                    policy_conditions.append(f"{cond.column} LIKE :{param_name}")
                    parameters[param_name] = f"%{value}%"
                elif cond.operator == PolicyOperator.STARTS_WITH:
                    policy_conditions.append(f"{cond.column} LIKE :{param_name}")
                    parameters[param_name] = f"{value}%"
                elif cond.operator == PolicyOperator.ENDS_WITH:
                    policy_conditions.append(f"{cond.column} LIKE :{param_name}")
                    parameters[param_name] = f"%{value}"
                else:
                    policy_conditions.append(f"{cond.column} {sql_op} :{param_name}")
                    parameters[param_name] = value

            if policy_conditions:
                conditions.append(f"({' AND '.join(policy_conditions)})")
                applied_policies.append(policy.name)

        sql_where = " AND ".join(conditions) if conditions else "1=1"

        return FilterResult(
            sql_where=sql_where,
            parameters=parameters,
            applied_policies=applied_policies,
        )

    def filter_rows(
        self,
        rows: List[Dict[str, Any]],
        table: str,
        action: PolicyAction,
        context: SecurityContext,
    ) -> List[Dict[str, Any]]:
        """
        Filter rows in-memory based on RLS policies.

        Args:
            rows: List of row dictionaries
            table: Table name
            action: Query action
            context: Security context

        Returns:
            Filtered rows
        """
        policies = self.get_applicable_policies(table, action, context)

        if not policies:
            return rows

        filtered = []
        for row in rows:
            if self._row_passes_policies(row, policies, context):
                filtered.append(row)

        return filtered

    def check_row_access(
        self,
        row: Dict[str, Any],
        table: str,
        action: PolicyAction,
        context: SecurityContext,
    ) -> bool:
        """
        Check if a single row passes RLS policies.

        Args:
            row: Row data
            table: Table name
            action: Query action
            context: Security context

        Returns:
            True if access is allowed
        """
        policies = self.get_applicable_policies(table, action, context)
        return self._row_passes_policies(row, policies, context)

    def _row_passes_policies(
        self,
        row: Dict[str, Any],
        policies: List[PolicyRule],
        context: SecurityContext,
    ) -> bool:
        """Check if row passes all policies."""
        for policy in policies:
            if not self._row_passes_policy(row, policy, context):
                return False
        return True

    def _row_passes_policy(
        self,
        row: Dict[str, Any],
        policy: PolicyRule,
        context: SecurityContext,
    ) -> bool:
        """Check if row passes a single policy."""
        for condition in policy.conditions:
            if not self._evaluate_condition(row, condition, context):
                return False
        return True

    def _evaluate_condition(
        self,
        row: Dict[str, Any],
        condition: PolicyCondition,
        context: SecurityContext,
    ) -> bool:
        """Evaluate a single condition."""
        row_value = row.get(condition.column)
        expected_value = self._resolve_value(condition.value, context)

        # Handle case sensitivity for strings
        if not condition.case_sensitive and isinstance(row_value, str) and isinstance(expected_value, str):
            row_value = row_value.lower()
            expected_value = expected_value.lower()

        op = condition.operator

        if op == PolicyOperator.IS_NULL:
            return row_value is None
        elif op == PolicyOperator.IS_NOT_NULL:
            return row_value is not None
        elif op == PolicyOperator.IN:
            return row_value in (expected_value if isinstance(expected_value, (list, tuple, set)) else [expected_value])
        elif op == PolicyOperator.NOT_IN:
            return row_value not in (expected_value if isinstance(expected_value, (list, tuple, set)) else [expected_value])
        elif op == PolicyOperator.CONTAINS:
            return expected_value in str(row_value) if row_value else False
        elif op == PolicyOperator.STARTS_WITH:
            return str(row_value).startswith(expected_value) if row_value else False
        elif op == PolicyOperator.ENDS_WITH:
            return str(row_value).endswith(expected_value) if row_value else False
        else:
            # Use operator mapping
            op_func = self.OPERATOR_MAP.get(op)
            if op_func:
                try:
                    return op_func(row_value, expected_value)
                except TypeError:
                    return False
            return False

    def _resolve_value(self, value: Any, context: SecurityContext) -> Any:
        """Resolve value, including context references."""
        if isinstance(value, str) and value.startswith("$"):
            return context.get_attribute(value)
        return value


# Pre-configured common policies
class CommonPolicies:
    """Common RLS policies."""

    @staticmethod
    def organization_isolation(table: str) -> PolicyRule:
        """Isolate data by organization."""
        return PolicyRule(
            name=f"{table}_org_isolation",
            table=table,
            actions=[PolicyAction.ALL],
            conditions=[
                PolicyCondition(
                    column="organization_id",
                    operator=PolicyOperator.EQUALS,
                    value="$user.organization_id",
                )
            ],
            description="Restrict access to organization's own data",
        )

    @staticmethod
    def tenant_isolation(table: str) -> PolicyRule:
        """Isolate data by tenant."""
        return PolicyRule(
            name=f"{table}_tenant_isolation",
            table=table,
            actions=[PolicyAction.ALL],
            conditions=[
                PolicyCondition(
                    column="tenant_id",
                    operator=PolicyOperator.EQUALS,
                    value="$user.tenant_id",
                )
            ],
            description="Restrict access to tenant's own data",
        )

    @staticmethod
    def owner_only(table: str) -> PolicyRule:
        """Only allow access to user's own data."""
        return PolicyRule(
            name=f"{table}_owner_only",
            table=table,
            actions=[PolicyAction.UPDATE, PolicyAction.DELETE],
            conditions=[
                PolicyCondition(
                    column="created_by",
                    operator=PolicyOperator.EQUALS,
                    value="$user.user_id",
                )
            ],
            description="Only owner can modify",
        )

    @staticmethod
    def department_access(table: str) -> PolicyRule:
        """Restrict access by department."""
        return PolicyRule(
            name=f"{table}_department",
            table=table,
            actions=[PolicyAction.SELECT],
            conditions=[
                PolicyCondition(
                    column="department",
                    operator=PolicyOperator.EQUALS,
                    value="$user.department",
                )
            ],
            description="Restrict to same department",
        )

    @staticmethod
    def regional_access(table: str, regions_column: str = "regions") -> PolicyRule:
        """Restrict access by region."""
        return PolicyRule(
            name=f"{table}_regional",
            table=table,
            actions=[PolicyAction.SELECT],
            conditions=[
                PolicyCondition(
                    column=regions_column,
                    operator=PolicyOperator.CONTAINS,
                    value="$user.region",
                )
            ],
            description="Restrict to user's region",
        )


class RLSMiddleware:
    """
    Middleware for applying RLS to SQLAlchemy queries.

    Example:
        middleware = RLSMiddleware(rls_manager)

        @app.middleware("http")
        async def rls_middleware(request: Request, call_next):
            context = SecurityContext(
                user_id=request.state.user.id,
                organization_id=request.state.user.organization_id,
                roles=request.state.user.roles,
            )
            request.state.rls_context = context
            return await call_next(request)
    """

    def __init__(self, rls_manager: RLSManager):
        self.rls_manager = rls_manager

    def apply_filter(
        self,
        query: Any,  # SQLAlchemy Query
        table_name: str,
        action: PolicyAction,
        context: SecurityContext,
    ) -> Any:
        """
        Apply RLS filter to SQLAlchemy query.

        Args:
            query: SQLAlchemy query
            table_name: Table name
            action: Query action
            context: Security context

        Returns:
            Filtered query
        """
        filter_result = self.rls_manager.get_sql_filter(table_name, action, context)

        if filter_result.sql_where and filter_result.sql_where != "1=1":
            try:
                from sqlalchemy import text
                query = query.filter(text(filter_result.sql_where).bindparams(**filter_result.parameters))
            except ImportError:
                logger.warning("SQLAlchemy not available")

        return query

    def create_filter_function(
        self,
        table_name: str,
        action: PolicyAction,
    ) -> Callable[[Any, SecurityContext], Any]:
        """
        Create a reusable filter function for a table.

        Args:
            table_name: Table name
            action: Query action

        Returns:
            Filter function
        """
        def filter_func(query: Any, context: SecurityContext) -> Any:
            return self.apply_filter(query, table_name, action, context)

        return filter_func
