"""GraphQL schema definition."""

from typing import Optional
from uuid import UUID

import strawberry
from strawberry.scalars import JSON

from app.api.graphql.context import get_context
from app.api.graphql.mutations.auth_mutations import AuthMutation
from app.api.graphql.mutations.inference_mutations import InferenceMutation
from app.api.graphql.queries.model_queries import ModelQuery
from app.api.graphql.queries.user_queries import UserQuery
from app.api.graphql.types.auth import UserType, OrganizationType
from app.api.graphql.types.data import DatasetType, ChannelType, MetricType
from app.api.graphql.types.model import ModelType, ExperimentType
from app.api.graphql.types.optimization import (
    BudgetScenarioType,
    OptimizationResultType,
    WhatIfAnalysisType,
)


@strawberry.type
class Query(UserQuery, ModelQuery):
    """Root query type combining all query resolvers."""

    @strawberry.field
    def version(self) -> str:
        """Get API version."""
        return "1.0.0"

    @strawberry.field
    def health(self) -> str:
        """Health check."""
        return "OK"


@strawberry.type
class Mutation(AuthMutation, InferenceMutation):
    """Root mutation type combining all mutation resolvers."""

    pass


# Create schema
schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
)
