"""
MCP Protocol Schemas.

Pydantic models for MCP protocol messages.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class ContentType(str, Enum):
    """Content types for MCP messages."""

    TEXT = "text"
    IMAGE = "image"
    RESOURCE = "resource"


class TextContent(BaseModel):
    """Text content in MCP messages."""

    type: str = Field(default="text")
    text: str


class ImageContent(BaseModel):
    """Image content in MCP messages."""

    type: str = Field(default="image")
    data: str  # Base64 encoded
    mime_type: str = Field(alias="mimeType")


class ResourceContent(BaseModel):
    """Resource reference content."""

    type: str = Field(default="resource")
    resource: Dict[str, Any]


Content = Union[TextContent, ImageContent, ResourceContent]


class Resource(BaseModel):
    """MCP Resource definition."""

    uri: str
    name: str
    description: Optional[str] = None
    mime_type: Optional[str] = Field(default=None, alias="mimeType")


class ResourceContents(BaseModel):
    """Resource contents response."""

    uri: str
    mime_type: Optional[str] = Field(default=None, alias="mimeType")
    text: Optional[str] = None
    blob: Optional[str] = None  # Base64 encoded binary


class ResourceTemplate(BaseModel):
    """Resource URI template."""

    uri_template: str = Field(alias="uriTemplate")
    name: str
    description: Optional[str] = None
    mime_type: Optional[str] = Field(default=None, alias="mimeType")


class Tool(BaseModel):
    """MCP Tool definition."""

    name: str
    description: str
    input_schema: Dict[str, Any] = Field(alias="inputSchema")


class ToolResult(BaseModel):
    """Tool execution result."""

    content: List[Content]
    is_error: bool = Field(default=False, alias="isError")


class Prompt(BaseModel):
    """MCP Prompt definition."""

    name: str
    description: Optional[str] = None
    arguments: Optional[List[Dict[str, Any]]] = None


class PromptMessage(BaseModel):
    """Prompt message."""

    role: str  # "user" or "assistant"
    content: Content


class PromptResult(BaseModel):
    """Prompt get result."""

    description: Optional[str] = None
    messages: List[PromptMessage]


class ServerCapabilities(BaseModel):
    """MCP Server capabilities."""

    resources: Optional[Dict[str, Any]] = None
    tools: Optional[Dict[str, Any]] = None
    prompts: Optional[Dict[str, Any]] = None
    logging: Optional[Dict[str, Any]] = None


class ClientCapabilities(BaseModel):
    """MCP Client capabilities."""

    roots: Optional[Dict[str, Any]] = None
    sampling: Optional[Dict[str, Any]] = None


class InitializeParams(BaseModel):
    """Initialize request parameters."""

    protocol_version: str = Field(alias="protocolVersion")
    capabilities: ClientCapabilities
    client_info: Dict[str, str] = Field(alias="clientInfo")


class InitializeResult(BaseModel):
    """Initialize response."""

    protocol_version: str = Field(alias="protocolVersion")
    capabilities: ServerCapabilities
    server_info: Dict[str, str] = Field(alias="serverInfo")


class ResourcesListResult(BaseModel):
    """Resources list response."""

    resources: List[Resource]
    next_cursor: Optional[str] = Field(default=None, alias="nextCursor")


class ResourcesReadParams(BaseModel):
    """Resources read parameters."""

    uri: str


class ResourcesReadResult(BaseModel):
    """Resources read response."""

    contents: List[ResourceContents]


class ToolsListResult(BaseModel):
    """Tools list response."""

    tools: List[Tool]
    next_cursor: Optional[str] = Field(default=None, alias="nextCursor")


class ToolsCallParams(BaseModel):
    """Tools call parameters."""

    name: str
    arguments: Optional[Dict[str, Any]] = None


class ToolsCallResult(BaseModel):
    """Tools call response."""

    content: List[Content]
    is_error: bool = Field(default=False, alias="isError")


class PromptsListResult(BaseModel):
    """Prompts list response."""

    prompts: List[Prompt]
    next_cursor: Optional[str] = Field(default=None, alias="nextCursor")


class PromptsGetParams(BaseModel):
    """Prompts get parameters."""

    name: str
    arguments: Optional[Dict[str, Any]] = None


class PromptsGetResult(BaseModel):
    """Prompts get response."""

    description: Optional[str] = None
    messages: List[PromptMessage]


class ProgressNotification(BaseModel):
    """Progress notification for long-running operations."""

    progress_token: str = Field(alias="progressToken")
    progress: float  # 0.0 to 1.0
    total: Optional[float] = None


class LogLevel(str, Enum):
    """Log levels."""

    DEBUG = "debug"
    INFO = "info"
    NOTICE = "notice"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    ALERT = "alert"
    EMERGENCY = "emergency"


class LogMessage(BaseModel):
    """Log message from server."""

    level: LogLevel
    logger: Optional[str] = None
    data: Any


class CancelledNotification(BaseModel):
    """Notification that a request was cancelled."""

    request_id: Union[str, int] = Field(alias="requestId")
    reason: Optional[str] = None
