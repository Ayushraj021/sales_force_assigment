"""
NOTEARS Algorithm for Causal Discovery

Implements the NOTEARS (Non-combinatorial Optimization via Trace Exponential
and Augmented lagRangian for Structure learning) algorithm for learning
DAGs from observational data.

Reference:
Zheng et al. (2018): DAGs with NO TEARS: Continuous Optimization for Structure Learning
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
from scipy import linalg
from scipy.optimize import minimize


@dataclass
class NOTEARSResult:
    """Result from NOTEARS causal discovery."""

    # Learned adjacency matrix
    adjacency_matrix: np.ndarray

    # Variable names
    variable_names: list[str]

    # Edge list with weights
    edges: list[tuple[str, str, float]]

    # Optimization metrics
    loss: float
    h_value: float  # Acyclicity constraint value
    n_iterations: int

    # Thresholds used
    edge_threshold: float


class NOTEARSDiscovery:
    """
    NOTEARS algorithm for structure learning.

    Learns a DAG structure from data using continuous optimization
    with an acyclicity constraint based on matrix exponential.

    Example:
        notears = NOTEARSDiscovery()
        result = notears.fit(data)
        print(result.edges)
    """

    def __init__(
        self,
        lambda1: float = 0.1,
        loss_type: str = "l2",
        max_iter: int = 100,
        h_tol: float = 1e-8,
        rho_max: float = 1e16,
        w_threshold: float = 0.3,
    ):
        """
        Initialize NOTEARS.

        Args:
            lambda1: L1 penalty parameter
            loss_type: Loss function ("l2" or "logistic")
            max_iter: Maximum iterations
            h_tol: Tolerance for acyclicity constraint
            rho_max: Maximum penalty parameter
            w_threshold: Threshold for edge weights
        """
        self.lambda1 = lambda1
        self.loss_type = loss_type
        self.max_iter = max_iter
        self.h_tol = h_tol
        self.rho_max = rho_max
        self.w_threshold = w_threshold

    def fit(
        self,
        data: pd.DataFrame,
        variable_names: Optional[list[str]] = None,
    ) -> NOTEARSResult:
        """
        Learn DAG structure from data.

        Args:
            data: DataFrame with variables as columns
            variable_names: Optional list of variable names

        Returns:
            NOTEARSResult with learned structure
        """
        if variable_names is None:
            variable_names = list(data.columns)

        X = data[variable_names].values
        X = (X - X.mean(axis=0)) / (X.std(axis=0) + 1e-8)  # Standardize

        n, d = X.shape

        # Run optimization
        W, loss, h_val, n_iter = self._notears_linear(X)

        # Threshold small weights
        W_thresh = W.copy()
        W_thresh[np.abs(W_thresh) < self.w_threshold] = 0

        # Extract edges
        edges = []
        for i in range(d):
            for j in range(d):
                if W_thresh[i, j] != 0:
                    edges.append((variable_names[j], variable_names[i], W_thresh[i, j]))

        return NOTEARSResult(
            adjacency_matrix=W_thresh,
            variable_names=variable_names,
            edges=edges,
            loss=loss,
            h_value=h_val,
            n_iterations=n_iter,
            edge_threshold=self.w_threshold,
        )

    def _notears_linear(
        self, X: np.ndarray
    ) -> tuple[np.ndarray, float, float, int]:
        """
        Solve NOTEARS for linear Gaussian model.

        min_W 0.5/n * ||X - XW||_F^2 + lambda1*||W||_1
        s.t. h(W) = tr(e^{W*W}) - d = 0
        """
        n, d = X.shape

        def _loss(W):
            """Calculate loss."""
            W = W.reshape((d, d))
            M = X @ W
            R = X - M
            loss = 0.5 / n * (R ** 2).sum()
            return loss

        def _h(W):
            """Acyclicity constraint using matrix exponential."""
            W = W.reshape((d, d))
            E = linalg.expm(W * W)
            h = np.trace(E) - d
            return h

        def _adj(W, rho, alpha):
            """Augmented Lagrangian."""
            W = W.reshape((d, d))
            loss = _loss(W.flatten())
            h = _h(W.flatten())
            obj = loss + 0.5 * rho * h ** 2 + alpha * h + self.lambda1 * np.abs(W).sum()
            return obj

        def _grad(W):
            """Gradient of loss + h."""
            W = W.reshape((d, d))
            M = X @ W
            R = X - M
            loss_grad = -1.0 / n * X.T @ R

            E = linalg.expm(W * W)
            h_grad = E.T * W * 2

            return loss_grad.flatten(), h_grad.flatten()

        # Initialize
        W = np.zeros(d * d)
        rho = 1.0
        alpha = 0.0
        h = np.inf
        n_iter = 0

        for _ in range(self.max_iter):
            # Inner optimization
            while rho < self.rho_max:
                def objective(W):
                    return _adj(W, rho, alpha)

                result = minimize(
                    objective,
                    W,
                    method="L-BFGS-B",
                    options={"maxiter": 1000},
                )
                W_new = result.x
                h_new = _h(W_new)

                if h_new > 0.25 * h:
                    rho *= 10
                else:
                    break

            W = W_new
            h = h_new
            alpha += rho * h
            n_iter += 1

            if h <= self.h_tol:
                break

        W = W.reshape((d, d))
        loss = _loss(W.flatten())

        return W, loss, h, n_iter

    def get_causal_order(self, result: NOTEARSResult) -> list[str]:
        """
        Get topological ordering of variables from learned DAG.

        Args:
            result: NOTEARSResult from fit()

        Returns:
            List of variables in causal order
        """
        W = result.adjacency_matrix
        d = W.shape[0]
        names = result.variable_names

        # Calculate in-degrees
        in_degrees = np.sum(np.abs(W) > 0, axis=0)

        order = []
        remaining = set(range(d))

        while remaining:
            # Find nodes with no incoming edges from remaining
            for i in remaining:
                has_incoming = False
                for j in remaining:
                    if j != i and W[j, i] != 0:
                        has_incoming = True
                        break
                if not has_incoming:
                    order.append(names[i])
                    remaining.remove(i)
                    break
            else:
                # Cycle detected, break ties by in-degree
                min_idx = min(remaining, key=lambda x: in_degrees[x])
                order.append(names[min_idx])
                remaining.remove(min_idx)

        return order

    def to_networkx(self, result: NOTEARSResult):
        """
        Convert result to NetworkX DiGraph.

        Args:
            result: NOTEARSResult from fit()

        Returns:
            NetworkX DiGraph
        """
        try:
            import networkx as nx
        except ImportError:
            raise ImportError("networkx required for this method")

        G = nx.DiGraph()
        G.add_nodes_from(result.variable_names)

        for source, target, weight in result.edges:
            G.add_edge(source, target, weight=weight)

        return G
