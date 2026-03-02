"""
MCP Exception Types.

Defines structured errors following JSON-RPC 2.0 and MCP protocol specifications.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class MCPErrorCode(str, Enum):
    """
    MCP error codes following JSON-RPC 2.0 specification.

    Standard JSON-RPC errors: -32700 to -32600
    MCP-specific errors: -32000 to -32099
    """

    # Standard JSON-RPC 2.0 errors
    PARSE_ERROR = "-32700"
    INVALID_REQUEST = "-32600"
    METHOD_NOT_FOUND = "-32601"
    INVALID_PARAMS = "-32602"
    INTERNAL_ERROR = "-32603"

    # MCP-specific errors (-32000 to -32099)
    AUTHENTICATION_REQUIRED = "-32001"
    INSUFFICIENT_SCOPE = "-32002"
    RATE_LIMITED = "-32003"
    RESOURCE_NOT_FOUND = "-32004"
    VALIDATION_ERROR = "-32005"
    ASYNC_JOB_PENDING = "-32006"
    EXTERNAL_SERVICE_ERROR = "-32007"
    RESOURCE_UNAVAILABLE = "-32008"
    OPERATION_TIMEOUT = "-32009"
    QUOTA_EXCEEDED = "-32010"
    CONFLICT = "-32011"
    PRECONDITION_FAILED = "-32012"


# HTTP status code mapping for each error code
ERROR_HTTP_STATUS: Dict[MCPErrorCode, int] = {
    MCPErrorCode.PARSE_ERROR: 400,
    MCPErrorCode.INVALID_REQUEST: 400,
    MCPErrorCode.METHOD_NOT_FOUND: 404,
    MCPErrorCode.INVALID_PARAMS: 422,
    MCPErrorCode.INTERNAL_ERROR: 500,
    MCPErrorCode.AUTHENTICATION_REQUIRED: 401,
    MCPErrorCode.INSUFFICIENT_SCOPE: 403,
    MCPErrorCode.RATE_LIMITED: 429,
    MCPErrorCode.RESOURCE_NOT_FOUND: 404,
    MCPErrorCode.VALIDATION_ERROR: 422,
    MCPErrorCode.ASYNC_JOB_PENDING: 202,
    MCPErrorCode.EXTERNAL_SERVICE_ERROR: 502,
    MCPErrorCode.RESOURCE_UNAVAILABLE: 503,
    MCPErrorCode.OPERATION_TIMEOUT: 504,
    MCPErrorCode.QUOTA_EXCEEDED: 429,
    MCPErrorCode.CONFLICT: 409,
    MCPErrorCode.PRECONDITION_FAILED: 412,
}


@dataclass
class MCPError(Exception):
    """
    Production MCP error with recovery suggestions.

    Follows JSON-RPC 2.0 error format with extensions for
    recovery suggestions and documentation links.

    Attributes:
        code: MCP error code from MCPErrorCode enum
        message: Human-readable error message
        data: Additional error context data
        recovery_suggestions: List of suggested recovery actions
        documentation_url: Link to relevant documentation
        request_id: Request ID for correlation
        retry_after: Seconds to wait before retry (for rate limiting)
    """

    code: MCPErrorCode
    message: str
    data: Optional[Dict[str, Any]] = None
    recovery_suggestions: Optional[List[str]] = None
    documentation_url: Optional[str] = None
    request_id: Optional[str] = None
    retry_after: Optional[int] = None

    def __post_init__(self):
        """Initialize the exception with the message."""
        super().__init__(self.message)

    @property
    def http_status(self) -> int:
        """Get corresponding HTTP status code."""
        return ERROR_HTTP_STATUS.get(self.code, 500)

    def to_json_rpc(self) -> Dict[str, Any]:
        """Convert to JSON-RPC 2.0 error format."""
        error: Dict[str, Any] = {
            "code": int(self.code.value),
            "message": self.message,
        }

        # Add extended data if present
        extended_data: Dict[str, Any] = {}

        if self.data:
            extended_data.update(self.data)

        if self.recovery_suggestions:
            extended_data["recovery_suggestions"] = self.recovery_suggestions

        if self.documentation_url:
            extended_data["documentation_url"] = self.documentation_url

        if self.request_id:
            extended_data["request_id"] = self.request_id

        if self.retry_after is not None:
            extended_data["retry_after"] = self.retry_after

        if extended_data:
            error["data"] = extended_data

        return error

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging and serialization."""
        return {
            "code": self.code.value,
            "message": self.message,
            "data": self.data,
            "recovery_suggestions": self.recovery_suggestions,
            "documentation_url": self.documentation_url,
            "request_id": self.request_id,
            "retry_after": self.retry_after,
            "http_status": self.http_status,
        }


# Convenience factory functions for common errors


def authentication_required(
    message: str = "Authentication is required to access this resource",
    request_id: Optional[str] = None,
) -> MCPError:
    """Create an authentication required error."""
    return MCPError(
        code=MCPErrorCode.AUTHENTICATION_REQUIRED,
        message=message,
        recovery_suggestions=[
            "Include a valid Bearer token in the Authorization header",
            "Obtain a new token if your current token has expired",
        ],
        documentation_url="/docs/authentication",
        request_id=request_id,
    )


def insufficient_scope(
    required_scope: str,
    available_scopes: Optional[List[str]] = None,
    request_id: Optional[str] = None,
) -> MCPError:
    """Create an insufficient scope error."""
    return MCPError(
        code=MCPErrorCode.INSUFFICIENT_SCOPE,
        message=f"Token does not have required scope: {required_scope}",
        data={
            "required_scope": required_scope,
            "available_scopes": available_scopes or [],
        },
        recovery_suggestions=[
            f"Request a token with the '{required_scope}' scope",
            "Contact your administrator to grant additional permissions",
        ],
        documentation_url="/docs/scopes",
        request_id=request_id,
    )


def rate_limited(
    retry_after: int,
    limit_type: str = "requests",
    limit_value: int = 0,
    request_id: Optional[str] = None,
) -> MCPError:
    """Create a rate limited error."""
    return MCPError(
        code=MCPErrorCode.RATE_LIMITED,
        message=f"Rate limit exceeded. Please retry after {retry_after} seconds.",
        data={
            "limit_type": limit_type,
            "limit_value": limit_value,
        },
        recovery_suggestions=[
            f"Wait {retry_after} seconds before retrying",
            "Consider upgrading your plan for higher rate limits",
            "Implement exponential backoff in your client",
        ],
        documentation_url="/docs/rate-limits",
        request_id=request_id,
        retry_after=retry_after,
    )


def resource_not_found(
    resource_type: str,
    resource_id: str,
    request_id: Optional[str] = None,
) -> MCPError:
    """Create a resource not found error."""
    return MCPError(
        code=MCPErrorCode.RESOURCE_NOT_FOUND,
        message=f"{resource_type} with ID '{resource_id}' not found",
        data={
            "resource_type": resource_type,
            "resource_id": resource_id,
        },
        recovery_suggestions=[
            "Verify the resource ID is correct",
            f"List available {resource_type.lower()}s to find valid IDs",
            "Check if the resource has been deleted or archived",
        ],
        request_id=request_id,
    )


def validation_error(
    errors: List[Dict[str, Any]],
    message: str = "Validation failed for the provided parameters",
    request_id: Optional[str] = None,
) -> MCPError:
    """Create a validation error with field-level details."""
    return MCPError(
        code=MCPErrorCode.VALIDATION_ERROR,
        message=message,
        data={"validation_errors": errors},
        recovery_suggestions=[
            "Review the validation errors and correct the input",
            "Refer to the API documentation for valid parameter formats",
        ],
        documentation_url="/docs/api-reference",
        request_id=request_id,
    )


def async_job_pending(
    job_id: str,
    status: str,
    progress: Optional[float] = None,
    estimated_completion: Optional[str] = None,
    request_id: Optional[str] = None,
) -> MCPError:
    """Create an async job pending notification."""
    data: Dict[str, Any] = {
        "job_id": job_id,
        "status": status,
    }
    if progress is not None:
        data["progress"] = progress
    if estimated_completion:
        data["estimated_completion"] = estimated_completion

    return MCPError(
        code=MCPErrorCode.ASYNC_JOB_PENDING,
        message=f"Job {job_id} is still processing",
        data=data,
        recovery_suggestions=[
            f"Poll for job status using get_training_status with job_id: {job_id}",
            "Use webhooks for real-time job completion notifications",
        ],
        request_id=request_id,
    )


def external_service_error(
    service_name: str,
    original_error: Optional[str] = None,
    request_id: Optional[str] = None,
) -> MCPError:
    """Create an external service error."""
    return MCPError(
        code=MCPErrorCode.EXTERNAL_SERVICE_ERROR,
        message=f"External service '{service_name}' is unavailable or returned an error",
        data={
            "service_name": service_name,
            "original_error": original_error,
        },
        recovery_suggestions=[
            "Retry the request after a short delay",
            "Check the service status page for outages",
            "Contact support if the issue persists",
        ],
        request_id=request_id,
    )


def internal_error(
    message: str = "An internal error occurred",
    error_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> MCPError:
    """Create an internal error."""
    return MCPError(
        code=MCPErrorCode.INTERNAL_ERROR,
        message=message,
        data={"error_id": error_id} if error_id else None,
        recovery_suggestions=[
            "Retry the request",
            "Contact support with the error ID if the issue persists",
        ],
        request_id=request_id,
    )


def invalid_params(
    message: str,
    param_name: Optional[str] = None,
    expected_type: Optional[str] = None,
    request_id: Optional[str] = None,
) -> MCPError:
    """Create an invalid parameters error."""
    data: Dict[str, Any] = {}
    if param_name:
        data["param_name"] = param_name
    if expected_type:
        data["expected_type"] = expected_type

    return MCPError(
        code=MCPErrorCode.INVALID_PARAMS,
        message=message,
        data=data if data else None,
        recovery_suggestions=[
            "Check the parameter types and values",
            "Refer to the API documentation for valid parameters",
        ],
        documentation_url="/docs/api-reference",
        request_id=request_id,
    )


def operation_timeout(
    operation: str,
    timeout_seconds: int,
    request_id: Optional[str] = None,
) -> MCPError:
    """Create an operation timeout error."""
    return MCPError(
        code=MCPErrorCode.OPERATION_TIMEOUT,
        message=f"Operation '{operation}' timed out after {timeout_seconds} seconds",
        data={
            "operation": operation,
            "timeout_seconds": timeout_seconds,
        },
        recovery_suggestions=[
            "Break the operation into smaller chunks",
            "Retry with a smaller dataset or simpler parameters",
            "Use async operations for long-running tasks",
        ],
        request_id=request_id,
    )
