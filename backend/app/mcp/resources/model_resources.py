"""
Model Resources for MCP.

Provides read-only access to model registry, details, performance, and parameters.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog

from app.mcp.core.auth import MCPTokenClaims
from app.mcp.core.exceptions import MCPError, MCPErrorCode, resource_not_found
from app.mcp.formatters.insight_formatter import format_model_performance
from app.mcp.resources.base import BaseResource, PaginatedResource

logger = structlog.get_logger("mcp.resources.models")


class ModelRegistryResource(PaginatedResource):
    """
    List all models with status.

    URI Pattern: models://{org}/registry
    Scope: models:read
    """

    resource_type = "model_registry"
    uri_template = "models://{org}/registry"
    description = "List all models in the registry with status"
    required_scope = "models:read"

    async def fetch(
        self,
        uri: str,
        claims: Optional[MCPTokenClaims],
    ) -> Dict[str, Any]:
        """Fetch model registry."""
        if not claims:
            raise MCPError(
                code=MCPErrorCode.AUTHENTICATION_REQUIRED,
                message="Authentication required to list models",
            )

        org_id = claims.org_id
        models = await self._get_models(org_id)

        # Format for LLM consumption
        formatted = []
        for model in models:
            formatted.append({
                "id": str(model.get("id", "")),
                "name": model.get("name", "Unnamed"),
                "type": model.get("model_type", "unknown"),
                "stage": model.get("stage", "development"),
                "version": model.get("version", "1.0.0"),
                "created_at": model.get("created_at", ""),
                "updated_at": model.get("updated_at", ""),
                "performance_summary": self._summarize_performance(model),
            })

        # Group by stage
        by_stage = {
            "production": [m for m in formatted if m["stage"] == "production"],
            "staging": [m for m in formatted if m["stage"] == "staging"],
            "development": [m for m in formatted if m["stage"] == "development"],
            "archived": [m for m in formatted if m["stage"] == "archived"],
        }

        return {
            "models": formatted,
            "total_count": len(formatted),
            "by_stage": {
                stage: len(models) for stage, models in by_stage.items()
            },
            "organization_id": org_id,
            "summary": self._generate_registry_summary(by_stage),
        }

    async def _get_models(self, org_id: str) -> List[Dict[str, Any]]:
        """Get models from database."""
        if not self.db:
            # Mock data
            return [
                {
                    "id": "model-001",
                    "name": "Q4 MMM Model",
                    "model_type": "pymc_mmm",
                    "stage": "production",
                    "version": "2.1.0",
                    "created_at": "2024-03-15T10:00:00Z",
                    "updated_at": "2024-06-01T14:30:00Z",
                    "metrics": {"mape": 0.085, "r2": 0.92},
                },
                {
                    "id": "model-002",
                    "name": "Regional Forecast",
                    "model_type": "prophet",
                    "stage": "staging",
                    "version": "1.5.0",
                    "created_at": "2024-05-01T09:00:00Z",
                    "updated_at": "2024-06-15T11:15:00Z",
                    "metrics": {"mape": 0.12, "r2": 0.88},
                },
            ]

        # Real database query
        from sqlalchemy import select
        from app.infrastructure.database.models.model import Model

        async with self.db() as session:
            result = await session.execute(
                select(Model).where(Model.organization_id == UUID(org_id))
            )
            models = result.scalars().all()

            return [
                {
                    "id": str(m.id),
                    "name": m.name,
                    "model_type": m.model_type,
                    "stage": m.stage,
                    "version": m.version,
                    "created_at": m.created_at.isoformat() if m.created_at else "",
                    "updated_at": m.updated_at.isoformat() if m.updated_at else "",
                    "metrics": m.metrics or {},
                }
                for m in models
            ]

    def _summarize_performance(self, model: Dict[str, Any]) -> str:
        """Generate performance summary."""
        metrics = model.get("metrics", {})
        mape = metrics.get("mape", 0)
        r2 = metrics.get("r2", 0)

        if mape and r2:
            return f"MAPE: {mape*100:.1f}%, R²: {r2*100:.0f}%"
        return "Performance metrics not available"

    def _generate_registry_summary(
        self,
        by_stage: Dict[str, List],
    ) -> str:
        """Generate registry summary."""
        prod = len(by_stage.get("production", []))
        staging = len(by_stage.get("staging", []))
        dev = len(by_stage.get("development", []))

        return f"{prod} production, {staging} staging, {dev} in development"


class ModelDetailResource(BaseResource):
    """
    Model detail with versions.

    URI Pattern: models://{org}/registry/{id}
    Scope: models:read
    """

    resource_type = "model_detail"
    uri_template = "models://{org}/registry/{id}"
    description = "Get model details including version history"
    required_scope = "models:read"

    async def fetch(
        self,
        uri: str,
        claims: Optional[MCPTokenClaims],
    ) -> Dict[str, Any]:
        """Fetch model details."""
        params = self._parse_uri_params(uri)
        model_id = params.get("id", "")

        if not model_id:
            raise MCPError(
                code=MCPErrorCode.INVALID_PARAMS,
                message="Model ID is required",
            )

        model = await self._get_model(model_id, claims.org_id if claims else "")

        if not model:
            raise resource_not_found("Model", model_id)

        return model

    async def _get_model(
        self,
        model_id: str,
        org_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get model details from database."""
        if not self.db:
            # Mock data
            return {
                "id": model_id,
                "name": "Q4 MMM Model",
                "description": "Marketing Mix Model for Q4 campaign optimization",
                "model_type": "pymc_mmm",
                "stage": "production",
                "current_version": "2.1.0",
                "created_at": "2024-03-15T10:00:00Z",
                "updated_at": "2024-06-01T14:30:00Z",
                "created_by": "analyst@company.com",
                "tags": ["mmm", "q4", "production"],
                "versions": [
                    {
                        "version": "2.1.0",
                        "created_at": "2024-06-01T14:30:00Z",
                        "stage": "production",
                        "metrics": {"mape": 0.085, "r2": 0.92},
                    },
                    {
                        "version": "2.0.0",
                        "created_at": "2024-05-15T10:00:00Z",
                        "stage": "archived",
                        "metrics": {"mape": 0.095, "r2": 0.89},
                    },
                ],
                "training_config": {
                    "dataset_id": "ds-001",
                    "target_column": "revenue",
                    "feature_columns": ["tv_spend", "digital_spend", "social_spend"],
                    "date_column": "date",
                },
                "summary": (
                    "Production MMM model for Q4 campaigns. "
                    "Trained on 52 weeks of data with 8.5% MAPE."
                ),
            }

        # Real database query
        from sqlalchemy import select
        from app.infrastructure.database.models.model import Model, ModelVersion

        async with self.db() as session:
            result = await session.execute(
                select(Model).where(
                    Model.id == UUID(model_id),
                    Model.organization_id == UUID(org_id),
                )
            )
            model = result.scalar_one_or_none()

            if not model:
                return None

            # Get versions
            versions_result = await session.execute(
                select(ModelVersion).where(ModelVersion.model_id == model.id)
            )
            versions = versions_result.scalars().all()

            return {
                "id": str(model.id),
                "name": model.name,
                "description": model.description or "",
                "model_type": model.model_type,
                "stage": model.stage,
                "current_version": model.version,
                "created_at": model.created_at.isoformat() if model.created_at else "",
                "updated_at": model.updated_at.isoformat() if model.updated_at else "",
                "versions": [
                    {
                        "version": v.version,
                        "created_at": v.created_at.isoformat() if v.created_at else "",
                        "stage": v.stage,
                        "metrics": v.metrics or {},
                    }
                    for v in versions
                ],
            }


class ModelPerformanceResource(BaseResource):
    """
    Model performance summary.

    URI Pattern: models://{org}/registry/{id}/performance
    Scope: models:read
    """

    resource_type = "model_performance"
    uri_template = "models://{org}/registry/{id}/performance"
    description = "Get model performance metrics with interpretations"
    required_scope = "models:read"

    async def fetch(
        self,
        uri: str,
        claims: Optional[MCPTokenClaims],
    ) -> Dict[str, Any]:
        """Fetch performance metrics."""
        params = self._parse_uri_params(uri)
        model_id = params.get("id", "")

        if not model_id:
            raise MCPError(
                code=MCPErrorCode.INVALID_PARAMS,
                message="Model ID is required",
            )

        metrics = await self._get_performance(model_id, claims.org_id if claims else "")

        if not metrics:
            raise resource_not_found("Model", model_id)

        # Format with insight formatter
        return format_model_performance(metrics, metrics.get("model_type", "mmm"))

    async def _get_performance(
        self,
        model_id: str,
        org_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get performance metrics from database."""
        if not self.db:
            # Mock data with comprehensive metrics
            return {
                "model_type": "pymc_mmm",
                "mape": 0.085,
                "rmse": 1234.56,
                "r2": 0.92,
                "mae": 980.0,
                "rhat_max": 1.02,
                "ess_min": 450,
                "training_time_seconds": 3600,
                "inference_time_ms": 50,
                "validation_split": 0.2,
                "cross_validation_folds": 5,
            }

        # Real database query
        from sqlalchemy import select
        from app.infrastructure.database.models.model import Model

        async with self.db() as session:
            result = await session.execute(
                select(Model).where(
                    Model.id == UUID(model_id),
                    Model.organization_id == UUID(org_id),
                )
            )
            model = result.scalar_one_or_none()

            if not model:
                return None

            return {
                "model_type": model.model_type,
                **(model.metrics or {}),
            }


class ModelParametersResource(BaseResource):
    """
    Model parameters with interpretation.

    URI Pattern: models://{org}/registry/{id}/parameters
    Scope: models:read
    """

    resource_type = "model_parameters"
    uri_template = "models://{org}/registry/{id}/parameters"
    description = "Get model parameters with business interpretations"
    required_scope = "models:read"

    async def fetch(
        self,
        uri: str,
        claims: Optional[MCPTokenClaims],
    ) -> Dict[str, Any]:
        """Fetch model parameters."""
        params = self._parse_uri_params(uri)
        model_id = params.get("id", "")

        if not model_id:
            raise MCPError(
                code=MCPErrorCode.INVALID_PARAMS,
                message="Model ID is required",
            )

        parameters = await self._get_parameters(
            model_id, claims.org_id if claims else ""
        )

        if not parameters:
            raise resource_not_found("Model", model_id)

        return self._format_parameters(parameters)

    async def _get_parameters(
        self,
        model_id: str,
        org_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get parameters from database."""
        if not self.db:
            # Mock MMM parameters
            return {
                "model_type": "pymc_mmm",
                "channel_effects": {
                    "tv_spend": {
                        "coefficient": 0.35,
                        "saturation": 0.7,
                        "adstock_decay": 0.4,
                        "ci_lower": 0.28,
                        "ci_upper": 0.42,
                    },
                    "digital_spend": {
                        "coefficient": 0.25,
                        "saturation": 0.85,
                        "adstock_decay": 0.2,
                        "ci_lower": 0.20,
                        "ci_upper": 0.30,
                    },
                    "social_spend": {
                        "coefficient": 0.15,
                        "saturation": 0.6,
                        "adstock_decay": 0.3,
                        "ci_lower": 0.10,
                        "ci_upper": 0.20,
                    },
                },
                "baseline": {
                    "intercept": 10000.0,
                    "trend": 0.02,
                    "seasonality_strength": 0.15,
                },
            }

        # Real database query
        from sqlalchemy import select
        from app.infrastructure.database.models.model import Model, ModelParameter

        async with self.db() as session:
            result = await session.execute(
                select(Model).where(
                    Model.id == UUID(model_id),
                    Model.organization_id == UUID(org_id),
                )
            )
            model = result.scalar_one_or_none()

            if not model:
                return None

            params_result = await session.execute(
                select(ModelParameter).where(ModelParameter.model_id == model.id)
            )
            params = params_result.scalars().all()

            return {
                "model_type": model.model_type,
                "parameters": {p.name: p.value for p in params},
            }

    def _format_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Format parameters with business interpretations."""
        model_type = params.get("model_type", "unknown")
        channel_effects = params.get("channel_effects", {})

        # Sort channels by coefficient (impact)
        sorted_channels = sorted(
            channel_effects.items(),
            key=lambda x: x[1].get("coefficient", 0),
            reverse=True,
        )

        formatted_channels = []
        for channel, effects in sorted_channels:
            coef = effects.get("coefficient", 0)
            sat = effects.get("saturation", 0)
            decay = effects.get("adstock_decay", 0)

            interpretation = self._interpret_channel(channel, coef, sat, decay)

            formatted_channels.append({
                "channel": channel,
                "coefficient": round(coef, 4),
                "saturation": round(sat, 3),
                "adstock_decay": round(decay, 3),
                "confidence_interval": [
                    round(effects.get("ci_lower", coef * 0.8), 4),
                    round(effects.get("ci_upper", coef * 1.2), 4),
                ],
                "interpretation": interpretation,
            })

        # Generate summary
        if formatted_channels:
            top_channel = formatted_channels[0]["channel"]
            summary = f"Analysis shows {top_channel} has the strongest impact on sales."
        else:
            summary = "No channel effects available."

        return {
            "model_type": model_type,
            "summary": summary,
            "channel_effects": formatted_channels,
            "baseline": params.get("baseline", {}),
            "insights": self._generate_parameter_insights(formatted_channels),
        }

    def _interpret_channel(
        self,
        channel: str,
        coefficient: float,
        saturation: float,
        decay: float,
    ) -> str:
        """Generate natural language interpretation."""
        channel_name = channel.replace("_", " ").title()

        # Coefficient interpretation
        if coefficient > 0.3:
            impact = "strong positive"
        elif coefficient > 0.15:
            impact = "moderate positive"
        elif coefficient > 0:
            impact = "mild positive"
        else:
            impact = "negligible"

        # Saturation interpretation
        if saturation > 0.8:
            sat_text = "near saturation point"
        elif saturation > 0.5:
            sat_text = "moderate saturation"
        else:
            sat_text = "room for increased spend"

        # Decay interpretation
        if decay > 0.5:
            decay_text = "long-lasting effects"
        elif decay > 0.25:
            decay_text = "moderate carryover"
        else:
            decay_text = "quick-decaying impact"

        return f"{channel_name} shows {impact} impact with {sat_text} and {decay_text}."

    def _generate_parameter_insights(
        self,
        channels: List[Dict[str, Any]],
    ) -> List[str]:
        """Generate actionable insights from parameters."""
        insights = []

        if not channels:
            return ["Insufficient data for insights"]

        # Top performer
        top = channels[0]
        insights.append(
            f"Highest ROI: {top['channel'].replace('_', ' ').title()} "
            f"with coefficient {top['coefficient']:.3f}"
        )

        # Saturation opportunities
        low_sat = [c for c in channels if c["saturation"] < 0.6]
        if low_sat:
            insights.append(
                f"Opportunity: {low_sat[0]['channel'].replace('_', ' ').title()} "
                f"has room for increased spend (saturation: {low_sat[0]['saturation']:.0%})"
            )

        # High saturation warnings
        high_sat = [c for c in channels if c["saturation"] > 0.85]
        if high_sat:
            insights.append(
                f"Warning: {high_sat[0]['channel'].replace('_', ' ').title()} "
                f"is near saturation ({high_sat[0]['saturation']:.0%})"
            )

        return insights
