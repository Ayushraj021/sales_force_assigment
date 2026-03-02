"""
MCP HTTP Transport Implementation.

Implements Streamable HTTP transport for MCP protocol.
"""

import json
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Union

import structlog
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.mcp.config import get_mcp_settings
from app.mcp.core.auth import MCPTokenClaims, get_mcp_claims
from app.mcp.core.exceptions import MCPError, MCPErrorCode

logger = structlog.get_logger("mcp.transport")


class JSONRPCVersion(str, Enum):
    """JSON-RPC version."""

    V2 = "2.0"


class MCPRequestMethod(str, Enum):
    """MCP request methods."""

    # Initialization
    INITIALIZE = "initialize"

    # Resources
    RESOURCES_LIST = "resources/list"
    RESOURCES_READ = "resources/read"
    RESOURCES_SUBSCRIBE = "resources/subscribe"
    RESOURCES_UNSUBSCRIBE = "resources/unsubscribe"

    # Tools
    TOOLS_LIST = "tools/list"
    TOOLS_CALL = "tools/call"

    # Prompts
    PROMPTS_LIST = "prompts/list"
    PROMPTS_GET = "prompts/get"

    # Completion
    COMPLETION_COMPLETE = "completion/complete"

    # Notifications
    NOTIFICATION_CANCELLED = "notifications/cancelled"
    NOTIFICATION_PROGRESS = "notifications/progress"


class JSONRPCRequest(BaseModel):
    """JSON-RPC 2.0 request."""

    jsonrpc: str = Field(default="2.0")
    id: Optional[Union[str, int]] = None
    method: str
    params: Optional[Dict[str, Any]] = None


class JSONRPCResponse(BaseModel):
    """JSON-RPC 2.0 response."""

    jsonrpc: str = Field(default="2.0")
    id: Optional[Union[str, int]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


class JSONRPCError(BaseModel):
    """JSON-RPC 2.0 error."""

    code: int
    message: str
    data: Optional[Dict[str, Any]] = None


@dataclass
class MCPServerInfo:
    """MCP server information."""

    name: str
    version: str
    protocol_version: str = "2024-11-05"


@dataclass
class MCPCapabilities:
    """MCP server capabilities."""

    resources: Dict[str, Any] = field(default_factory=lambda: {"subscribe": False})
    tools: Dict[str, Any] = field(default_factory=dict)
    prompts: Dict[str, Any] = field(default_factory=dict)


class MCPHttpTransport:
    """
    Streamable HTTP transport for MCP.

    Implements the MCP protocol over HTTP with optional streaming support.

    Example:
        transport = MCPHttpTransport(
            server_info=MCPServerInfo(name="sales-forecast", version="1.0.0"),
        )

        # Register handlers
        transport.register_resource_handler("data://{org}/datasets", list_datasets)
        transport.register_tool_handler("train_model", train_model_handler)

        # Create router
        router = transport.create_router()
        app.include_router(router, prefix="/mcp")
    """

    def __init__(
        self,
        server_info: MCPServerInfo,
        capabilities: Optional[MCPCapabilities] = None,
    ):
        """
        Initialize transport.

        Args:
            server_info: Server information
            capabilities: Server capabilities
        """
        self.server_info = server_info
        self.capabilities = capabilities or MCPCapabilities()
        self.settings = get_mcp_settings()

        # Handler registries
        self._resource_handlers: Dict[str, Callable] = {}
        self._tool_handlers: Dict[str, Callable] = {}
        self._prompt_handlers: Dict[str, Callable] = {}

        self.logger = structlog.get_logger("mcp.transport")

    def register_resource_handler(
        self,
        uri_pattern: str,
        handler: Callable,
    ) -> None:
        """
        Register a resource handler.

        Args:
            uri_pattern: URI pattern (e.g., "data://{org}/datasets")
            handler: Async handler function
        """
        self._resource_handlers[uri_pattern] = handler

    def register_tool_handler(
        self,
        tool_name: str,
        handler: Any,
    ) -> None:
        """
        Register a tool handler.

        Args:
            tool_name: Tool name
            handler: Tool object with handle() and get_schema() methods,
                     or an async handler function
        """
        self._tool_handlers[tool_name] = handler

    def register_prompt_handler(
        self,
        prompt_name: str,
        handler: Callable,
    ) -> None:
        """
        Register a prompt handler.

        Args:
            prompt_name: Prompt name
            handler: Async handler function
        """
        self._prompt_handlers[prompt_name] = handler

    async def handle_request(
        self,
        request: JSONRPCRequest,
        claims: Optional[MCPTokenClaims] = None,
    ) -> JSONRPCResponse:
        """
        Handle a JSON-RPC request.

        Args:
            request: JSON-RPC request
            claims: Authenticated user claims

        Returns:
            JSON-RPC response
        """
        try:
            method = request.method
            params = request.params or {}

            # Route to appropriate handler
            if method == MCPRequestMethod.INITIALIZE:
                result = await self._handle_initialize(params)
            elif method == MCPRequestMethod.RESOURCES_LIST:
                result = await self._handle_resources_list(params, claims)
            elif method == MCPRequestMethod.RESOURCES_READ:
                result = await self._handle_resources_read(params, claims)
            elif method == MCPRequestMethod.TOOLS_LIST:
                result = await self._handle_tools_list(params, claims)
            elif method == MCPRequestMethod.TOOLS_CALL:
                result = await self._handle_tools_call(params, claims)
            elif method == MCPRequestMethod.PROMPTS_LIST:
                result = await self._handle_prompts_list(params, claims)
            elif method == MCPRequestMethod.PROMPTS_GET:
                result = await self._handle_prompts_get(params, claims)
            else:
                raise MCPError(
                    code=MCPErrorCode.METHOD_NOT_FOUND,
                    message=f"Method '{method}' not found",
                )

            return JSONRPCResponse(
                id=request.id,
                result=result,
            )

        except MCPError as e:
            return JSONRPCResponse(
                id=request.id,
                error=e.to_json_rpc(),
            )
        except Exception as e:
            self.logger.exception("Unexpected error handling MCP request", error=str(e))
            return JSONRPCResponse(
                id=request.id,
                error={
                    "code": int(MCPErrorCode.INTERNAL_ERROR.value),
                    "message": "Internal server error",
                },
            )

    async def _handle_initialize(
        self,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle initialize request."""
        return {
            "protocolVersion": self.server_info.protocol_version,
            "capabilities": {
                "resources": self.capabilities.resources,
                "tools": self.capabilities.tools,
                "prompts": self.capabilities.prompts,
            },
            "serverInfo": {
                "name": self.server_info.name,
                "version": self.server_info.version,
            },
        }

    async def _handle_resources_list(
        self,
        params: Dict[str, Any],
        claims: Optional[MCPTokenClaims],
    ) -> Dict[str, Any]:
        """Handle resources/list request."""
        resources = []
        for uri_pattern, handler in self._resource_handlers.items():
            # Get resource metadata from handler
            if hasattr(handler, "get_metadata"):
                metadata = handler.get_metadata()
                resources.append(metadata)

        return {"resources": resources}

    async def _handle_resources_read(
        self,
        params: Dict[str, Any],
        claims: Optional[MCPTokenClaims],
    ) -> Dict[str, Any]:
        """Handle resources/read request."""
        uri = params.get("uri")
        if not uri:
            raise MCPError(
                code=MCPErrorCode.INVALID_PARAMS,
                message="Missing 'uri' parameter",
            )

        # Find matching handler
        handler = self._find_resource_handler(uri)
        if not handler:
            raise MCPError(
                code=MCPErrorCode.RESOURCE_NOT_FOUND,
                message=f"Resource '{uri}' not found",
            )

        # Execute handler
        result = await handler(uri=uri, claims=claims)
        return {"contents": [result]}

    async def _handle_tools_list(
        self,
        params: Dict[str, Any],
        claims: Optional[MCPTokenClaims],
    ) -> Dict[str, Any]:
        """Handle tools/list request."""
        tools = []
        for tool_name, handler in self._tool_handlers.items():
            if hasattr(handler, "get_schema"):
                schema = handler.get_schema()
                tools.append(schema)

        return {"tools": tools}

    async def _handle_tools_call(
        self,
        params: Dict[str, Any],
        claims: Optional[MCPTokenClaims],
    ) -> Dict[str, Any]:
        """Handle tools/call request."""
        tool_name = params.get("name")
        if not tool_name:
            raise MCPError(
                code=MCPErrorCode.INVALID_PARAMS,
                message="Missing 'name' parameter",
            )

        handler = self._tool_handlers.get(tool_name)
        if not handler:
            raise MCPError(
                code=MCPErrorCode.METHOD_NOT_FOUND,
                message=f"Tool '{tool_name}' not found",
            )

        arguments = params.get("arguments", {})

        # Execute handler - support both tool objects and direct callables
        if hasattr(handler, "handle"):
            result = await handler.handle(arguments=arguments, claims=claims)
        else:
            result = await handler(arguments=arguments, claims=claims)

        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result) if isinstance(result, dict) else str(result),
                }
            ],
        }

    async def _handle_prompts_list(
        self,
        params: Dict[str, Any],
        claims: Optional[MCPTokenClaims],
    ) -> Dict[str, Any]:
        """Handle prompts/list request."""
        prompts = []
        for prompt_name, handler in self._prompt_handlers.items():
            if hasattr(handler, "get_metadata"):
                metadata = handler.get_metadata()
                prompts.append(metadata)

        return {"prompts": prompts}

    async def _handle_prompts_get(
        self,
        params: Dict[str, Any],
        claims: Optional[MCPTokenClaims],
    ) -> Dict[str, Any]:
        """Handle prompts/get request."""
        prompt_name = params.get("name")
        if not prompt_name:
            raise MCPError(
                code=MCPErrorCode.INVALID_PARAMS,
                message="Missing 'name' parameter",
            )

        handler = self._prompt_handlers.get(prompt_name)
        if not handler:
            raise MCPError(
                code=MCPErrorCode.RESOURCE_NOT_FOUND,
                message=f"Prompt '{prompt_name}' not found",
            )

        arguments = params.get("arguments", {})
        result = await handler(arguments=arguments, claims=claims)

        return result

    def _find_resource_handler(self, uri: str) -> Optional[Callable]:
        """Find handler for a resource URI."""
        for pattern, handler in self._resource_handlers.items():
            if self._matches_pattern(pattern, uri):
                return handler
        return None

    def _matches_pattern(self, pattern: str, uri: str) -> bool:
        """Check if URI matches pattern."""
        import re

        # Convert pattern to regex
        regex_pattern = pattern.replace("{", "(?P<").replace("}", ">[^/]+)")
        regex_pattern = "^" + regex_pattern + "$"

        return bool(re.match(regex_pattern, uri))

    def create_router(self, prefix: str = "") -> APIRouter:
        """
        Create FastAPI router for MCP endpoints.

        Args:
            prefix: Route prefix

        Returns:
            FastAPI APIRouter
        """
        router = APIRouter(prefix=prefix, tags=["MCP"])

        @router.post("")
        @router.post("/")
        async def handle_mcp_request(
            request: Request,
        ) -> Response:
            """Handle MCP JSON-RPC request."""
            try:
                body = await request.json()
            except json.JSONDecodeError:
                return JSONResponse(
                    content={
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": int(MCPErrorCode.PARSE_ERROR.value),
                            "message": "Invalid JSON",
                        },
                    },
                    status_code=400,
                )

            # Get claims if authenticated
            claims = None
            if hasattr(request.state, "mcp_claims"):
                claims = request.state.mcp_claims

            # Handle batch requests
            if isinstance(body, list):
                responses = []
                for req_data in body:
                    try:
                        req = JSONRPCRequest(**req_data)
                        resp = await self.handle_request(req, claims)
                        responses.append(resp.model_dump(exclude_none=True))
                    except Exception:
                        responses.append({
                            "jsonrpc": "2.0",
                            "id": req_data.get("id"),
                            "error": {
                                "code": int(MCPErrorCode.INVALID_REQUEST.value),
                                "message": "Invalid request format",
                            },
                        })
                return JSONResponse(content=responses)

            # Handle single request
            try:
                req = JSONRPCRequest(**body)
                resp = await self.handle_request(req, claims)
                return JSONResponse(content=resp.model_dump(exclude_none=True))
            except Exception:
                return JSONResponse(
                    content={
                        "jsonrpc": "2.0",
                        "id": body.get("id"),
                        "error": {
                            "code": int(MCPErrorCode.INVALID_REQUEST.value),
                            "message": "Invalid request format",
                        },
                    },
                    status_code=400,
                )

        @router.get("/health")
        async def health_check() -> Dict[str, Any]:
            """Health check endpoint."""
            return {
                "status": "healthy",
                "server": self.server_info.name,
                "version": self.server_info.version,
                "protocol_version": self.server_info.protocol_version,
            }

        @router.get("/ready")
        async def readiness_check() -> Dict[str, Any]:
            """Readiness check endpoint."""
            return {
                "status": "ready",
                "server": self.server_info.name,
            }

        return router


class StreamingTransport(MCPHttpTransport):
    """
    Extended transport with SSE streaming support.

    Supports long-running operations with progress updates.
    """

    async def handle_streaming_request(
        self,
        request: JSONRPCRequest,
        claims: Optional[MCPTokenClaims] = None,
    ) -> AsyncIterator[str]:
        """
        Handle request with streaming response.

        Yields SSE-formatted events.
        """
        request_id = str(request.id) if request.id else str(uuid.uuid4())

        try:
            # Send initial acknowledgment
            yield self._format_sse_event(
                "progress",
                {
                    "id": request_id,
                    "progress": 0,
                    "status": "started",
                },
            )

            # Handle the request
            response = await self.handle_request(request, claims)

            # Send result
            yield self._format_sse_event(
                "result",
                response.model_dump(exclude_none=True),
            )

            # Send completion
            yield self._format_sse_event(
                "complete",
                {"id": request_id},
            )

        except Exception as e:
            yield self._format_sse_event(
                "error",
                {
                    "id": request_id,
                    "error": str(e),
                },
            )

    def _format_sse_event(
        self,
        event_type: str,
        data: Any,
    ) -> str:
        """Format SSE event."""
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

    def create_streaming_router(self, prefix: str = "") -> APIRouter:
        """Create router with streaming support."""
        router = self.create_router(prefix)

        @router.post("/stream")
        async def handle_streaming_mcp_request(
            request: Request,
        ) -> StreamingResponse:
            """Handle MCP request with streaming response."""
            try:
                body = await request.json()
                req = JSONRPCRequest(**body)

                claims = None
                if hasattr(request.state, "mcp_claims"):
                    claims = request.state.mcp_claims

                return StreamingResponse(
                    self.handle_streaming_request(req, claims),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                    },
                )
            except Exception:
                return JSONResponse(
                    content={
                        "jsonrpc": "2.0",
                        "error": {
                            "code": int(MCPErrorCode.PARSE_ERROR.value),
                            "message": "Invalid request",
                        },
                    },
                    status_code=400,
                )

        return router
