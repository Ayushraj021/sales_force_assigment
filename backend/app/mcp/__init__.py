"""
MCP (Model Context Protocol) Server Package.

Provides AI assistants with semantic access to sales forecasting
data, models, analytics, and optimization capabilities.
"""

from app.mcp.server import create_mcp_server, MCPServerFactory
from app.mcp.config import MCPSettings, get_mcp_settings

__all__ = [
    "create_mcp_server",
    "MCPServerFactory",
    "MCPSettings",
    "get_mcp_settings",
]

__version__ = "1.0.0"
