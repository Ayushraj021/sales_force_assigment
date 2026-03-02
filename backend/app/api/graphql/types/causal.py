"""CausalGraph GraphQL types."""

from datetime import datetime
from typing import Optional
from uuid import UUID

import strawberry
from strawberry.scalars import JSON


@strawberry.type
class CausalGraphType:
    """Causal graph type."""

    id: UUID
    name: str
    description: Optional[str]

    # Algorithm used
    algorithm: str  # pc, notears, fci, etc.
    algorithm_params: Optional[JSON]

    # Graph structure
    nodes: JSON  # List of node names
    edges: JSON  # List of edge dicts {from, to, weight}
    adjacency_matrix: Optional[JSON]

    # Metadata
    n_nodes: Optional[int]
    n_edges: Optional[int]
    is_dag: Optional[bool]

    # Data source
    dataset_id: Optional[UUID]

    # Relationships
    organization_id: Optional[UUID]

    # Timestamps
    created_at: datetime


@strawberry.input
class CausalGraphFilterInput:
    """Input for filtering causal graphs."""

    algorithm: Optional[str] = None
    dataset_id: Optional[UUID] = None
    is_dag: Optional[bool] = None


@strawberry.type
class CausalEdgeType:
    """Causal edge type."""

    from_node: str
    to_node: str
    weight: Optional[float]
    edge_type: str  # directed, bidirected, undirected


@strawberry.type
class CausalPathType:
    """Causal path between two nodes."""

    from_node: str
    to_node: str
    path: list[str]
    total_effect: Optional[float]


@strawberry.type
class CausalEffectType:
    """Causal effect estimation result."""

    treatment: str
    outcome: str
    effect: float
    confidence_interval_lower: Optional[float]
    confidence_interval_upper: Optional[float]
    p_value: Optional[float]
    method: str
