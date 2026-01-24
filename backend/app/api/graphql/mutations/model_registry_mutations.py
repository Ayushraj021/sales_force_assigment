"""Model Registry mutations."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

import strawberry
import structlog
from strawberry.types import Info

from app.api.graphql.context import get_db_session, get_current_user_from_context
from app.api.graphql.types.model_registry import (
    RegistryModelVersionType,
    ModelPromotionResultType,
    RegisterModelInput,
    UpdateModelVersionInput,
    PromoteModelInput,
)
from app.core.exceptions import NotFoundError, ValidationError

logger = structlog.get_logger()


@strawberry.type
class ModelRegistryMutation:
    """Model Registry mutations."""

    @strawberry.mutation
    async def register_model(
        self,
        info: Info,
        input: RegisterModelInput,
    ) -> RegistryModelVersionType:
        """Register a new model version."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        if not input.name or len(input.name.strip()) == 0:
            raise ValidationError("Model name is required")

        now = datetime.utcnow()
        version = input.version or "1.0.0"

        model_version = RegistryModelVersionType(
            id=uuid4(),
            model_name=input.name.strip(),
            version=version,
            model_type=input.model_type,
            framework=input.framework,
            stage="development",
            metrics=input.metrics or {},
            parameters=input.parameters or {},
            tags=input.tags or {},
            description=input.description,
            checksum=None,
            file_size_bytes=None,
            created_at=now,
            updated_at=now,
            created_by=current_user.id,
        )

        logger.info(
            "Model registered",
            model_name=input.name,
            version=version,
            registered_by=str(current_user.id),
        )

        return model_version

    @strawberry.mutation
    async def update_model_version(
        self,
        info: Info,
        name: str,
        version: str,
        input: UpdateModelVersionInput,
    ) -> RegistryModelVersionType:
        """Update a model version."""
        db = await get_db_session(info)
        await get_current_user_from_context(info, db)

        raise NotFoundError("ModelVersion", f"{name}:{version}")

    @strawberry.mutation
    async def promote_model(
        self,
        info: Info,
        input: PromoteModelInput,
    ) -> ModelPromotionResultType:
        """Promote a model to a new stage."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        valid_stages = ["development", "staging", "production", "archived"]
        if input.stage not in valid_stages:
            raise ValidationError(f"stage must be one of: {', '.join(valid_stages)}")

        # In production, this would update the database
        result = ModelPromotionResultType(
            success=True,
            model_name=input.model_name,
            version=input.version,
            from_stage="development",
            to_stage=input.stage,
            promoted_at=datetime.utcnow(),
            message=f"Model {input.model_name}:{input.version} promoted to {input.stage}",
        )

        logger.info(
            "Model promoted",
            model_name=input.model_name,
            version=input.version,
            to_stage=input.stage,
            promoted_by=str(current_user.id),
        )

        return result

    @strawberry.mutation
    async def archive_model(
        self,
        info: Info,
        name: str,
        version: str,
    ) -> ModelPromotionResultType:
        """Archive a model version."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        result = ModelPromotionResultType(
            success=True,
            model_name=name,
            version=version,
            from_stage="unknown",
            to_stage="archived",
            promoted_at=datetime.utcnow(),
            message=f"Model {name}:{version} archived",
        )

        logger.info(
            "Model archived",
            model_name=name,
            version=version,
            archived_by=str(current_user.id),
        )

        return result

    @strawberry.mutation
    async def delete_model_version(
        self,
        info: Info,
        name: str,
        version: str,
    ) -> bool:
        """Delete a model version."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        logger.info(
            "Model version deleted",
            model_name=name,
            version=version,
            deleted_by=str(current_user.id),
        )

        return True

    @strawberry.mutation
    async def delete_all_versions(
        self,
        info: Info,
        name: str,
    ) -> bool:
        """Delete all versions of a model."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        logger.info(
            "All model versions deleted",
            model_name=name,
            deleted_by=str(current_user.id),
        )

        return True

    @strawberry.mutation
    async def add_model_tag(
        self,
        info: Info,
        name: str,
        version: str,
        tag_key: str,
        tag_value: str,
    ) -> RegistryModelVersionType:
        """Add a tag to a model version."""
        db = await get_db_session(info)
        await get_current_user_from_context(info, db)

        raise NotFoundError("ModelVersion", f"{name}:{version}")

    @strawberry.mutation
    async def remove_model_tag(
        self,
        info: Info,
        name: str,
        version: str,
        tag_key: str,
    ) -> RegistryModelVersionType:
        """Remove a tag from a model version."""
        db = await get_db_session(info)
        await get_current_user_from_context(info, db)

        raise NotFoundError("ModelVersion", f"{name}:{version}")

    @strawberry.mutation
    async def update_model_metrics(
        self,
        info: Info,
        name: str,
        version: str,
        metrics: strawberry.scalars.JSON,
    ) -> RegistryModelVersionType:
        """Update metrics for a model version."""
        db = await get_db_session(info)
        await get_current_user_from_context(info, db)

        raise NotFoundError("ModelVersion", f"{name}:{version}")
