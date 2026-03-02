"""
MCP Server Factory.

Creates and configures MCP servers for the sales forecasting platform.
"""

from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.mcp.config import get_mcp_settings
from app.mcp.core.auth import MCPAuthenticator, get_mcp_claims, MCPTokenClaims
from app.mcp.core.exceptions import MCPError, MCPErrorCode
from app.mcp.core.middleware import (
    AuditLogger,
    MCPObservabilityMiddleware,
    MCPSecurityMiddleware,
    RateLimiter,
)
from app.mcp.core.transport import (
    MCPHttpTransport,
    MCPServerInfo,
    MCPCapabilities,
    StreamingTransport,
)

logger = structlog.get_logger("mcp.server")


class MCPServerFactory:
    """
    Factory for creating MCP servers.

    Creates configured MCP server instances with proper
    authentication, rate limiting, and observability.

    Example:
        factory = MCPServerFactory(redis_client=redis)

        # Create data server
        data_server = factory.create_data_server()

        # Create models server
        models_server = factory.create_models_server()

        # Mount to FastAPI
        app.include_router(data_server, prefix="/mcp/data")
        app.include_router(models_server, prefix="/mcp/models")
    """

    def __init__(
        self,
        redis_client=None,
        db_session=None,
        celery_app=None,
    ):
        """
        Initialize factory.

        Args:
            redis_client: Redis client for caching and rate limiting
            db_session: Database session factory
            celery_app: Celery application for async tasks
        """
        self.redis = redis_client
        self.db = db_session
        self.celery = celery_app
        self.settings = get_mcp_settings()
        self.auth = MCPAuthenticator(secret_key=settings.SECRET_KEY)
        self.rate_limiter = RateLimiter(redis_client) if redis_client else None
        self.audit_logger = AuditLogger(redis_client=redis_client)

    def create_data_server(self) -> APIRouter:
        """
        Create MCP server for data operations.

        Provides access to datasets, schemas, quality reports, and previews.
        """
        transport = StreamingTransport(
            server_info=MCPServerInfo(
                name="mcp-data-server",
                version=self.settings.MCP_SERVER_VERSION,
            ),
            capabilities=MCPCapabilities(
                resources={"subscribe": False, "listChanged": True},
            ),
        )

        # Register resources (lazy import to avoid circular deps)
        self._register_data_resources(transport)

        # Register tools
        self._register_data_tools(transport)

        return self._create_router(transport, "data")

    def create_models_server(self) -> APIRouter:
        """
        Create MCP server for model operations.

        Provides access to model registry, training, and versioning.
        """
        transport = StreamingTransport(
            server_info=MCPServerInfo(
                name="mcp-models-server",
                version=self.settings.MCP_SERVER_VERSION,
            ),
            capabilities=MCPCapabilities(
                resources={"subscribe": False},
                tools={},
            ),
        )

        # Register resources
        self._register_model_resources(transport)

        # Register tools
        self._register_model_tools(transport)

        return self._create_router(transport, "models")

    def create_forecast_server(self) -> APIRouter:
        """
        Create MCP server for forecast operations.

        Provides predictions, decomposition, and explainability.
        """
        transport = StreamingTransport(
            server_info=MCPServerInfo(
                name="mcp-forecast-server",
                version=self.settings.MCP_SERVER_VERSION,
            ),
            capabilities=MCPCapabilities(
                resources={"subscribe": True},
                tools={},
            ),
        )

        # Register resources and tools (to be implemented)
        self._register_forecast_resources(transport)
        self._register_forecast_tools(transport)

        return self._create_router(transport, "forecast")

    def create_optimization_server(self) -> APIRouter:
        """
        Create MCP server for optimization operations.

        Provides budget optimization, attribution, and ROI analysis.
        """
        transport = StreamingTransport(
            server_info=MCPServerInfo(
                name="mcp-optimization-server",
                version=self.settings.MCP_SERVER_VERSION,
            ),
            capabilities=MCPCapabilities(
                tools={},
            ),
        )

        # Register tools
        self._register_optimization_tools(transport)

        return self._create_router(transport, "optimization")

    def _create_router(
        self,
        transport: MCPHttpTransport,
        server_type: str,
    ) -> APIRouter:
        """Create a configured router for a transport."""
        router = transport.create_streaming_router()

        # Note: Authentication is handled via FastAPI dependencies in core/auth.py
        # (get_mcp_claims, require_mcp_scope) which should be added to individual
        # endpoints as needed. Rate limiting is handled via the RateLimiter service.
        #
        # For MCP servers, auth is optional and configured via MCP_REQUIRE_AUTH.
        # When auth is required, endpoints should use the get_mcp_claims dependency.

        return router

    def _register_data_resources(self, transport: MCPHttpTransport) -> None:
        """Register data resources."""
        from app.mcp.resources.data_resources import (
            DatasetsResource,
            DatasetSchemaResource,
            DatasetQualityResource,
            DatasetPreviewResource,
        )

        datasets = DatasetsResource(db=self.db, redis=self.redis)
        schema = DatasetSchemaResource(db=self.db, redis=self.redis)
        quality = DatasetQualityResource(db=self.db, redis=self.redis)
        preview = DatasetPreviewResource(db=self.db, redis=self.redis)

        transport.register_resource_handler(
            "data://{org}/datasets",
            datasets.handle,
        )
        transport.register_resource_handler(
            "data://{org}/datasets/{id}/schema",
            schema.handle,
        )
        transport.register_resource_handler(
            "data://{org}/datasets/{id}/quality",
            quality.handle,
        )
        transport.register_resource_handler(
            "data://{org}/datasets/{id}/preview",
            preview.handle,
        )

    def _register_data_tools(self, transport: MCPHttpTransport) -> None:
        """Register data tools."""
        from app.mcp.tools.data_tools import (
            ValidateDataTool,
            RunETLPipelineTool,
            CheckDataQualityTool,
        )

        validate = ValidateDataTool(db=self.db)
        etl = RunETLPipelineTool(db=self.db, celery=self.celery)
        quality = CheckDataQualityTool(db=self.db)

        transport.register_tool_handler("validate_data", validate)
        transport.register_tool_handler("run_etl_pipeline", etl)
        transport.register_tool_handler("check_data_quality", quality)

    def _register_model_resources(self, transport: MCPHttpTransport) -> None:
        """Register model resources."""
        from app.mcp.resources.model_resources import (
            ModelRegistryResource,
            ModelDetailResource,
            ModelPerformanceResource,
            ModelParametersResource,
        )

        registry = ModelRegistryResource(db=self.db, redis=self.redis)
        detail = ModelDetailResource(db=self.db, redis=self.redis)
        performance = ModelPerformanceResource(db=self.db, redis=self.redis)
        parameters = ModelParametersResource(db=self.db, redis=self.redis)

        transport.register_resource_handler(
            "models://{org}/registry",
            registry.handle,
        )
        transport.register_resource_handler(
            "models://{org}/registry/{id}",
            detail.handle,
        )
        transport.register_resource_handler(
            "models://{org}/registry/{id}/performance",
            performance.handle,
        )
        transport.register_resource_handler(
            "models://{org}/registry/{id}/parameters",
            parameters.handle,
        )

    def _register_model_tools(self, transport: MCPHttpTransport) -> None:
        """Register model tools."""
        from app.mcp.tools.model_tools import (
            TrainModelTool,
            GetTrainingStatusTool,
            RunInferenceTool,
            CompareModelsTool,
            PromoteModelTool,
        )

        train = TrainModelTool(db=self.db, celery=self.celery)
        status = GetTrainingStatusTool(db=self.db, celery=self.celery)
        inference = RunInferenceTool(db=self.db)
        compare = CompareModelsTool(db=self.db)
        promote = PromoteModelTool(db=self.db)

        transport.register_tool_handler("train_model", train)
        transport.register_tool_handler("get_training_status", status)
        transport.register_tool_handler("run_inference", inference)
        transport.register_tool_handler("compare_models", compare)
        transport.register_tool_handler("promote_model", promote)

    def _register_forecast_resources(self, transport: MCPHttpTransport) -> None:
        """Register forecast resources (placeholder)."""
        pass

    def _register_forecast_tools(self, transport: MCPHttpTransport) -> None:
        """Register forecast tools (placeholder)."""
        pass

    def _register_optimization_tools(self, transport: MCPHttpTransport) -> None:
        """Register optimization tools."""
        from app.mcp.tools.optimization_tools import (
            OptimizeBudgetTool,
            AnalyzeROITool,
            RunWhatIfScenarioTool,
            AnalyzeAttributionTool,
        )

        optimize = OptimizeBudgetTool(db=self.db)
        roi = AnalyzeROITool(db=self.db)
        whatif = RunWhatIfScenarioTool(db=self.db)
        attribution = AnalyzeAttributionTool(db=self.db)

        transport.register_tool_handler("optimize_budget", optimize)
        transport.register_tool_handler("analyze_roi", roi)
        transport.register_tool_handler("run_what_if_scenario", whatif)
        transport.register_tool_handler("analyze_attribution", attribution)


def create_mcp_server(
    redis_client=None,
    db_session=None,
    celery_app=None,
) -> APIRouter:
    """
    Create the main MCP server router.

    Combines all MCP sub-servers into a single router.

    Args:
        redis_client: Redis client instance
        db_session: Database session factory
        celery_app: Celery application

    Returns:
        FastAPI APIRouter with all MCP endpoints
    """
    mcp_settings = get_mcp_settings()

    if not mcp_settings.MCP_ENABLED:
        logger.info("MCP server is disabled")
        router = APIRouter()

        @router.get("/health")
        async def mcp_disabled():
            return {"status": "disabled", "message": "MCP server is disabled"}

        return router

    factory = MCPServerFactory(
        redis_client=redis_client,
        db_session=db_session,
        celery_app=celery_app,
    )

    # Create main router
    router = APIRouter(tags=["MCP"])

    # Mount sub-servers
    router.include_router(
        factory.create_data_server(),
        prefix="/data",
        tags=["MCP Data"],
    )
    router.include_router(
        factory.create_models_server(),
        prefix="/models",
        tags=["MCP Models"],
    )
    router.include_router(
        factory.create_forecast_server(),
        prefix="/forecast",
        tags=["MCP Forecast"],
    )
    router.include_router(
        factory.create_optimization_server(),
        prefix="/optimization",
        tags=["MCP Optimization"],
    )

    # Add health check at root
    @router.get("/health")
    async def mcp_health():
        """MCP server health check."""
        return {
            "status": "healthy",
            "version": mcp_settings.MCP_SERVER_VERSION,
            "servers": ["data", "models", "forecast", "optimization"],
        }

    @router.get("/info")
    async def mcp_info():
        """MCP server information."""
        return {
            "name": mcp_settings.MCP_SERVER_NAME,
            "version": mcp_settings.MCP_SERVER_VERSION,
            "protocol_version": "2024-11-05",
            "servers": {
                "data": {
                    "path": "/mcp/data",
                    "description": "Dataset management, ETL, connectors",
                },
                "models": {
                    "path": "/mcp/models",
                    "description": "Model registry, training, versioning",
                },
                "forecast": {
                    "path": "/mcp/forecast",
                    "description": "Predictions, decomposition, explainability",
                },
                "optimization": {
                    "path": "/mcp/optimization",
                    "description": "Budget optimization, attribution, ROI",
                },
            },
            "authentication": "OAuth 2.1 Bearer Token",
            "documentation": "/docs#mcp",
        }

    logger.info(
        "MCP server created",
        version=mcp_settings.MCP_SERVER_VERSION,
        servers=["data", "models", "forecast", "optimization"],
    )

    return router


def create_mcp_app() -> FastAPI:
    """
    Create a standalone MCP FastAPI application.

    For running MCP as a separate service.

    Returns:
        FastAPI application
    """
    mcp_settings = get_mcp_settings()

    app = FastAPI(
        title="Sales Forecasting MCP Server",
        version=mcp_settings.MCP_SERVER_VERSION,
        description="Model Context Protocol server for sales forecasting platform",
    )

    # Add CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=mcp_settings.MCP_ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add security middleware
    app.add_middleware(MCPSecurityMiddleware)

    # Add observability middleware
    app.add_middleware(
        MCPObservabilityMiddleware,
        server_name=mcp_settings.MCP_SERVER_NAME,
    )

    # Create and mount MCP router
    mcp_router = create_mcp_server()
    app.include_router(mcp_router, prefix=mcp_settings.MCP_BASE_PATH)

    return app
