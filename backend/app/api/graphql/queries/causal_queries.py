"""CausalGraph queries."""

from typing import Optional
from uuid import UUID

import strawberry
import structlog
from sqlalchemy import select
from strawberry.types import Info

from app.api.graphql.context import get_db_session, get_current_user_from_context
from app.api.graphql.types.causal import (
    CausalEdgeType,
    CausalGraphFilterInput,
    CausalGraphType,
    CausalPathType,
)
from app.core.exceptions import NotFoundError
from app.infrastructure.database.models.experiments import CausalGraph

logger = structlog.get_logger()


def causal_graph_to_graphql(graph: CausalGraph) -> CausalGraphType:
    """Convert causal graph to GraphQL type."""
    return CausalGraphType(
        id=graph.id,
        name=graph.name,
        description=graph.description,
        algorithm=graph.algorithm,
        algorithm_params=graph.algorithm_params,
        nodes=graph.nodes,
        edges=graph.edges,
        adjacency_matrix=graph.adjacency_matrix,
        n_nodes=graph.n_nodes,
        n_edges=graph.n_edges,
        is_dag=graph.is_dag,
        dataset_id=graph.dataset_id,
        organization_id=graph.organization_id,
        created_at=graph.created_at,
    )


@strawberry.type
class CausalQuery:
    """CausalGraph queries."""

    @strawberry.field
    async def causal_graphs(
        self,
        info: Info,
        filter: Optional[CausalGraphFilterInput] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CausalGraphType]:
        """Get causal graphs for the organization."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        query = select(CausalGraph).where(
            CausalGraph.organization_id == current_user.organization_id
        )

        # Apply filters
        if filter:
            if filter.algorithm:
                query = query.where(CausalGraph.algorithm == filter.algorithm)
            if filter.dataset_id:
                query = query.where(CausalGraph.dataset_id == filter.dataset_id)
            if filter.is_dag is not None:
                query = query.where(CausalGraph.is_dag == filter.is_dag)

        # Order by creation date descending and paginate
        query = query.order_by(CausalGraph.created_at.desc()).offset(offset).limit(limit)

        result = await db.execute(query)
        graphs = result.scalars().all()

        return [causal_graph_to_graphql(g) for g in graphs]

    @strawberry.field
    async def causal_graph(
        self,
        info: Info,
        graph_id: UUID,
    ) -> CausalGraphType:
        """Get a specific causal graph by ID."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        result = await db.execute(
            select(CausalGraph).where(
                CausalGraph.id == graph_id,
                CausalGraph.organization_id == current_user.organization_id,
            )
        )
        graph = result.scalar_one_or_none()

        if not graph:
            raise NotFoundError("Causal graph", str(graph_id))

        return causal_graph_to_graphql(graph)

    @strawberry.field
    async def causal_graph_edges(
        self,
        info: Info,
        graph_id: UUID,
    ) -> list[CausalEdgeType]:
        """Get edges from a causal graph."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        result = await db.execute(
            select(CausalGraph).where(
                CausalGraph.id == graph_id,
                CausalGraph.organization_id == current_user.organization_id,
            )
        )
        graph = result.scalar_one_or_none()

        if not graph:
            raise NotFoundError("Causal graph", str(graph_id))

        edges = []
        if graph.edges:
            for edge in graph.edges:
                edges.append(CausalEdgeType(
                    from_node=edge.get("from", edge.get("source", "")),
                    to_node=edge.get("to", edge.get("target", "")),
                    weight=edge.get("weight"),
                    edge_type=edge.get("type", "directed"),
                ))

        return edges

    @strawberry.field
    async def causal_graph_nodes(
        self,
        info: Info,
        graph_id: UUID,
    ) -> list[str]:
        """Get nodes from a causal graph."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        result = await db.execute(
            select(CausalGraph).where(
                CausalGraph.id == graph_id,
                CausalGraph.organization_id == current_user.organization_id,
            )
        )
        graph = result.scalar_one_or_none()

        if not graph:
            raise NotFoundError("Causal graph", str(graph_id))

        return graph.nodes or []

    @strawberry.field
    async def find_causal_paths(
        self,
        info: Info,
        graph_id: UUID,
        from_node: str,
        to_node: str,
    ) -> list[CausalPathType]:
        """Find all causal paths between two nodes in a graph."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        result = await db.execute(
            select(CausalGraph).where(
                CausalGraph.id == graph_id,
                CausalGraph.organization_id == current_user.organization_id,
            )
        )
        graph = result.scalar_one_or_none()

        if not graph:
            raise NotFoundError("Causal graph", str(graph_id))

        # Build adjacency list
        adj = {}
        if graph.nodes:
            for node in graph.nodes:
                adj[node] = []
        if graph.edges:
            for edge in graph.edges:
                source = edge.get("from", edge.get("source", ""))
                target = edge.get("to", edge.get("target", ""))
                if source in adj:
                    adj[source].append(target)

        # Find all paths using DFS
        paths = []

        def dfs(current: str, target: str, path: list[str], visited: set):
            if current == target:
                paths.append(path.copy())
                return
            if current in visited:
                return

            visited.add(current)
            for neighbor in adj.get(current, []):
                dfs(neighbor, target, path + [neighbor], visited)
            visited.remove(current)

        if from_node in adj:
            dfs(from_node, to_node, [from_node], set())

        return [
            CausalPathType(
                from_node=from_node,
                to_node=to_node,
                path=p,
                total_effect=None,  # Would need actual effect estimation
            )
            for p in paths
        ]

    @strawberry.field
    async def node_parents(
        self,
        info: Info,
        graph_id: UUID,
        node: str,
    ) -> list[str]:
        """Get parent nodes (direct causes) of a node."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        result = await db.execute(
            select(CausalGraph).where(
                CausalGraph.id == graph_id,
                CausalGraph.organization_id == current_user.organization_id,
            )
        )
        graph = result.scalar_one_or_none()

        if not graph:
            raise NotFoundError("Causal graph", str(graph_id))

        parents = []
        if graph.edges:
            for edge in graph.edges:
                target = edge.get("to", edge.get("target", ""))
                if target == node:
                    source = edge.get("from", edge.get("source", ""))
                    parents.append(source)

        return parents

    @strawberry.field
    async def node_children(
        self,
        info: Info,
        graph_id: UUID,
        node: str,
    ) -> list[str]:
        """Get child nodes (direct effects) of a node."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        result = await db.execute(
            select(CausalGraph).where(
                CausalGraph.id == graph_id,
                CausalGraph.organization_id == current_user.organization_id,
            )
        )
        graph = result.scalar_one_or_none()

        if not graph:
            raise NotFoundError("Causal graph", str(graph_id))

        children = []
        if graph.edges:
            for edge in graph.edges:
                source = edge.get("from", edge.get("source", ""))
                if source == node:
                    target = edge.get("to", edge.get("target", ""))
                    children.append(target)

        return children

    @strawberry.field
    async def causal_algorithms(self) -> list[str]:
        """Get list of available causal discovery algorithms."""
        return [
            "pc",
            "fci",
            "notears",
            "golem",
            "dagma",
            "lingam",
            "granger",
        ]

    @strawberry.field
    async def causal_graphs_by_dataset(
        self,
        info: Info,
        dataset_id: UUID,
    ) -> list[CausalGraphType]:
        """Get all causal graphs for a specific dataset."""
        db = await get_db_session(info)
        current_user = await get_current_user_from_context(info, db)

        result = await db.execute(
            select(CausalGraph).where(
                CausalGraph.dataset_id == dataset_id,
                CausalGraph.organization_id == current_user.organization_id,
            ).order_by(CausalGraph.created_at.desc())
        )
        graphs = result.scalars().all()

        return [causal_graph_to_graphql(g) for g in graphs]
