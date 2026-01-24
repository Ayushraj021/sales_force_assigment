"""
Base Resource Classes for MCP.

Provides abstract base classes for MCP resources with caching support.
"""

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Type, TypeVar

import structlog

from app.mcp.config import CACHE_TTL_CONFIG, get_mcp_settings
from app.mcp.core.auth import MCPTokenClaims
from app.mcp.core.exceptions import MCPError, MCPErrorCode, resource_not_found

logger = structlog.get_logger("mcp.resources")

T = TypeVar("T", bound="BaseResource")


@dataclass
class ResourceMetadata:
    """Metadata for an MCP resource."""

    uri: str
    name: str
    description: str
    mime_type: str = "application/json"
    annotations: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "uri": self.uri,
            "name": self.name,
            "description": self.description,
            "mimeType": self.mime_type,
        }
        if self.annotations:
            result["annotations"] = self.annotations
        return result


@dataclass
class ResourceTemplate:
    """Template for parameterized resources."""

    uri_template: str
    name: str
    description: str
    mime_type: str = "application/json"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "uriTemplate": self.uri_template,
            "name": self.name,
            "description": self.description,
            "mimeType": self.mime_type,
        }


class ResourceCache:
    """
    Cache for MCP resources.

    Uses Redis for distributed caching with configurable TTL.
    """

    def __init__(self, redis_client=None):
        """
        Initialize cache.

        Args:
            redis_client: Redis client instance
        """
        self.redis = redis_client
        self.settings = get_mcp_settings()
        self.prefix = self.settings.MCP_CACHE_PREFIX

    def _make_key(self, resource_type: str, uri: str, org_id: str) -> str:
        """Generate cache key."""
        uri_hash = hashlib.md5(uri.encode()).hexdigest()[:12]
        return f"{self.prefix}resource:{resource_type}:{org_id}:{uri_hash}"

    async def get(
        self,
        resource_type: str,
        uri: str,
        org_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached resource.

        Args:
            resource_type: Type of resource
            uri: Resource URI
            org_id: Organization ID

        Returns:
            Cached data or None
        """
        if not self.redis or not self.settings.MCP_CACHE_ENABLED:
            return None

        try:
            key = self._make_key(resource_type, uri, org_id)
            data = await self.redis.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning("Cache get failed", error=str(e))
        return None

    async def set(
        self,
        resource_type: str,
        uri: str,
        org_id: str,
        data: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Cache a resource.

        Args:
            resource_type: Type of resource
            uri: Resource URI
            org_id: Organization ID
            data: Data to cache
            ttl: TTL in seconds (uses config default if not specified)

        Returns:
            True if cached successfully
        """
        if not self.redis or not self.settings.MCP_CACHE_ENABLED:
            return False

        try:
            key = self._make_key(resource_type, uri, org_id)
            cache_ttl = ttl or CACHE_TTL_CONFIG.get(
                resource_type, self.settings.MCP_DEFAULT_CACHE_TTL_SECONDS
            )
            await self.redis.set(key, json.dumps(data), expire=cache_ttl)
            return True
        except Exception as e:
            logger.warning("Cache set failed", error=str(e))
            return False

    async def invalidate(
        self,
        resource_type: str,
        uri: str,
        org_id: str,
    ) -> bool:
        """Invalidate a cached resource."""
        if not self.redis:
            return False

        try:
            key = self._make_key(resource_type, uri, org_id)
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.warning("Cache invalidate failed", error=str(e))
            return False

    async def invalidate_pattern(
        self,
        resource_type: str,
        org_id: str,
    ) -> int:
        """Invalidate all resources of a type for an org."""
        if not self.redis:
            return 0

        try:
            pattern = f"{self.prefix}resource:{resource_type}:{org_id}:*"
            deleted = 0
            async for key in self.redis.client.scan_iter(match=pattern):
                await self.redis.delete(key)
                deleted += 1
            return deleted
        except Exception as e:
            logger.warning("Cache invalidate pattern failed", error=str(e))
            return 0


class BaseResource(ABC):
    """
    Abstract base class for MCP resources.

    Provides common functionality for all resources including
    caching, authorization, and response formatting.

    Example:
        class DatasetsResource(BaseResource):
            resource_type = "datasets_list"
            uri_template = "data://{org}/datasets"

            async def fetch(self, uri, claims):
                # Fetch datasets from database
                return {"datasets": [...]}
    """

    # Subclasses must define these
    resource_type: str = ""
    uri_template: str = ""
    description: str = ""
    required_scope: str = ""

    def __init__(self, db=None, redis=None):
        """
        Initialize resource.

        Args:
            db: Database session factory
            redis: Redis client for caching
        """
        self.db = db
        self.cache = ResourceCache(redis_client=redis)
        self.settings = get_mcp_settings()
        self.logger = structlog.get_logger(f"mcp.resources.{self.resource_type}")

    def get_metadata(self) -> Dict[str, Any]:
        """Get resource metadata for listing."""
        return ResourceTemplate(
            uri_template=self.uri_template,
            name=self.resource_type,
            description=self.description,
        ).to_dict()

    async def handle(
        self,
        uri: str,
        claims: Optional[MCPTokenClaims] = None,
    ) -> Dict[str, Any]:
        """
        Handle resource request.

        Args:
            uri: Resource URI
            claims: Authenticated user claims

        Returns:
            Resource contents
        """
        # Extract org_id from claims or URI
        org_id = self._extract_org_id(uri, claims)

        # Check authorization
        if claims and self.required_scope:
            if not claims.has_scope(self.required_scope):
                raise MCPError(
                    code=MCPErrorCode.INSUFFICIENT_SCOPE,
                    message=f"Scope '{self.required_scope}' required",
                )

        # Check cache
        cached = await self.cache.get(self.resource_type, uri, org_id)
        if cached:
            self.logger.debug("Cache hit", uri=uri)
            return cached

        # Fetch from source
        try:
            data = await self.fetch(uri, claims)
        except MCPError:
            raise
        except Exception as e:
            self.logger.exception("Resource fetch failed", uri=uri, error=str(e))
            raise MCPError(
                code=MCPErrorCode.INTERNAL_ERROR,
                message=f"Failed to fetch resource: {str(e)}",
            )

        # Format response
        response = self.format_response(uri, data)

        # Cache the result
        await self.cache.set(self.resource_type, uri, org_id, response)

        return response

    @abstractmethod
    async def fetch(
        self,
        uri: str,
        claims: Optional[MCPTokenClaims],
    ) -> Dict[str, Any]:
        """
        Fetch resource data.

        Subclasses must implement this method.

        Args:
            uri: Resource URI
            claims: Authenticated user claims

        Returns:
            Raw resource data
        """
        pass

    def format_response(
        self,
        uri: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Format resource response for MCP.

        Args:
            uri: Resource URI
            data: Raw resource data

        Returns:
            Formatted response with MCP structure
        """
        return {
            "uri": uri,
            "mimeType": "application/json",
            "text": json.dumps(data),
        }

    def _extract_org_id(
        self,
        uri: str,
        claims: Optional[MCPTokenClaims],
    ) -> str:
        """Extract organization ID from claims or URI."""
        if claims:
            return claims.org_id

        # Try to parse from URI
        import re

        match = re.search(r"://([^/]+)/", uri)
        if match:
            return match.group(1)

        return "unknown"

    def _parse_uri_params(self, uri: str) -> Dict[str, str]:
        """Parse parameters from URI based on template."""
        import re

        # Convert template to regex
        pattern = self.uri_template.replace("{", "(?P<").replace("}", ">[^/]+)")
        match = re.match(pattern, uri)

        if match:
            return match.groupdict()
        return {}


class PaginatedResource(BaseResource):
    """
    Base class for paginated resources.

    Adds pagination support for large resource collections.
    """

    default_page_size: int = 20
    max_page_size: int = 100

    async def handle(
        self,
        uri: str,
        claims: Optional[MCPTokenClaims] = None,
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Handle paginated resource request."""
        org_id = self._extract_org_id(uri, claims)

        # Parse pagination params
        page_size = min(limit or self.default_page_size, self.max_page_size)

        # Check authorization
        if claims and self.required_scope:
            if not claims.has_scope(self.required_scope):
                raise MCPError(
                    code=MCPErrorCode.INSUFFICIENT_SCOPE,
                    message=f"Scope '{self.required_scope}' required",
                )

        # Fetch data with pagination
        try:
            data, next_cursor = await self.fetch_paginated(
                uri, claims, cursor, page_size
            )
        except MCPError:
            raise
        except Exception as e:
            self.logger.exception("Resource fetch failed", uri=uri, error=str(e))
            raise MCPError(
                code=MCPErrorCode.INTERNAL_ERROR,
                message=f"Failed to fetch resource: {str(e)}",
            )

        # Format response
        response = self.format_response(uri, data)
        if next_cursor:
            response["nextCursor"] = next_cursor

        return response

    async def fetch_paginated(
        self,
        uri: str,
        claims: Optional[MCPTokenClaims],
        cursor: Optional[str],
        limit: int,
    ) -> tuple[Dict[str, Any], Optional[str]]:
        """
        Fetch paginated resource data.

        Returns:
            Tuple of (data, next_cursor)
        """
        data = await self.fetch(uri, claims)
        return data, None
