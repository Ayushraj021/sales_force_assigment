"""
MCP Configuration Module.

Extends application settings with MCP-specific configuration.
"""

from functools import lru_cache
from typing import Dict, List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class MCPSettings(BaseSettings):
    """MCP-specific configuration extending application settings."""

    # Server Configuration
    MCP_ENABLED: bool = Field(default=True, description="Enable MCP server")
    MCP_BASE_PATH: str = Field(default="/mcp", description="Base path for MCP endpoints")
    MCP_SERVER_NAME: str = Field(
        default="sales-forecast-mcp", description="MCP server identifier"
    )
    MCP_SERVER_VERSION: str = Field(default="1.0.0", description="MCP server version")

    # Authentication
    MCP_TOKEN_AUDIENCE: str = Field(
        default="mcp-server", description="Expected JWT audience"
    )
    MCP_TOKEN_ISSUER: str = Field(
        default="sales-forecast", description="Expected JWT issuer"
    )
    MCP_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30, description="Access token expiration in minutes"
    )
    MCP_REQUIRE_AUTH: bool = Field(
        default=True, description="Require authentication for all MCP endpoints"
    )

    # Rate Limiting
    MCP_RATE_LIMIT_ENABLED: bool = Field(
        default=True, description="Enable rate limiting"
    )
    MCP_DEFAULT_RATE_LIMIT_PER_MINUTE: int = Field(
        default=100, description="Default requests per minute"
    )
    MCP_DEFAULT_RATE_LIMIT_PER_HOUR: int = Field(
        default=2000, description="Default requests per hour"
    )
    MCP_DEFAULT_BURST_LIMIT: int = Field(
        default=20, description="Default burst limit"
    )

    # Caching
    MCP_CACHE_ENABLED: bool = Field(default=True, description="Enable resource caching")
    MCP_DEFAULT_CACHE_TTL_SECONDS: int = Field(
        default=300, description="Default cache TTL in seconds"
    )
    MCP_CACHE_PREFIX: str = Field(
        default="mcp:", description="Redis cache key prefix"
    )

    # Async Jobs
    MCP_JOB_TIMEOUT_SECONDS: int = Field(
        default=3600, description="Maximum job execution time"
    )
    MCP_JOB_POLL_INTERVAL_SECONDS: int = Field(
        default=5, description="Job status polling interval"
    )
    MCP_MAX_CONCURRENT_JOBS: int = Field(
        default=10, description="Maximum concurrent async jobs per org"
    )

    # Observability
    MCP_METRICS_ENABLED: bool = Field(
        default=True, description="Enable Prometheus metrics"
    )
    MCP_TRACING_ENABLED: bool = Field(
        default=True, description="Enable OpenTelemetry tracing"
    )
    MCP_AUDIT_LOGGING_ENABLED: bool = Field(
        default=True, description="Enable audit logging"
    )
    MCP_LOG_REQUEST_BODY: bool = Field(
        default=False, description="Log request bodies (disable in production)"
    )
    MCP_LOG_RESPONSE_BODY: bool = Field(
        default=False, description="Log response bodies (disable in production)"
    )

    # Transport Configuration
    MCP_MAX_REQUEST_SIZE_BYTES: int = Field(
        default=10 * 1024 * 1024, description="Maximum request size (10MB)"
    )
    MCP_REQUEST_TIMEOUT_SECONDS: int = Field(
        default=60, description="Request timeout"
    )
    MCP_STREAMING_ENABLED: bool = Field(
        default=True, description="Enable streaming responses"
    )

    # Resource Configuration
    MCP_MAX_PREVIEW_ROWS: int = Field(
        default=10, description="Maximum rows in data preview"
    )
    MCP_MAX_RESOURCE_SIZE_BYTES: int = Field(
        default=5 * 1024 * 1024, description="Maximum resource response size (5MB)"
    )

    # Tool Configuration
    MCP_TOOL_EXECUTION_TIMEOUT: int = Field(
        default=300, description="Tool execution timeout in seconds"
    )
    MCP_ALLOW_DESTRUCTIVE_TOOLS: bool = Field(
        default=False, description="Allow tools that modify/delete data"
    )

    # Security
    MCP_ALLOWED_ORIGINS: List[str] = Field(
        default=["*"], description="Allowed CORS origins"
    )
    MCP_SECURE_HEADERS_ENABLED: bool = Field(
        default=True, description="Enable security headers"
    )

    @field_validator("MCP_ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v):
        """Parse comma-separated origins."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    class Config:
        env_prefix = ""
        env_file = ".env"
        extra = "ignore"


# Rate limit configurations by tier
RATE_LIMIT_TIERS: Dict[str, Dict[str, int]] = {
    "free": {
        "requests_per_minute": 10,
        "requests_per_hour": 100,
        "burst_limit": 5,
    },
    "starter": {
        "requests_per_minute": 30,
        "requests_per_hour": 500,
        "burst_limit": 10,
    },
    "professional": {
        "requests_per_minute": 100,
        "requests_per_hour": 2000,
        "burst_limit": 20,
    },
    "enterprise": {
        "requests_per_minute": 500,
        "requests_per_hour": 10000,
        "burst_limit": 50,
    },
}

# Cache TTL configurations by resource type
CACHE_TTL_CONFIG: Dict[str, int] = {
    "datasets_list": 300,  # 5 minutes
    "dataset_schema": 900,  # 15 minutes
    "dataset_quality": 1800,  # 30 minutes
    "dataset_preview": 300,  # 5 minutes
    "model_registry": 300,  # 5 minutes
    "model_detail": 300,  # 5 minutes
    "model_performance": 900,  # 15 minutes
    "model_parameters": 900,  # 15 minutes
    "forecast_results": 600,  # 10 minutes
    "optimization_results": 600,  # 10 minutes
}


@lru_cache()
def get_mcp_settings() -> MCPSettings:
    """Get cached MCP settings instance."""
    return MCPSettings()
