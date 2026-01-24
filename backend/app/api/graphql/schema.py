"""GraphQL schema definition."""

import strawberry

from app.api.graphql.context import DatabaseSessionExtension

# Mutations
from app.api.graphql.mutations.auth_mutations import AuthMutation
from app.api.graphql.mutations.dataset_mutations import DatasetMutation
from app.api.graphql.mutations.inference_mutations import InferenceMutation
from app.api.graphql.mutations.model_mutations import ModelMutation
from app.api.graphql.mutations.user_mutations import UserMutation
from app.api.graphql.mutations.organization_mutations import OrganizationMutation
from app.api.graphql.mutations.connector_mutations import ConnectorMutation
from app.api.graphql.mutations.forecast_mutations import ForecastMutation
from app.api.graphql.mutations.optimization_mutations import OptimizationMutation
from app.api.graphql.mutations.experiment_mutations import ExperimentMutation
from app.api.graphql.mutations.report_mutations import ReportMutation
from app.api.graphql.mutations.api_key_mutations import APIKeyMutation
from app.api.graphql.mutations.role_mutations import RoleMutation
# Phase 4 Mutations
from app.api.graphql.mutations.branding_mutations import BrandingMutation
from app.api.graphql.mutations.geo_experiment_mutations import GeoExperimentMutation
from app.api.graphql.mutations.attribution_mutations import AttributionMutation
from app.api.graphql.mutations.dashboard_mutations import DashboardMutation
# Phase 5 Mutations
from app.api.graphql.mutations.channel_mutations import ChannelMutation
from app.api.graphql.mutations.consent_mutations import ConsentMutation
# Phase 6 Mutations
from app.api.graphql.mutations.monitoring_mutations import MonitoringMutation
from app.api.graphql.mutations.etl_mutations import ETLMutation
from app.api.graphql.mutations.model_registry_mutations import ModelRegistryMutation
from app.api.graphql.mutations.scheduler_mutations import SchedulerMutation
# Data Preprocessing Mutations
from app.api.graphql.mutations.data_preprocessing_mutations import DataPreprocessingMutation

# Queries
from app.api.graphql.queries.dataset_queries import DatasetQuery
from app.api.graphql.queries.model_queries import ModelQuery
from app.api.graphql.queries.user_queries import UserQuery
from app.api.graphql.queries.connector_queries import ConnectorQuery
from app.api.graphql.queries.forecast_queries import ForecastQuery
from app.api.graphql.queries.optimization_queries import OptimizationQuery
from app.api.graphql.queries.report_queries import ReportQuery
from app.api.graphql.queries.api_key_queries import APIKeyQuery
from app.api.graphql.queries.role_queries import RoleQuery
# Phase 4 Queries
from app.api.graphql.queries.audit_queries import AuditQuery
from app.api.graphql.queries.branding_queries import BrandingQuery
from app.api.graphql.queries.geo_experiment_queries import GeoExperimentQuery
from app.api.graphql.queries.attribution_queries import AttributionQuery
from app.api.graphql.queries.dashboard_queries import DashboardQuery
# Phase 5 Queries
from app.api.graphql.queries.channel_queries import ChannelQuery
from app.api.graphql.queries.data_version_queries import DataVersionQuery
from app.api.graphql.queries.consent_queries import ConsentQuery
from app.api.graphql.queries.causal_queries import CausalQuery
# Phase 6 Queries
from app.api.graphql.queries.monitoring_queries import MonitoringQuery
from app.api.graphql.queries.etl_queries import ETLQuery
from app.api.graphql.queries.model_registry_queries import ModelRegistryQuery
from app.api.graphql.queries.scheduler_queries import SchedulerQuery
# Data Preprocessing Queries
from app.api.graphql.queries.data_preprocessing_queries import DataPreprocessingQuery


@strawberry.type
class Query(
    UserQuery,
    ModelQuery,
    DatasetQuery,
    ConnectorQuery,
    ForecastQuery,
    OptimizationQuery,
    ReportQuery,
    APIKeyQuery,
    RoleQuery,
    # Phase 4 Queries
    AuditQuery,
    BrandingQuery,
    GeoExperimentQuery,
    AttributionQuery,
    DashboardQuery,
    # Phase 5 Queries
    ChannelQuery,
    DataVersionQuery,
    ConsentQuery,
    CausalQuery,
    # Phase 6 Queries
    MonitoringQuery,
    ETLQuery,
    ModelRegistryQuery,
    SchedulerQuery,
    # Data Preprocessing Queries
    DataPreprocessingQuery,
):
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
class Mutation(
    AuthMutation,
    InferenceMutation,
    DatasetMutation,
    ModelMutation,
    UserMutation,
    OrganizationMutation,
    ConnectorMutation,
    ForecastMutation,
    OptimizationMutation,
    ExperimentMutation,
    ReportMutation,
    APIKeyMutation,
    RoleMutation,
    # Phase 4 Mutations
    BrandingMutation,
    GeoExperimentMutation,
    AttributionMutation,
    DashboardMutation,
    # Phase 5 Mutations
    ChannelMutation,
    ConsentMutation,
    # Phase 6 Mutations
    MonitoringMutation,
    ETLMutation,
    ModelRegistryMutation,
    SchedulerMutation,
    # Data Preprocessing Mutations
    DataPreprocessingMutation,
):
    """Root mutation type combining all mutation resolvers."""

    pass


# Create schema with database session extension
schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    extensions=[DatabaseSessionExtension],
)
