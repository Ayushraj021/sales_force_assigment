"""
MCP Core Module.

Contains authentication, middleware, exceptions, schemas, and transport implementations.
"""

from app.mcp.core.auth import MCPAuthenticator, MCPTokenClaims, MCP_SCOPES
from app.mcp.core.exceptions import MCPError, MCPErrorCode
from app.mcp.core.middleware import (
    RateLimiter,
    RateLimitConfig,
    MCPObservabilityMiddleware,
    AuditLogger,
    MCPAuditEvent,
)
from app.mcp.core.transport import MCPHttpTransport

__all__ = [
    "MCPAuthenticator",
    "MCPTokenClaims",
    "MCP_SCOPES",
    "MCPError",
    "MCPErrorCode",
    "RateLimiter",
    "RateLimitConfig",
    "MCPObservabilityMiddleware",
    "AuditLogger",
    "MCPAuditEvent",
    "MCPHttpTransport",
]
