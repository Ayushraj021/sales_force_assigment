"""
SHAP Explainer

Shapley Additive Explanations for model interpretability.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union
from enum import Enum
import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class ExplainerType(str, Enum):
    """Types of SHAP explainers."""
    TREE = "tree"  # For tree-based models
    LINEAR = "linear"  # For linear models
    KERNEL = "kernel"  # Model-agnostic
    DEEP = "deep"  # For neural networks
    GRADIENT = "gradient"  # Gradient-based for neural nets
    PARTITION = "partition"  # Hierarchical


@dataclass
class SHAPExplanation:
    """SHAP explanation results."""
    shap_values: np.ndarray
    base_value: float
    feature_names: List[str]
    feature_importance: Dict[str, float]
    interaction_values: Optional[np.ndarray] = None

    def get_top_features(self, n: int = 10) -> List[tuple]:
        """Get top N important features."""
        sorted_features = sorted(
            self.feature_importance.items(),
            key=lambda x: abs(x[1]),
            reverse=True
        )
        return sorted_features[:n]

    def to_dataframe(self) -> pd.DataFrame:
        """Convert SHAP values to DataFrame."""
        return pd.DataFrame(
            self.shap_values,
            columns=self.feature_names
        )

    def get_feature_summary(self) -> pd.DataFrame:
        """Get feature importance summary."""
        mean_abs_shap = np.abs(self.shap_values).mean(axis=0)
        std_shap = self.shap_values.std(axis=0)

        return pd.DataFrame({
            "feature": self.feature_names,
            "mean_abs_shap": mean_abs_shap,
            "std_shap": std_shap,
            "importance": [self.feature_importance.get(f, 0) for f in self.feature_names],
        }).sort_values("mean_abs_shap", ascending=False)


@dataclass
class SHAPConfig:
    """Configuration for SHAP explainer."""
    explainer_type: ExplainerType = ExplainerType.KERNEL
    n_samples: int = 100  # Background samples for kernel
    max_evals: int = 500  # Max evaluations
    check_additivity: bool = False
    approximate: bool = True
    feature_perturbation: str = "interventional"


class SHAPExplainer:
    """
    SHAP (SHapley Additive exPlanations) Explainer.

    Features:
    - Multiple explainer types (Tree, Linear, Kernel, Deep)
    - Global and local explanations
    - Feature interactions
    - Visualization support

    Example:
        explainer = SHAPExplainer(model)
        explanation = explainer.explain(X_test)

        print("Top features:", explanation.get_top_features())
        explainer.plot_summary(explanation)
    """

    def __init__(
        self,
        model: Any,
        config: Optional[SHAPConfig] = None,
        feature_names: Optional[List[str]] = None,
    ):
        self.model = model
        self.config = config or SHAPConfig()
        self.feature_names = feature_names
        self.explainer = None
        self._background_data = None

    def fit(self, X: np.ndarray) -> "SHAPExplainer":
        """
        Fit the explainer with background data.

        Args:
            X: Background data for computing expectations

        Returns:
            self
        """
        self._background_data = X

        if self.feature_names is None:
            self.feature_names = [f"feature_{i}" for i in range(X.shape[1])]

        self.explainer = self._create_explainer(X)
        return self

    def explain(
        self,
        X: np.ndarray,
        return_interactions: bool = False,
    ) -> SHAPExplanation:
        """
        Generate SHAP explanations.

        Args:
            X: Data to explain
            return_interactions: Whether to compute interaction values

        Returns:
            SHAPExplanation with SHAP values and feature importance
        """
        if self.explainer is None:
            raise ValueError("Explainer not fitted. Call fit() first.")

        # Compute SHAP values
        shap_values = self._compute_shap_values(X)

        # Get base value
        base_value = self._get_base_value()

        # Compute feature importance
        feature_importance = self._compute_importance(shap_values)

        # Compute interactions if requested
        interaction_values = None
        if return_interactions and self.config.explainer_type == ExplainerType.TREE:
            interaction_values = self._compute_interactions(X)

        return SHAPExplanation(
            shap_values=shap_values,
            base_value=base_value,
            feature_names=self.feature_names,
            feature_importance=feature_importance,
            interaction_values=interaction_values,
        )

    def explain_instance(
        self,
        x: np.ndarray,
    ) -> Dict[str, float]:
        """
        Explain a single instance.

        Args:
            x: Single data point (1, n_features)

        Returns:
            Dict mapping feature names to SHAP values
        """
        if self.explainer is None:
            raise ValueError("Explainer not fitted")

        x = x.reshape(1, -1)
        shap_values = self._compute_shap_values(x)

        return dict(zip(self.feature_names, shap_values.flatten()))

    def _create_explainer(self, X: np.ndarray):
        """Create SHAP explainer based on model type."""
        try:
            import shap
        except ImportError:
            logger.warning("SHAP not available, using fallback")
            return None

        # Select background samples
        if len(X) > self.config.n_samples:
            indices = np.random.choice(len(X), self.config.n_samples, replace=False)
            background = X[indices]
        else:
            background = X

        if self.config.explainer_type == ExplainerType.TREE:
            try:
                return shap.TreeExplainer(self.model, background)
            except Exception:
                logger.warning("TreeExplainer failed, falling back to Kernel")
                return shap.KernelExplainer(self.model.predict, background)

        elif self.config.explainer_type == ExplainerType.LINEAR:
            try:
                return shap.LinearExplainer(self.model, background)
            except Exception:
                return shap.KernelExplainer(self.model.predict, background)

        elif self.config.explainer_type == ExplainerType.DEEP:
            try:
                return shap.DeepExplainer(self.model, background)
            except Exception:
                return shap.KernelExplainer(
                    lambda x: self.model.predict(x),
                    background
                )

        elif self.config.explainer_type == ExplainerType.GRADIENT:
            try:
                return shap.GradientExplainer(self.model, background)
            except Exception:
                return shap.KernelExplainer(
                    lambda x: self.model.predict(x),
                    background
                )

        else:  # Kernel (default)
            predict_fn = getattr(self.model, 'predict', self.model)
            return shap.KernelExplainer(predict_fn, background)

    def _compute_shap_values(self, X: np.ndarray) -> np.ndarray:
        """Compute SHAP values."""
        if self.explainer is None:
            # Fallback: use permutation importance
            return self._fallback_importance(X)

        try:
            import shap
            shap_values = self.explainer.shap_values(X)

            # Handle multi-output
            if isinstance(shap_values, list):
                shap_values = shap_values[0]

            return np.array(shap_values)

        except Exception as e:
            logger.warning(f"SHAP computation failed: {e}")
            return self._fallback_importance(X)

    def _fallback_importance(self, X: np.ndarray) -> np.ndarray:
        """Fallback importance using permutation."""
        n_samples, n_features = X.shape
        importance = np.zeros((n_samples, n_features))

        try:
            base_pred = self.model.predict(X)

            for j in range(n_features):
                X_permuted = X.copy()
                X_permuted[:, j] = np.random.permutation(X_permuted[:, j])
                perm_pred = self.model.predict(X_permuted)
                importance[:, j] = base_pred - perm_pred

        except Exception:
            pass

        return importance

    def _get_base_value(self) -> float:
        """Get base value (expected value)."""
        if self.explainer is None:
            return 0.0

        try:
            expected = self.explainer.expected_value
            if isinstance(expected, np.ndarray):
                return float(expected[0])
            return float(expected)
        except Exception:
            return 0.0

    def _compute_importance(
        self,
        shap_values: np.ndarray,
    ) -> Dict[str, float]:
        """Compute feature importance from SHAP values."""
        mean_abs_shap = np.abs(shap_values).mean(axis=0)

        return {
            name: float(imp)
            for name, imp in zip(self.feature_names, mean_abs_shap)
        }

    def _compute_interactions(
        self,
        X: np.ndarray,
    ) -> Optional[np.ndarray]:
        """Compute SHAP interaction values."""
        if self.explainer is None:
            return None

        try:
            return self.explainer.shap_interaction_values(X)
        except Exception:
            return None

    def plot_summary(
        self,
        explanation: SHAPExplanation,
        max_display: int = 20,
    ):
        """Create summary plot of SHAP values."""
        try:
            import shap
            import matplotlib.pyplot as plt

            shap.summary_plot(
                explanation.shap_values,
                feature_names=explanation.feature_names,
                max_display=max_display,
                show=False,
            )
            return plt.gcf()
        except Exception as e:
            logger.warning(f"Plot failed: {e}")
            return None

    def plot_waterfall(
        self,
        explanation: SHAPExplanation,
        instance_idx: int = 0,
    ):
        """Create waterfall plot for single instance."""
        try:
            import shap
            import matplotlib.pyplot as plt

            shap.waterfall_plot(
                shap.Explanation(
                    values=explanation.shap_values[instance_idx],
                    base_values=explanation.base_value,
                    feature_names=explanation.feature_names,
                ),
                show=False,
            )
            return plt.gcf()
        except Exception as e:
            logger.warning(f"Plot failed: {e}")
            return None

    def plot_force(
        self,
        explanation: SHAPExplanation,
        instance_idx: int = 0,
    ):
        """Create force plot for single instance."""
        try:
            import shap

            return shap.force_plot(
                explanation.base_value,
                explanation.shap_values[instance_idx],
                feature_names=explanation.feature_names,
            )
        except Exception:
            return None

    def plot_dependence(
        self,
        explanation: SHAPExplanation,
        feature: str,
        X: np.ndarray,
        interaction_feature: Optional[str] = None,
    ):
        """Create dependence plot for a feature."""
        try:
            import shap
            import matplotlib.pyplot as plt

            feature_idx = self.feature_names.index(feature)

            shap.dependence_plot(
                feature_idx,
                explanation.shap_values,
                X,
                feature_names=explanation.feature_names,
                interaction_index=interaction_feature,
                show=False,
            )
            return plt.gcf()
        except Exception:
            return None


class SHAPModelExplainer:
    """
    High-level SHAP explainer for common model types.

    Automatically detects model type and uses appropriate explainer.
    """

    def __init__(self, model: Any, feature_names: Optional[List[str]] = None):
        self.model = model
        self.feature_names = feature_names
        self.explainer_type = self._detect_model_type()

    def _detect_model_type(self) -> ExplainerType:
        """Detect model type for appropriate explainer."""
        model_class = type(self.model).__name__.lower()

        if any(t in model_class for t in ["forest", "tree", "xgb", "lgb", "catboost"]):
            return ExplainerType.TREE
        elif any(t in model_class for t in ["linear", "ridge", "lasso", "elastic"]):
            return ExplainerType.LINEAR
        elif any(t in model_class for t in ["neural", "nn", "torch", "tensorflow"]):
            return ExplainerType.DEEP
        else:
            return ExplainerType.KERNEL

    def explain(
        self,
        X_train: np.ndarray,
        X_explain: np.ndarray,
    ) -> SHAPExplanation:
        """Generate SHAP explanations."""
        config = SHAPConfig(explainer_type=self.explainer_type)
        explainer = SHAPExplainer(
            self.model,
            config=config,
            feature_names=self.feature_names,
        )
        explainer.fit(X_train)
        return explainer.explain(X_explain)
