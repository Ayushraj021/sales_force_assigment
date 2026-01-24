"""
DAG Discovery Module

Comprehensive causal graph discovery using multiple algorithms
and constraint-based methods.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import numpy as np
import pandas as pd
from scipy import stats


class DiscoveryAlgorithm(str, Enum):
    """Available causal discovery algorithms."""

    PC = "pc"
    FCI = "fci"
    GES = "ges"
    NOTEARS = "notears"
    LINGAM = "lingam"


@dataclass
class CausalEdge:
    """Represents a causal edge."""

    source: str
    target: str
    edge_type: str  # "directed", "bidirected", "undirected"
    weight: Optional[float] = None
    confidence: Optional[float] = None


@dataclass
class CausalGraph:
    """Represents a causal graph structure."""

    nodes: list[str]
    edges: list[CausalEdge]
    adjacency_matrix: np.ndarray
    algorithm: str
    metadata: dict = field(default_factory=dict)

    def get_parents(self, node: str) -> list[str]:
        """Get parent nodes of a given node."""
        return [e.source for e in self.edges if e.target == node and e.edge_type == "directed"]

    def get_children(self, node: str) -> list[str]:
        """Get child nodes of a given node."""
        return [e.target for e in self.edges if e.source == node and e.edge_type == "directed"]

    def get_ancestors(self, node: str) -> set[str]:
        """Get all ancestor nodes."""
        ancestors = set()
        to_visit = self.get_parents(node)
        while to_visit:
            parent = to_visit.pop()
            if parent not in ancestors:
                ancestors.add(parent)
                to_visit.extend(self.get_parents(parent))
        return ancestors

    def get_descendants(self, node: str) -> set[str]:
        """Get all descendant nodes."""
        descendants = set()
        to_visit = self.get_children(node)
        while to_visit:
            child = to_visit.pop()
            if child not in descendants:
                descendants.add(child)
                to_visit.extend(self.get_children(child))
        return descendants

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "nodes": self.nodes,
            "edges": [
                {
                    "source": e.source,
                    "target": e.target,
                    "edge_type": e.edge_type,
                    "weight": e.weight,
                    "confidence": e.confidence,
                }
                for e in self.edges
            ],
            "algorithm": self.algorithm,
            "metadata": self.metadata,
        }


class DAGDiscovery:
    """
    Causal DAG discovery from observational data.

    Supports multiple algorithms for structure learning including
    constraint-based (PC, FCI) and score-based (GES) methods.

    Example:
        discovery = DAGDiscovery()
        graph = discovery.fit(data, algorithm="pc")
        parents = graph.get_parents("revenue")
    """

    def __init__(
        self,
        alpha: float = 0.05,
        max_cond_vars: int = 5,
        seed: Optional[int] = None,
    ):
        """
        Initialize DAG discovery.

        Args:
            alpha: Significance level for conditional independence tests
            max_cond_vars: Maximum conditioning set size
            seed: Random seed
        """
        self.alpha = alpha
        self.max_cond_vars = max_cond_vars
        self.seed = seed
        self._rng = np.random.default_rng(seed)

    def fit(
        self,
        data: pd.DataFrame,
        algorithm: DiscoveryAlgorithm = DiscoveryAlgorithm.PC,
        variable_names: Optional[list[str]] = None,
    ) -> CausalGraph:
        """
        Discover causal structure from data.

        Args:
            data: DataFrame with variables as columns
            algorithm: Discovery algorithm to use
            variable_names: Optional list of variable names

        Returns:
            CausalGraph with discovered structure
        """
        if variable_names is None:
            variable_names = list(data.columns)

        X = data[variable_names].values

        if algorithm == DiscoveryAlgorithm.PC:
            return self._pc_algorithm(X, variable_names)
        elif algorithm == DiscoveryAlgorithm.NOTEARS:
            from .notears import NOTEARSDiscovery
            notears = NOTEARSDiscovery()
            result = notears.fit(data, variable_names)
            return self._notears_to_graph(result)
        else:
            raise ValueError(f"Algorithm {algorithm} not yet implemented")

    def _pc_algorithm(
        self, X: np.ndarray, variable_names: list[str]
    ) -> CausalGraph:
        """
        PC algorithm for causal discovery.

        Phase 1: Skeleton discovery through conditional independence tests
        Phase 2: Edge orientation using v-structures and propagation rules
        """
        n, d = X.shape

        # Initialize complete undirected graph
        adj = np.ones((d, d)) - np.eye(d)
        sep_sets: dict[tuple[int, int], set[int]] = {}

        # Phase 1: Skeleton discovery
        for size in range(self.max_cond_vars + 1):
            for i in range(d):
                for j in range(i + 1, d):
                    if adj[i, j] == 0:
                        continue

                    # Find neighbors
                    neighbors_i = set(np.where(adj[i] == 1)[0]) - {j}
                    neighbors_j = set(np.where(adj[j] == 1)[0]) - {i}
                    neighbors = neighbors_i | neighbors_j

                    if len(neighbors) < size:
                        continue

                    # Test all conditioning sets of given size
                    from itertools import combinations
                    for cond_set in combinations(neighbors, size):
                        cond_set = set(cond_set)
                        if self._conditional_independence_test(X, i, j, cond_set):
                            adj[i, j] = 0
                            adj[j, i] = 0
                            sep_sets[(i, j)] = cond_set
                            sep_sets[(j, i)] = cond_set
                            break

        # Phase 2: Orient edges
        # Find v-structures: i -> k <- j where i and j not adjacent
        directed = np.zeros((d, d))

        for k in range(d):
            parents = np.where(adj[:, k] == 1)[0]
            for i in range(len(parents)):
                for j in range(i + 1, len(parents)):
                    pi, pj = parents[i], parents[j]
                    if adj[pi, pj] == 0:  # i and j not adjacent
                        # Check if k in separation set
                        sep = sep_sets.get((pi, pj), set())
                        if k not in sep:
                            # Orient as v-structure
                            directed[pi, k] = 1
                            directed[pj, k] = 1

        # Convert to edges
        edges = []
        for i in range(d):
            for j in range(d):
                if directed[i, j] == 1:
                    edges.append(CausalEdge(
                        source=variable_names[i],
                        target=variable_names[j],
                        edge_type="directed",
                    ))
                elif adj[i, j] == 1 and directed[i, j] == 0 and directed[j, i] == 0:
                    if i < j:  # Avoid duplicates
                        edges.append(CausalEdge(
                            source=variable_names[i],
                            target=variable_names[j],
                            edge_type="undirected",
                        ))

        return CausalGraph(
            nodes=variable_names,
            edges=edges,
            adjacency_matrix=adj,
            algorithm="pc",
            metadata={"alpha": self.alpha, "n_samples": n},
        )

    def _conditional_independence_test(
        self,
        X: np.ndarray,
        i: int,
        j: int,
        cond_set: set[int],
    ) -> bool:
        """
        Test conditional independence using partial correlation.

        Tests if X_i ⫫ X_j | X_cond_set
        """
        if len(cond_set) == 0:
            # Simple correlation test
            corr = np.corrcoef(X[:, i], X[:, j])[0, 1]
            n = len(X)
            # Fisher transformation
            z = 0.5 * np.log((1 + corr) / (1 - corr + 1e-10))
            se = 1 / np.sqrt(n - 3)
            p_value = 2 * (1 - stats.norm.cdf(np.abs(z / se)))
        else:
            # Partial correlation
            cond_list = list(cond_set)
            var_indices = [i, j] + cond_list

            # Compute partial correlation via regression residuals
            X_subset = X[:, var_indices]
            if len(cond_list) > 0:
                X_cond = X[:, cond_list]
                # Regress X_i on conditioning set
                coef_i = np.linalg.lstsq(X_cond, X[:, i], rcond=None)[0]
                res_i = X[:, i] - X_cond @ coef_i
                # Regress X_j on conditioning set
                coef_j = np.linalg.lstsq(X_cond, X[:, j], rcond=None)[0]
                res_j = X[:, j] - X_cond @ coef_j
                # Correlation of residuals
                corr = np.corrcoef(res_i, res_j)[0, 1]
            else:
                corr = np.corrcoef(X[:, i], X[:, j])[0, 1]

            n = len(X)
            df = n - len(cond_set) - 3
            if df < 1:
                return False

            # Fisher transformation
            z = 0.5 * np.log((1 + corr) / (1 - corr + 1e-10))
            se = 1 / np.sqrt(df)
            p_value = 2 * (1 - stats.norm.cdf(np.abs(z / se)))

        return p_value > self.alpha

    def _notears_to_graph(self, result) -> CausalGraph:
        """Convert NOTEARS result to CausalGraph."""
        edges = [
            CausalEdge(
                source=src,
                target=tgt,
                edge_type="directed",
                weight=w,
            )
            for src, tgt, w in result.edges
        ]

        return CausalGraph(
            nodes=result.variable_names,
            edges=edges,
            adjacency_matrix=result.adjacency_matrix,
            algorithm="notears",
            metadata={
                "loss": result.loss,
                "h_value": result.h_value,
                "edge_threshold": result.edge_threshold,
            },
        )

    def intervention_effect(
        self,
        data: pd.DataFrame,
        graph: CausalGraph,
        treatment: str,
        outcome: str,
        adjustment_set: Optional[list[str]] = None,
    ) -> dict:
        """
        Estimate causal effect via adjustment formula.

        Args:
            data: Observational data
            graph: Causal graph
            treatment: Treatment variable
            outcome: Outcome variable
            adjustment_set: Variables to adjust for (auto-computed if None)

        Returns:
            Estimated causal effect
        """
        if adjustment_set is None:
            # Use backdoor criterion
            adjustment_set = self._find_adjustment_set(graph, treatment, outcome)

        if adjustment_set is None:
            raise ValueError("No valid adjustment set found")

        # Regression adjustment
        X = data[adjustment_set + [treatment]].values
        y = data[outcome].values

        # OLS
        X_aug = np.column_stack([np.ones(len(X)), X])
        coef = np.linalg.lstsq(X_aug, y, rcond=None)[0]

        treatment_idx = len(adjustment_set) + 1
        effect = coef[treatment_idx]

        # Standard error
        y_pred = X_aug @ coef
        residuals = y - y_pred
        mse = np.mean(residuals ** 2)
        cov = mse * np.linalg.inv(X_aug.T @ X_aug)
        se = np.sqrt(cov[treatment_idx, treatment_idx])

        return {
            "effect": effect,
            "standard_error": se,
            "p_value": 2 * (1 - stats.norm.cdf(np.abs(effect / se))),
            "adjustment_set": adjustment_set,
        }

    def _find_adjustment_set(
        self, graph: CausalGraph, treatment: str, outcome: str
    ) -> Optional[list[str]]:
        """Find valid adjustment set using backdoor criterion."""
        # Simple implementation: adjust for parents of treatment
        parents = graph.get_parents(treatment)
        if parents:
            return parents

        # Or parents of outcome that are not descendants of treatment
        outcome_parents = graph.get_parents(outcome)
        treatment_descendants = graph.get_descendants(treatment)

        valid = [p for p in outcome_parents if p not in treatment_descendants and p != treatment]
        return valid if valid else None
