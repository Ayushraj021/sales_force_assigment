"""
Base Tool Classes for MCP.

Provides abstract base classes for MCP tools with validation support.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, Union

import structlog
from pydantic import BaseModel, ValidationError

from app.mcp.config import get_mcp_settings
from app.mcp.core.auth import MCPTokenClaims
from app.mcp.core.exceptions import MCPError, MCPErrorCode, validation_error

logger = structlog.get_logger("mcp.tools")


class ParameterType(str, Enum):
    """Parameter types for tool schemas."""

    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


@dataclass
class ToolParameter:
    """
    Definition of a tool parameter.

    Used to generate JSON Schema for tool input validation.
    """

    name: str
    param_type: ParameterType
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[Any]] = None
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    items: Optional["ToolParameter"] = None  # For arrays

    def to_json_schema(self) -> Dict[str, Any]:
        """Convert to JSON Schema format."""
        schema: Dict[str, Any] = {
            "type": self.param_type.value,
            "description": self.description,
        }

        if self.default is not None:
            schema["default"] = self.default
        if self.enum:
            schema["enum"] = self.enum
        if self.minimum is not None:
            schema["minimum"] = self.minimum
        if self.maximum is not None:
            schema["maximum"] = self.maximum
        if self.min_length is not None:
            schema["minLength"] = self.min_length
        if self.max_length is not None:
            schema["maxLength"] = self.max_length
        if self.pattern:
            schema["pattern"] = self.pattern
        if self.items and self.param_type == ParameterType.ARRAY:
            schema["items"] = self.items.to_json_schema()

        return schema


@dataclass
class ToolResult:
    """
    Result from tool execution.

    Provides structured output with success/error status.
    """

    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    is_async: bool = False
    job_id: Optional[str] = None
    message: Optional[str] = None

    def to_mcp_content(self) -> List[Dict[str, Any]]:
        """Convert to MCP content format."""
        if self.success:
            import json

            content = {
                "type": "text",
                "text": json.dumps(self.data) if self.data else self.message or "Success",
            }
        else:
            content = {
                "type": "text",
                "text": self.error or "Unknown error",
            }

        return [content]


class BaseTool(ABC):
    """
    Abstract base class for MCP tools.

    Provides common functionality including:
    - Parameter validation
    - Authorization checking
    - Schema generation
    - Error handling

    Example:
        class TrainModelTool(BaseTool):
            name = "train_model"
            description = "Train a new model version"
            required_scope = "models:train"

            parameters = [
                ToolParameter("model_id", ParameterType.STRING, "Model ID"),
                ToolParameter("dataset_id", ParameterType.STRING, "Dataset ID"),
            ]

            async def execute(self, arguments, claims):
                # Implementation
                return ToolResult(success=True, data={...})
    """

    # Subclasses must define these
    name: str = ""
    description: str = ""
    required_scope: str = ""
    parameters: List[ToolParameter] = []
    is_async: bool = False

    def __init__(self, db=None, celery=None):
        """
        Initialize tool.

        Args:
            db: Database session factory
            celery: Celery app for async tasks
        """
        self.db = db
        self.celery = celery
        self.settings = get_mcp_settings()
        self.logger = structlog.get_logger(f"mcp.tools.{self.name}")

    def get_schema(self) -> Dict[str, Any]:
        """Get tool schema for MCP listing."""
        properties = {}
        required = []

        for param in self.parameters:
            properties[param.name] = param.to_json_schema()
            if param.required:
                required.append(param.name)

        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }

    async def handle(
        self,
        arguments: Dict[str, Any],
        claims: Optional[MCPTokenClaims] = None,
    ) -> Dict[str, Any]:
        """
        Handle tool call with validation.

        Args:
            arguments: Tool arguments
            claims: Authenticated user claims

        Returns:
            Tool result
        """
        # Check authorization
        if claims and self.required_scope:
            if not claims.has_scope(self.required_scope):
                raise MCPError(
                    code=MCPErrorCode.INSUFFICIENT_SCOPE,
                    message=f"Scope '{self.required_scope}' required for {self.name}",
                )

        # Validate arguments
        errors = self._validate_arguments(arguments)
        if errors:
            raise validation_error(errors, f"Invalid arguments for {self.name}")

        # Execute tool
        try:
            result = await self.execute(arguments, claims)
            return result.data if result.success else {"error": result.error}
        except MCPError:
            raise
        except Exception as e:
            self.logger.exception("Tool execution failed", tool=self.name, error=str(e))
            raise MCPError(
                code=MCPErrorCode.INTERNAL_ERROR,
                message=f"Tool execution failed: {str(e)}",
            )

    def _validate_arguments(
        self,
        arguments: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Validate tool arguments against parameter definitions."""
        errors = []

        for param in self.parameters:
            value = arguments.get(param.name)

            # Check required
            if param.required and value is None:
                errors.append({
                    "field": param.name,
                    "message": f"'{param.name}' is required",
                })
                continue

            if value is None:
                continue

            # Type validation
            type_valid = self._check_type(value, param.param_type)
            if not type_valid:
                errors.append({
                    "field": param.name,
                    "message": f"'{param.name}' must be of type {param.param_type.value}",
                })
                continue

            # Enum validation
            if param.enum and value not in param.enum:
                errors.append({
                    "field": param.name,
                    "message": f"'{param.name}' must be one of: {param.enum}",
                })

            # Range validation
            if param.minimum is not None and value < param.minimum:
                errors.append({
                    "field": param.name,
                    "message": f"'{param.name}' must be >= {param.minimum}",
                })
            if param.maximum is not None and value > param.maximum:
                errors.append({
                    "field": param.name,
                    "message": f"'{param.name}' must be <= {param.maximum}",
                })

            # String length validation
            if isinstance(value, str):
                if param.min_length and len(value) < param.min_length:
                    errors.append({
                        "field": param.name,
                        "message": f"'{param.name}' must have at least {param.min_length} characters",
                    })
                if param.max_length and len(value) > param.max_length:
                    errors.append({
                        "field": param.name,
                        "message": f"'{param.name}' must have at most {param.max_length} characters",
                    })

        return errors

    def _check_type(self, value: Any, param_type: ParameterType) -> bool:
        """Check if value matches parameter type."""
        if param_type == ParameterType.STRING:
            return isinstance(value, str)
        elif param_type == ParameterType.NUMBER:
            return isinstance(value, (int, float))
        elif param_type == ParameterType.INTEGER:
            return isinstance(value, int) and not isinstance(value, bool)
        elif param_type == ParameterType.BOOLEAN:
            return isinstance(value, bool)
        elif param_type == ParameterType.ARRAY:
            return isinstance(value, list)
        elif param_type == ParameterType.OBJECT:
            return isinstance(value, dict)
        return True

    @abstractmethod
    async def execute(
        self,
        arguments: Dict[str, Any],
        claims: Optional[MCPTokenClaims],
    ) -> ToolResult:
        """
        Execute the tool.

        Subclasses must implement this method.

        Args:
            arguments: Validated tool arguments
            claims: Authenticated user claims

        Returns:
            ToolResult with execution outcome
        """
        pass


class AsyncTool(BaseTool):
    """
    Base class for async/long-running tools.

    Provides job tracking for operations that may take a long time.
    """

    is_async = True

    async def execute(
        self,
        arguments: Dict[str, Any],
        claims: Optional[MCPTokenClaims],
    ) -> ToolResult:
        """Execute async tool by queuing job."""
        # Start async job
        job_id = await self.start_job(arguments, claims)

        return ToolResult(
            success=True,
            is_async=True,
            job_id=job_id,
            data={
                "job_id": job_id,
                "status": "queued",
                "message": f"Job {job_id} has been queued. Use get_training_status to check progress.",
            },
        )

    @abstractmethod
    async def start_job(
        self,
        arguments: Dict[str, Any],
        claims: Optional[MCPTokenClaims],
    ) -> str:
        """
        Start the async job.

        Returns:
            Job ID for tracking
        """
        pass

    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get status of async job."""
        if not self.celery:
            return {"status": "unknown", "error": "Celery not configured"}

        result = self.celery.AsyncResult(job_id)

        if result.ready():
            if result.successful():
                return {
                    "status": "completed",
                    "result": result.get(),
                }
            else:
                return {
                    "status": "failed",
                    "error": str(result.result),
                }
        else:
            return {
                "status": "running",
                "progress": getattr(result, "info", {}).get("progress", 0),
            }


class ToolRegistry:
    """Registry of available tools."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[BaseTool]:
        """Get tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        """List all tool schemas."""
        return [tool.get_schema() for tool in self._tools.values()]

    def get_tool_names(self) -> List[str]:
        """Get list of tool names."""
        return list(self._tools.keys())
