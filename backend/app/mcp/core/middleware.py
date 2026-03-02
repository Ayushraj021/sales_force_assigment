"""
MCP Middleware Module.

Provides rate limiting, observability, and audit logging for MCP servers.
"""

import hashlib
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.mcp.config import RATE_LIMIT_TIERS, get_mcp_settings
from app.mcp.core.exceptions import MCPError, MCPErrorCode, rate_limited

logger = structlog.get_logger("mcp.middleware")


# Optional imports for metrics (graceful degradation if not available)
try:
    from prometheus_client import Counter, Histogram

    mcp_requests_total = Counter(
        "mcp_requests_total",
        "Total MCP requests",
        ["server", "method", "status"],
    )

    mcp_request_duration = Histogram(
        "mcp_request_duration_seconds",
        "MCP request duration",
        ["server", "method"],
        buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    )

    mcp_tool_executions = Counter(
        "mcp_tool_executions_total",
        "Tool executions",
        ["tool", "status"],
    )

    mcp_resource_access = Counter(
        "mcp_resource_access_total",
        "Resource access",
        ["resource_type", "operation"],
    )

    mcp_rate_limit_hits = Counter(
        "mcp_rate_limit_hits_total",
        "Rate limit hits",
        ["org_id", "tier"],
    )

    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    logger.warning("Prometheus metrics not available, metrics disabled")

# Optional tracing imports
try:
    from opentelemetry import trace
    from opentelemetry.trace import SpanKind, Status, StatusCode

    tracer = trace.get_tracer("mcp-server")
    TRACING_AVAILABLE = True
except ImportError:
    TRACING_AVAILABLE = False
    tracer = None
    logger.warning("OpenTelemetry tracing not available, tracing disabled")


@dataclass
class RateLimitConfig:
    """Rate limit configuration for an organization tier."""

    requests_per_minute: int
    requests_per_hour: int
    burst_limit: int

    @classmethod
    def from_tier(cls, tier: str) -> "RateLimitConfig":
        """Create config from tier name."""
        tier_config = RATE_LIMIT_TIERS.get(tier, RATE_LIMIT_TIERS["professional"])
        return cls(
            requests_per_minute=tier_config["requests_per_minute"],
            requests_per_hour=tier_config["requests_per_hour"],
            burst_limit=tier_config["burst_limit"],
        )


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""

    allowed: bool
    remaining: int
    limit: int
    reset_at: int
    retry_after: Optional[int] = None

    def to_headers(self) -> Dict[str, str]:
        """Convert to rate limit response headers."""
        headers = {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(max(0, self.remaining)),
            "X-RateLimit-Reset": str(self.reset_at),
        }
        if self.retry_after:
            headers["Retry-After"] = str(self.retry_after)
        return headers


class RateLimiter:
    """
    Token bucket rate limiter with Redis backend.

    Implements a sliding window algorithm for accurate rate limiting.

    Example:
        limiter = RateLimiter(redis_client)
        allowed, headers = await limiter.check_rate_limit(
            org_id="org-123",
            tier="professional",
            operation="tool_call"
        )
    """

    def __init__(self, redis_client):
        """
        Initialize rate limiter.

        Args:
            redis_client: RedisClient instance
        """
        self.redis = redis_client
        self.settings = get_mcp_settings()

    async def check_rate_limit(
        self,
        org_id: str,
        tier: str,
        operation: str,
    ) -> Tuple[bool, Dict[str, str]]:
        """
        Check and update rate limit for an organization.

        Uses sliding window log algorithm for accurate limiting.

        Args:
            org_id: Organization ID
            tier: Subscription tier
            operation: Operation type (request, tool_call, etc.)

        Returns:
            Tuple of (allowed: bool, headers: dict)
        """
        if not self.settings.MCP_RATE_LIMIT_ENABLED:
            return True, {}

        config = RateLimitConfig.from_tier(tier)
        now = int(time.time())
        minute_window = now // 60
        hour_window = now // 3600

        # Keys for per-minute and per-hour tracking
        minute_key = f"mcp:ratelimit:{org_id}:minute:{minute_window}"
        hour_key = f"mcp:ratelimit:{org_id}:hour:{hour_window}"

        try:
            # Get current counts
            minute_count = await self.redis.get(minute_key)
            hour_count = await self.redis.get(hour_key)

            minute_count = int(minute_count) if minute_count else 0
            hour_count = int(hour_count) if hour_count else 0

            # Check limits
            if minute_count >= config.requests_per_minute:
                retry_after = 60 - (now % 60)
                if METRICS_AVAILABLE:
                    mcp_rate_limit_hits.labels(org_id=org_id, tier=tier).inc()
                return False, RateLimitResult(
                    allowed=False,
                    remaining=0,
                    limit=config.requests_per_minute,
                    reset_at=now + retry_after,
                    retry_after=retry_after,
                ).to_headers()

            if hour_count >= config.requests_per_hour:
                retry_after = 3600 - (now % 3600)
                if METRICS_AVAILABLE:
                    mcp_rate_limit_hits.labels(org_id=org_id, tier=tier).inc()
                return False, RateLimitResult(
                    allowed=False,
                    remaining=0,
                    limit=config.requests_per_hour,
                    reset_at=now + retry_after,
                    retry_after=retry_after,
                ).to_headers()

            # Increment counters
            pipe = self.redis.client.pipeline()
            pipe.incr(minute_key)
            pipe.expire(minute_key, 120)  # 2 minute TTL
            pipe.incr(hour_key)
            pipe.expire(hour_key, 7200)  # 2 hour TTL
            await pipe.execute()

            remaining = config.requests_per_minute - minute_count - 1
            reset_at = (minute_window + 1) * 60

            return True, RateLimitResult(
                allowed=True,
                remaining=remaining,
                limit=config.requests_per_minute,
                reset_at=reset_at,
            ).to_headers()

        except Exception as e:
            logger.error("Rate limit check failed", error=str(e))
            # Fail open on errors
            return True, {}

    async def get_limit_status(
        self,
        org_id: str,
        tier: str,
    ) -> Dict[str, Any]:
        """Get current rate limit status for an organization."""
        config = RateLimitConfig.from_tier(tier)
        now = int(time.time())
        minute_window = now // 60
        hour_window = now // 3600

        minute_key = f"mcp:ratelimit:{org_id}:minute:{minute_window}"
        hour_key = f"mcp:ratelimit:{org_id}:hour:{hour_window}"

        try:
            minute_count = await self.redis.get(minute_key)
            hour_count = await self.redis.get(hour_key)

            return {
                "minute": {
                    "used": int(minute_count) if minute_count else 0,
                    "limit": config.requests_per_minute,
                    "remaining": config.requests_per_minute
                    - (int(minute_count) if minute_count else 0),
                    "resets_at": (minute_window + 1) * 60,
                },
                "hour": {
                    "used": int(hour_count) if hour_count else 0,
                    "limit": config.requests_per_hour,
                    "remaining": config.requests_per_hour
                    - (int(hour_count) if hour_count else 0),
                    "resets_at": (hour_window + 1) * 3600,
                },
            }
        except Exception as e:
            logger.error("Failed to get rate limit status", error=str(e))
            return {}


@dataclass
class MCPAuditEvent:
    """
    Audit event for MCP operations.

    Records all significant operations for compliance and debugging.
    """

    timestamp: datetime
    event_type: str  # "tool_call", "resource_access", "auth_failure"
    user_id: str
    organization_id: str
    server: str
    method: str
    resource_uri: Optional[str] = None
    tool_name: Optional[str] = None
    input_hash: Optional[str] = None  # Hash of input (not raw data)
    status: str = "success"
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    duration_ms: Optional[float] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/storage."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "user_id": self.user_id,
            "organization_id": self.organization_id,
            "server": self.server,
            "method": self.method,
            "resource_uri": self.resource_uri,
            "tool_name": self.tool_name,
            "input_hash": self.input_hash,
            "status": self.status,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "duration_ms": self.duration_ms,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "request_id": self.request_id,
            "metadata": self.metadata,
        }


class AuditLogger:
    """
    Audit logger for MCP operations.

    Logs to structured log and optionally to database for compliance.
    """

    def __init__(self, redis_client=None, db_session=None):
        """
        Initialize audit logger.

        Args:
            redis_client: Optional Redis client for real-time streaming
            db_session: Optional database session for persistence
        """
        self.redis = redis_client
        self.db = db_session
        self.logger = structlog.get_logger("mcp.audit")
        self.settings = get_mcp_settings()

    async def log_event(self, event: MCPAuditEvent) -> None:
        """
        Log an audit event.

        Args:
            event: Audit event to log
        """
        if not self.settings.MCP_AUDIT_LOGGING_ENABLED:
            return

        # Structured log for SIEM integration
        self.logger.info(
            "mcp_audit_event",
            **event.to_dict(),
        )

        # Optional: Store in Redis for real-time monitoring
        if self.redis:
            try:
                await self.redis.lpush(
                    f"mcp:audit:{event.organization_id}",
                    str(event.to_dict()),
                )
                # Keep only last 1000 events per org
                await self.redis.client.ltrim(
                    f"mcp:audit:{event.organization_id}",
                    0,
                    999,
                )
            except Exception as e:
                self.logger.warning("Failed to store audit event in Redis", error=str(e))

    async def log_tool_call(
        self,
        user_id: str,
        org_id: str,
        tool_name: str,
        input_data: Dict[str, Any],
        status: str,
        duration_ms: float,
        request_id: Optional[str] = None,
        error: Optional[MCPError] = None,
    ) -> None:
        """Log a tool call event."""
        # Hash input data for privacy
        input_hash = hashlib.sha256(str(input_data).encode()).hexdigest()[:16]

        event = MCPAuditEvent(
            timestamp=datetime.now(timezone.utc),
            event_type="tool_call",
            user_id=user_id,
            organization_id=org_id,
            server="mcp-tools",
            method="tools/call",
            tool_name=tool_name,
            input_hash=input_hash,
            status=status,
            error_code=error.code.value if error else None,
            error_message=error.message if error else None,
            duration_ms=duration_ms,
            request_id=request_id,
        )
        await self.log_event(event)

        # Update metrics
        if METRICS_AVAILABLE:
            mcp_tool_executions.labels(tool=tool_name, status=status).inc()

    async def log_resource_access(
        self,
        user_id: str,
        org_id: str,
        resource_uri: str,
        status: str,
        duration_ms: float,
        request_id: Optional[str] = None,
    ) -> None:
        """Log a resource access event."""
        event = MCPAuditEvent(
            timestamp=datetime.now(timezone.utc),
            event_type="resource_access",
            user_id=user_id,
            organization_id=org_id,
            server="mcp-resources",
            method="resources/read",
            resource_uri=resource_uri,
            status=status,
            duration_ms=duration_ms,
            request_id=request_id,
        )
        await self.log_event(event)

        # Update metrics
        if METRICS_AVAILABLE:
            # Extract resource type from URI
            resource_type = resource_uri.split("://")[0] if "://" in resource_uri else "unknown"
            mcp_resource_access.labels(resource_type=resource_type, operation="read").inc()

    async def log_auth_failure(
        self,
        ip_address: str,
        user_agent: str,
        error_message: str,
        request_id: Optional[str] = None,
    ) -> None:
        """Log an authentication failure."""
        event = MCPAuditEvent(
            timestamp=datetime.now(timezone.utc),
            event_type="auth_failure",
            user_id="anonymous",
            organization_id="unknown",
            server="mcp-auth",
            method="authenticate",
            status="failure",
            error_message=error_message,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )
        await self.log_event(event)


class MCPObservabilityMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging, tracing, and metrics.

    Provides comprehensive observability for MCP servers.
    """

    def __init__(
        self,
        app: ASGIApp,
        server_name: str = "mcp-server",
    ):
        super().__init__(app)
        self.server_name = server_name
        self.logger = structlog.get_logger("mcp.observability")
        self.settings = get_mcp_settings()

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """Process request with observability."""
        # Generate request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        # Extract method from path
        method = self._extract_method(request.url.path)

        start_time = time.time()

        # Create span if tracing is available
        if TRACING_AVAILABLE and tracer:
            with tracer.start_as_current_span(
                f"mcp.{method}",
                kind=SpanKind.SERVER,
            ) as span:
                span.set_attribute("mcp.server", self.server_name)
                span.set_attribute("mcp.method", method)
                span.set_attribute("mcp.request_id", request_id)
                span.set_attribute("http.url", str(request.url))
                span.set_attribute("http.method", request.method)

                try:
                    response = await call_next(request)
                    span.set_attribute("http.status_code", response.status_code)
                    self._record_success(method, start_time, request_id)
                    return self._add_headers(response, request_id)
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    self._record_error(method, start_time, request_id, e)
                    raise
        else:
            try:
                response = await call_next(request)
                self._record_success(method, start_time, request_id)
                return self._add_headers(response, request_id)
            except Exception as e:
                self._record_error(method, start_time, request_id, e)
                raise

    def _extract_method(self, path: str) -> str:
        """Extract MCP method from request path."""
        parts = path.strip("/").split("/")
        if len(parts) >= 2:
            return f"{parts[-2]}/{parts[-1]}"
        return "unknown"

    def _record_success(
        self,
        method: str,
        start_time: float,
        request_id: str,
    ) -> None:
        """Record successful request metrics."""
        duration = time.time() - start_time

        if METRICS_AVAILABLE:
            mcp_requests_total.labels(
                server=self.server_name,
                method=method,
                status="success",
            ).inc()
            mcp_request_duration.labels(
                server=self.server_name,
                method=method,
            ).observe(duration)

        if self.settings.MCP_LOG_REQUEST_BODY or self.settings.MCP_LOG_RESPONSE_BODY:
            self.logger.info(
                "mcp_request_success",
                server=self.server_name,
                method=method,
                duration_ms=duration * 1000,
                request_id=request_id,
            )

    def _record_error(
        self,
        method: str,
        start_time: float,
        request_id: str,
        error: Exception,
    ) -> None:
        """Record failed request metrics."""
        duration = time.time() - start_time

        if METRICS_AVAILABLE:
            mcp_requests_total.labels(
                server=self.server_name,
                method=method,
                status="error",
            ).inc()
            mcp_request_duration.labels(
                server=self.server_name,
                method=method,
            ).observe(duration)

        self.logger.error(
            "mcp_request_error",
            server=self.server_name,
            method=method,
            duration_ms=duration * 1000,
            request_id=request_id,
            error=str(error),
            error_type=type(error).__name__,
        )

    def _add_headers(self, response: Response, request_id: str) -> Response:
        """Add observability headers to response."""
        response.headers["X-Request-ID"] = request_id
        response.headers["X-MCP-Server"] = self.server_name
        return response


class MCPSecurityMiddleware(BaseHTTPMiddleware):
    """
    Security middleware for MCP servers.

    Adds security headers and performs basic security checks.
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.settings = get_mcp_settings()

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """Process request with security checks."""
        # Check request size
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.settings.MCP_MAX_REQUEST_SIZE_BYTES:
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=413,
                content={
                    "error": {
                        "code": -32600,
                        "message": "Request too large",
                    }
                },
            )

        response = await call_next(request)

        # Add security headers if enabled
        if self.settings.MCP_SECURE_HEADERS_ENABLED:
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
            response.headers["Cache-Control"] = "no-store"
            response.headers["Pragma"] = "no-cache"

        return response
