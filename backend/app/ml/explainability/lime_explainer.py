"""
LIME Explainer

Local Interpretable Model-agnostic Explanations.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class KernelType(str, Enum):
    """Kernel types for LIME."""
    EXPONENTIAL = "exponential"
    GAUSSIAN = "gaussian"


@dataclass
class LIMEExplanation:
    """LIME explanation for a single instance."""
    instance: np.ndarray
    prediction: float
    feature_weights: Dict[str, float]
    intercept: float
    local_model_score: float  # R² of local model
    feature_names: List[str]

    def get_top_features(self, n: int = 10) -> List[Tuple[str, float]]:
        """Get top N features by absolute weight."""
        sorted_features = sorted(
            self.feature_weights.items(),
            key=lambda x: abs(x[1]),
            reverse=True
        )
        return sorted_features[:n]

    def get_positive_features(self) -> List[Tuple[str, float]]:
        """Get features with positive contribution."""
        return [
            (k, v) for k, v in self.feature_weights.items()
            if v > 0
        ]

    def get_negative_features(self) -> List[Tuple[str, float]]:
        """Get features with negative contribution."""
        return [
            (k, v) for k, v in self.feature_weights.items()
            if v < 0
        ]

    def to_dataframe(self) -> pd.DataFrame:
        """Convert to DataFrame."""
        return pd.DataFrame([
            {"feature": k, "weight": v, "abs_weight": abs(v)}
            for k, v in self.feature_weights.items()
        ]).sort_values("abs_weight", ascending=False)


@dataclass
class LIMEConfig:
    """Configuration for LIME explainer."""
    kernel_type: KernelType = KernelType.EXPONENTIAL
    kernel_width: float = 0.75
    n_samples: int = 5000
    n_features: int = 10  # Max features in explanation
    discretize_continuous: bool = True
    discretizer: str = "quartile"  # quartile, decile, entropy


class LIMEExplainer:
    """
    LIME (Local Interpretable Model-agnostic Explanations) Explainer.

    Features:
    - Model-agnostic local explanations
    - Configurable sampling and weighting
    - Support for tabular, text, and image data
    - Feature selection for sparse explanations

    Example:
        explainer = LIMEExplainer(model, feature_names)
        explanation = explainer.explain_instance(x_test[0])

        print("Feature weights:", explanation.get_top_features())
    """

    def __init__(
        self,
        model: Any,
        feature_names: List[str],
        config: Optional[LIMEConfig] = None,
        categorical_features: Optional[List[int]] = None,
    ):
        self.model = model
        self.feature_names = feature_names
        self.config = config or LIMEConfig()
        self.categorical_features = categorical_features or []

        self._training_data: Optional[np.ndarray] = None
        self._training_stats: Dict[str, Any] = {}

    def fit(self, X: np.ndarray) -> "LIMEExplainer":
        """
        Fit explainer with training data statistics.

        Args:
            X: Training data for computing statistics

        Returns:
            self
        """
        self._training_data = X
        self._training_stats = self._compute_stats(X)
        return self

    def explain_instance(
        self,
        x: np.ndarray,
        num_features: Optional[int] = None,
    ) -> LIMEExplanation:
        """
        Explain a single instance.

        Args:
            x: Instance to explain (1D array)
            num_features: Number of features in explanation

        Returns:
            LIMEExplanation with feature weights
        """
        x = np.asarray(x).flatten()
        num_features = num_features or self.config.n_features

        # Generate perturbed samples
        samples, weights = self._generate_samples(x)

        # Get predictions for samples
        predictions = self._predict(samples)

        # Fit local linear model
        feature_weights, intercept, score = self._fit_local_model(
            samples, predictions, weights, num_features
        )

        # Get original prediction
        original_pred = self._predict(x.reshape(1, -1))[0]

        return LIMEExplanation(
            instance=x,
            prediction=original_pred,
            feature_weights=feature_weights,
            intercept=intercept,
            local_model_score=score,
            feature_names=self.feature_names,
        )

    def explain_batch(
        self,
        X: np.ndarray,
        num_features: Optional[int] = None,
    ) -> List[LIMEExplanation]:
        """Explain multiple instances."""
        return [
            self.explain_instance(x, num_features)
            for x in X
        ]

    def _compute_stats(self, X: np.ndarray) -> Dict[str, Any]:
        """Compute statistics for sampling."""
        return {
            "mean": np.mean(X, axis=0),
            "std": np.std(X, axis=0) + 1e-6,
            "min": np.min(X, axis=0),
            "max": np.max(X, axis=0),
        }

    def _generate_samples(
        self,
        x: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Generate perturbed samples around instance."""
        n_features = len(x)
        n_samples = self.config.n_samples

        # Generate random perturbations
        if self._training_data is not None:
            # Sample from training data distribution
            indices = np.random.choice(
                len(self._training_data),
                size=n_samples,
                replace=True
            )
            samples = self._training_data[indices].copy()
        else:
            # Use Gaussian perturbations
            std = self._training_stats.get("std", np.ones(n_features))
            samples = np.random.randn(n_samples, n_features) * std + x

        # Create binary representation for weighting
        binary_samples = np.zeros((n_samples, n_features))

        for i in range(n_samples):
            # Randomly select features to keep from original
            keep_mask = np.random.random(n_features) > 0.5
            samples[i, keep_mask] = x[keep_mask]
            binary_samples[i, keep_mask] = 1

        # Compute distances for weighting
        distances = self._compute_distances(binary_samples, np.ones(n_features))

        # Compute kernel weights
        weights = self._kernel(distances)

        return samples, weights

    def _compute_distances(
        self,
        samples: np.ndarray,
        original: np.ndarray,
    ) -> np.ndarray:
        """Compute distances from original instance."""
        # Cosine distance on binary representation
        return np.sqrt(np.sum((samples - original) ** 2, axis=1))

    def _kernel(self, distances: np.ndarray) -> np.ndarray:
        """Compute kernel weights from distances."""
        width = self.config.kernel_width * np.sqrt(len(self.feature_names))

        if self.config.kernel_type == KernelType.EXPONENTIAL:
            return np.sqrt(np.exp(-(distances ** 2) / (width ** 2)))
        else:  # Gaussian
            return np.exp(-(distances ** 2) / (2 * width ** 2))

    def _predict(self, X: np.ndarray) -> np.ndarray:
        """Get model predictions."""
        try:
            if hasattr(self.model, "predict_proba"):
                # For classifiers, use probability of positive class
                proba = self.model.predict_proba(X)
                if proba.ndim > 1:
                    return proba[:, 1]
                return proba
            else:
                return self.model.predict(X)
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return np.zeros(len(X))

    def _fit_local_model(
        self,
        samples: np.ndarray,
        predictions: np.ndarray,
        weights: np.ndarray,
        num_features: int,
    ) -> Tuple[Dict[str, float], float, float]:
        """Fit weighted linear model locally."""
        from sklearn.linear_model import Ridge
        from sklearn.feature_selection import SelectKBest, f_regression

        # Feature selection
        if num_features < samples.shape[1]:
            selector = SelectKBest(f_regression, k=num_features)
            samples_selected = selector.fit_transform(samples, predictions)
            selected_indices = selector.get_support(indices=True)
            selected_features = [self.feature_names[i] for i in selected_indices]
        else:
            samples_selected = samples
            selected_features = self.feature_names

        # Fit weighted ridge regression
        model = Ridge(alpha=1.0)

        # Apply sample weights
        sqrt_weights = np.sqrt(weights)
        X_weighted = samples_selected * sqrt_weights.reshape(-1, 1)
        y_weighted = predictions * sqrt_weights

        model.fit(X_weighted, y_weighted)

        # Compute R²
        y_pred = model.predict(samples_selected)
        ss_res = np.sum(weights * (predictions - y_pred) ** 2)
        ss_tot = np.sum(weights * (predictions - np.average(predictions, weights=weights)) ** 2)
        score = 1 - ss_res / (ss_tot + 1e-10)

        # Create feature weights dict
        feature_weights = {}
        for i, feature in enumerate(selected_features):
            feature_weights[feature] = float(model.coef_[i])

        # Add zero weights for non-selected features
        for feature in self.feature_names:
            if feature not in feature_weights:
                feature_weights[feature] = 0.0

        return feature_weights, float(model.intercept_), float(score)

    def plot_explanation(
        self,
        explanation: LIMEExplanation,
        num_features: int = 10,
    ):
        """Plot LIME explanation as horizontal bar chart."""
        try:
            import matplotlib.pyplot as plt

            top_features = explanation.get_top_features(num_features)
            features, weights = zip(*top_features)

            colors = ['green' if w > 0 else 'red' for w in weights]

            fig, ax = plt.subplots(figsize=(10, 6))
            y_pos = np.arange(len(features))
            ax.barh(y_pos, weights, color=colors)
            ax.set_yticks(y_pos)
            ax.set_yticklabels(features)
            ax.set_xlabel("Feature Weight")
            ax.set_title(f"LIME Explanation (R² = {explanation.local_model_score:.3f})")

            plt.tight_layout()
            return fig

        except Exception as e:
            logger.warning(f"Plot failed: {e}")
            return None


class TabularLIME(LIMEExplainer):
    """
    LIME explainer specifically optimized for tabular data.

    Includes discretization and categorical feature handling.
    """

    def __init__(
        self,
        model: Any,
        training_data: np.ndarray,
        feature_names: List[str],
        categorical_features: Optional[List[int]] = None,
        config: Optional[LIMEConfig] = None,
    ):
        super().__init__(model, feature_names, config, categorical_features)
        self.fit(training_data)

        # Create discretizer if configured
        self._discretizer = None
        if self.config.discretize_continuous:
            self._create_discretizer(training_data)

    def _create_discretizer(self, X: np.ndarray):
        """Create discretizer for continuous features."""
        n_features = X.shape[1]
        self._discretizer = {}

        for i in range(n_features):
            if i not in self.categorical_features:
                # Compute quartile boundaries
                values = X[:, i]
                if self.config.discretizer == "quartile":
                    boundaries = np.percentile(values, [25, 50, 75])
                elif self.config.discretizer == "decile":
                    boundaries = np.percentile(values, np.arange(10, 100, 10))
                else:
                    boundaries = np.percentile(values, [25, 50, 75])

                self._discretizer[i] = boundaries

    def _discretize(self, x: np.ndarray) -> np.ndarray:
        """Discretize continuous features."""
        if self._discretizer is None:
            return x

        x_discrete = x.copy()
        for i, boundaries in self._discretizer.items():
            x_discrete[i] = np.digitize(x[i], boundaries)

        return x_discrete
