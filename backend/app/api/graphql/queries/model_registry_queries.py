"""Model Registry queries."""

from typing import Optional
from uuid import UUID

import strawberry
import structlog
from strawberry.types import Info

from app.api.graphql.context import get_db_session, get_current_user_from_context
from app.api.graphql.types.model_registry import (
    RegistryModelVersionType,
    ModelRegistryEntryType,
    ModelComparisonType,
    ModelFilterInput,
    CompareModelsInput,
)
from app.core.exceptions import NotFoundError

logger = structlog.get_logger()


@strawberry.type
class ModelRegistryQuery:
    """Model Registry queries."""

    @strawberry.field
    async def registry_models(
        self,
        info: Info,
        filter: Optional[ModelFilterInput] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ModelRegistryEntryType]:
        """Get all models in the registry."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        logger.info(
            "Fetching registry models",
            user_id=str(current_user.id),
            org_id=str(current_user.organization_id),
        )

        return []

    @strawberry.field
    async def registry_model(
        self,
        info: Info,
        name: str,
    ) -> ModelRegistryEntryType:
        """Get a specific model from the registry."""
        db = await get_db_session(info)
        await get_current_user_from_context(info, db)

        raise NotFoundError("RegistryModel", name)

    @strawberry.field
    async def model_version(
        self,
        info: Info,
        name: str,
        version: str,
    ) -> RegistryModelVersionType:
        """Get a specific model version."""
        db = await get_db_session(info)
        await get_current_user_from_context(info, db)

        raise NotFoundError("ModelVersion", f"{name}:{version}")

    @strawberry.field
    async def model_versions(
        self,
        info: Info,
        name: str,
    ) -> list[RegistryModelVersionType]:
        """Get all versions of a model."""
        db = await get_db_session(info)
        await get_current_user_from_context(info, db)

        return []

    @strawberry.field
    async def production_models(
        self,
        info: Info,
    ) -> list[RegistryModelVersionType]:
        """Get all models in production stage."""
        db = await get_db_session(info)
        await get_current_user_from_context(info, db)

        return []

    @strawberry.field
    async def staging_models(
        self,
        info: Info,
    ) -> list[RegistryModelVersionType]:
        """Get all models in staging stage."""
        db = await get_db_session(info)
        await get_current_user_from_context(info, db)

        return []

    @strawberry.field
    async def compare_models(
        self,
        info: Info,
        input: CompareModelsInput,
    ) -> list[ModelComparisonType]:
        """Compare metrics across model versions."""
        db = await get_db_session(info)
        await get_current_user_from_context(info, db)

        return []

    @strawberry.field
    async def latest_version(
        self,
        info: Info,
        name: str,
    ) -> Optional[RegistryModelVersionType]:
        """Get the latest version of a model."""
        db = await get_db_session(info)
        await get_current_user_from_context(info, db)

        return None

    @strawberry.field
    async def model_stages(self) -> list[str]:
        """Get available model stages."""
        return ["development", "staging", "production", "archived"]

    @strawberry.field
    async def model_frameworks(self) -> list[str]:
        """Get supported ML frameworks."""
        return ["sklearn", "pytorch", "tensorflow", "xgboost", "lightgbm", "pymc", "unknown"]
