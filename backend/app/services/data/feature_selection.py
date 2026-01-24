"""
Feature Selection Service

Automated feature selection and analysis:
- Correlation analysis
- Variance threshold filtering
- Feature importance ranking
- Mutual information scoring
- Recursive feature elimination
- Multicollinearity detection
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Set
from enum import Enum
import pandas as pd
import numpy as np
from scipy import stats
from scipy.stats import spearmanr, pearsonr
import warnings

warnings.filterwarnings('ignore')


class SelectionMethod(str, Enum):
    """Feature selection methods"""
    VARIANCE_THRESHOLD = "variance_threshold"
    CORRELATION_FILTER = "correlation_filter"
    MUTUAL_INFORMATION = "mutual_information"
    ANOVA_F_TEST = "anova_f_test"
    CHI_SQUARE = "chi_square"
    IMPORTANCE_BASED = "importance_based"
    RFE = "recursive_feature_elimination"
    COMBINED = "combined"


class CorrelationMethod(str, Enum):
    """Correlation calculation methods"""
    PEARSON = "pearson"
    SPEARMAN = "spearman"
    KENDALL = "kendall"


@dataclass
class FeatureScore:
    """Score and metadata for a single feature"""
    name: str
    score: float
    rank: int
    selected: bool
    method: str
    statistics: Dict[str, Any] = field(default_factory=dict)
    correlations: Dict[str, float] = field(default_factory=dict)
    recommendation: str = ""


@dataclass
class CorrelationPair:
    """Correlation between two features"""
    feature1: str
    feature2: str
    correlation: float
    p_value: Optional[float]
    method: str
    is_significant: bool


@dataclass
class FeatureSelectionResult:
    """Complete feature selection result"""
    selected_features: List[str]
    removed_features: List[str]
    feature_scores: List[FeatureScore]
    correlation_matrix: Dict[str, Dict[str, float]]
    high_correlations: List[CorrelationPair]
    multicollinear_groups: List[List[str]]
    recommendations: List[str]
    summary: Dict[str, Any]


class FeatureSelectionService:
    """Service for automated feature selection"""

    def __init__(self):
        pass

    def select_features(
        self,
        df: pd.DataFrame,
        target_column: Optional[str] = None,
        method: SelectionMethod = SelectionMethod.COMBINED,
        config: Optional[Dict[str, Any]] = None
    ) -> FeatureSelectionResult:
        """
        Perform feature selection on a DataFrame

        Args:
            df: Input DataFrame
            target_column: Target variable column (for supervised selection)
            method: Selection method to use
            config: Configuration options

        Returns:
            FeatureSelectionResult with selected features and analysis
        """
        config = config or {}

        # Get feature columns (exclude target)
        feature_columns = [col for col in df.columns if col != target_column]
        numeric_features = df[feature_columns].select_dtypes(include=[np.number]).columns.tolist()

        # Calculate correlation matrix
        correlation_matrix = self._calculate_correlation_matrix(
            df[numeric_features],
            method=CorrelationMethod(config.get('correlation_method', 'pearson'))
        )

        # Find high correlations
        high_correlations = self._find_high_correlations(
            correlation_matrix,
            threshold=config.get('correlation_threshold', 0.8)
        )

        # Detect multicollinearity
        multicollinear_groups = self._detect_multicollinearity(
            df[numeric_features],
            threshold=config.get('vif_threshold', 5.0)
        )

        # Calculate feature scores based on method
        feature_scores = self._calculate_feature_scores(
            df, target_column, numeric_features, method, config
        )

        # Select features
        selected_features, removed_features = self._apply_selection(
            feature_scores, high_correlations, multicollinear_groups, config
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            feature_scores, high_correlations, multicollinear_groups
        )

        # Summary statistics
        summary = {
            'total_features': len(feature_columns),
            'numeric_features': len(numeric_features),
            'selected_features': len(selected_features),
            'removed_features': len(removed_features),
            'high_correlation_pairs': len(high_correlations),
            'multicollinear_groups': len(multicollinear_groups),
        }

        return FeatureSelectionResult(
            selected_features=selected_features,
            removed_features=removed_features,
            feature_scores=feature_scores,
            correlation_matrix=correlation_matrix,
            high_correlations=high_correlations,
            multicollinear_groups=multicollinear_groups,
            recommendations=recommendations,
            summary=summary,
        )

    def _calculate_correlation_matrix(
        self,
        df: pd.DataFrame,
        method: CorrelationMethod = CorrelationMethod.PEARSON
    ) -> Dict[str, Dict[str, float]]:
        """Calculate correlation matrix"""
        if df.empty:
            return {}

        corr_matrix = df.corr(method=method.value)
        return corr_matrix.to_dict()

    def _find_high_correlations(
        self,
        correlation_matrix: Dict[str, Dict[str, float]],
        threshold: float = 0.8
    ) -> List[CorrelationPair]:
        """Find highly correlated feature pairs"""
        high_correlations = []
        processed_pairs: Set[Tuple[str, str]] = set()

        for feat1, correlations in correlation_matrix.items():
            for feat2, corr_value in correlations.items():
                if feat1 == feat2:
                    continue

                pair_key = tuple(sorted([feat1, feat2]))
                if pair_key in processed_pairs:
                    continue

                processed_pairs.add(pair_key)

                if abs(corr_value) >= threshold:
                    high_correlations.append(CorrelationPair(
                        feature1=feat1,
                        feature2=feat2,
                        correlation=round(corr_value, 4),
                        p_value=None,
                        method='pearson',
                        is_significant=True,
                    ))

        # Sort by absolute correlation
        high_correlations.sort(key=lambda x: abs(x.correlation), reverse=True)
        return high_correlations

    def _detect_multicollinearity(
        self,
        df: pd.DataFrame,
        threshold: float = 5.0
    ) -> List[List[str]]:
        """Detect multicollinear feature groups using VIF"""
        if df.empty or len(df.columns) < 2:
            return []

        multicollinear_groups = []

        try:
            # Calculate VIF for each feature
            vif_data = {}
            for col in df.columns:
                if df[col].std() == 0:
                    continue

                # Simple VIF approximation using R-squared
                other_cols = [c for c in df.columns if c != col]
                if not other_cols:
                    continue

                X = df[other_cols].dropna()
                y = df[col].dropna()

                # Align indices
                common_idx = X.index.intersection(y.index)
                if len(common_idx) < 10:
                    continue

                X = X.loc[common_idx]
                y = y.loc[common_idx]

                # Calculate R-squared using correlation
                correlations = X.corrwith(y)
                r_squared = correlations.pow(2).mean()
                vif = 1 / (1 - r_squared) if r_squared < 1 else float('inf')
                vif_data[col] = vif

            # Group features with high VIF
            high_vif_features = [col for col, vif in vif_data.items() if vif > threshold]

            if len(high_vif_features) > 1:
                # Cluster highly correlated high-VIF features
                corr_matrix = df[high_vif_features].corr()
                processed = set()

                for feat in high_vif_features:
                    if feat in processed:
                        continue

                    group = [feat]
                    processed.add(feat)

                    for other_feat in high_vif_features:
                        if other_feat in processed:
                            continue

                        if abs(corr_matrix.loc[feat, other_feat]) > 0.7:
                            group.append(other_feat)
                            processed.add(other_feat)

                    if len(group) > 1:
                        multicollinear_groups.append(group)

        except Exception:
            pass

        return multicollinear_groups

    def _calculate_feature_scores(
        self,
        df: pd.DataFrame,
        target_column: Optional[str],
        numeric_features: List[str],
        method: SelectionMethod,
        config: Dict[str, Any]
    ) -> List[FeatureScore]:
        """Calculate feature scores using specified method"""
        scores = []

        for feat in numeric_features:
            score_value = 0.0
            statistics = {}

            # Variance score
            variance = df[feat].var()
            statistics['variance'] = round(variance, 4) if not np.isnan(variance) else 0

            # Calculate score based on method
            if target_column and target_column in df.columns:
                target = df[target_column]

                if method in [SelectionMethod.CORRELATION_FILTER, SelectionMethod.COMBINED]:
                    try:
                        corr, p_value = pearsonr(
                            df[feat].dropna(),
                            target.loc[df[feat].dropna().index]
                        )
                        statistics['target_correlation'] = round(corr, 4)
                        statistics['correlation_p_value'] = round(p_value, 4)
                        score_value = abs(corr) if not np.isnan(corr) else 0
                    except Exception:
                        score_value = 0

                if method in [SelectionMethod.MUTUAL_INFORMATION, SelectionMethod.COMBINED]:
                    try:
                        mi_score = self._calculate_mutual_information(df[feat], target)
                        statistics['mutual_information'] = round(mi_score, 4)
                        if method == SelectionMethod.MUTUAL_INFORMATION:
                            score_value = mi_score
                        elif method == SelectionMethod.COMBINED:
                            score_value = (score_value + mi_score) / 2
                    except Exception:
                        pass

                if method == SelectionMethod.ANOVA_F_TEST:
                    try:
                        f_stat, p_value = self._calculate_anova_f(df[feat], target)
                        statistics['f_statistic'] = round(f_stat, 4)
                        statistics['f_p_value'] = round(p_value, 4)
                        score_value = f_stat
                    except Exception:
                        score_value = 0

            if method == SelectionMethod.VARIANCE_THRESHOLD:
                score_value = variance if not np.isnan(variance) else 0

            scores.append(FeatureScore(
                name=feat,
                score=round(score_value, 4),
                rank=0,  # Will be set after sorting
                selected=True,  # Will be updated
                method=method.value,
                statistics=statistics,
                correlations={},
            ))

        # Sort by score and assign ranks
        scores.sort(key=lambda x: x.score, reverse=True)
        for i, score in enumerate(scores):
            score.rank = i + 1

        return scores

    def _calculate_mutual_information(self, feature: pd.Series, target: pd.Series) -> float:
        """Calculate mutual information between feature and target"""
        # Simple histogram-based MI estimation
        try:
            feature_clean = feature.dropna()
            target_clean = target.loc[feature_clean.index]

            # Discretize continuous variables
            n_bins = min(10, len(feature_clean.unique()))
            feature_binned = pd.cut(feature_clean, bins=n_bins, labels=False)

            if target_clean.dtype in ['int64', 'float64']:
                target_binned = pd.cut(target_clean, bins=n_bins, labels=False)
            else:
                target_binned = pd.factorize(target_clean)[0]

            # Calculate joint and marginal probabilities
            joint_counts = pd.crosstab(feature_binned, target_binned)
            joint_probs = joint_counts / joint_counts.sum().sum()

            marginal_x = joint_probs.sum(axis=1)
            marginal_y = joint_probs.sum(axis=0)

            # Calculate MI
            mi = 0.0
            for i in joint_probs.index:
                for j in joint_probs.columns:
                    p_xy = joint_probs.loc[i, j]
                    p_x = marginal_x.loc[i]
                    p_y = marginal_y.loc[j]
                    if p_xy > 0 and p_x > 0 and p_y > 0:
                        mi += p_xy * np.log2(p_xy / (p_x * p_y))

            return mi
        except Exception:
            return 0.0

    def _calculate_anova_f(self, feature: pd.Series, target: pd.Series) -> Tuple[float, float]:
        """Calculate ANOVA F-statistic"""
        try:
            feature_clean = feature.dropna()
            target_clean = target.loc[feature_clean.index]

            # Group feature values by target categories
            if target_clean.dtype == 'object' or target_clean.nunique() < 10:
                groups = [feature_clean[target_clean == cat].values for cat in target_clean.unique()]
                groups = [g for g in groups if len(g) > 0]

                if len(groups) >= 2:
                    f_stat, p_value = stats.f_oneway(*groups)
                    return f_stat, p_value
        except Exception:
            pass

        return 0.0, 1.0

    def _apply_selection(
        self,
        feature_scores: List[FeatureScore],
        high_correlations: List[CorrelationPair],
        multicollinear_groups: List[List[str]],
        config: Dict[str, Any]
    ) -> Tuple[List[str], List[str]]:
        """Apply selection rules to features"""
        selected = set(s.name for s in feature_scores)
        removed = set()

        # Remove features with low variance
        variance_threshold = config.get('variance_threshold', 0.01)
        for score in feature_scores:
            if score.statistics.get('variance', 1) < variance_threshold:
                if score.name in selected:
                    selected.remove(score.name)
                    removed.add(score.name)
                    score.selected = False
                    score.recommendation = f"Low variance ({score.statistics.get('variance', 0):.4f})"

        # Remove highly correlated features (keep higher scoring one)
        for corr_pair in high_correlations:
            if corr_pair.feature1 in selected and corr_pair.feature2 in selected:
                # Find scores
                score1 = next((s for s in feature_scores if s.name == corr_pair.feature1), None)
                score2 = next((s for s in feature_scores if s.name == corr_pair.feature2), None)

                if score1 and score2:
                    to_remove = corr_pair.feature2 if score1.score >= score2.score else corr_pair.feature1
                    selected.remove(to_remove)
                    removed.add(to_remove)

                    for s in feature_scores:
                        if s.name == to_remove:
                            s.selected = False
                            s.recommendation = f"High correlation with {corr_pair.feature1 if to_remove == corr_pair.feature2 else corr_pair.feature2} ({corr_pair.correlation:.2f})"

        # Handle multicollinear groups (keep best from each group)
        for group in multicollinear_groups:
            group_scores = [(s.name, s.score) for s in feature_scores if s.name in group]
            if group_scores:
                group_scores.sort(key=lambda x: x[1], reverse=True)
                best = group_scores[0][0]

                for feat, _ in group_scores[1:]:
                    if feat in selected:
                        selected.remove(feat)
                        removed.add(feat)

                        for s in feature_scores:
                            if s.name == feat:
                                s.selected = False
                                s.recommendation = f"Multicollinear with {best}"

        # Apply max features limit
        max_features = config.get('max_features')
        if max_features and len(selected) > max_features:
            sorted_selected = sorted(
                [(s.name, s.score) for s in feature_scores if s.name in selected],
                key=lambda x: x[1],
                reverse=True
            )

            for feat, _ in sorted_selected[max_features:]:
                selected.remove(feat)
                removed.add(feat)

                for s in feature_scores:
                    if s.name == feat:
                        s.selected = False
                        s.recommendation = f"Exceeded max features limit ({max_features})"

        return list(selected), list(removed)

    def _generate_recommendations(
        self,
        feature_scores: List[FeatureScore],
        high_correlations: List[CorrelationPair],
        multicollinear_groups: List[List[str]]
    ) -> List[str]:
        """Generate feature selection recommendations"""
        recommendations = []

        # High correlation warnings
        if high_correlations:
            recommendations.append(
                f"Found {len(high_correlations)} highly correlated feature pairs. "
                "Consider removing redundant features to reduce multicollinearity."
            )

        # Multicollinearity warnings
        if multicollinear_groups:
            recommendations.append(
                f"Detected {len(multicollinear_groups)} groups of multicollinear features. "
                "Keep only one feature from each group."
            )

        # Low importance features
        low_importance = [s for s in feature_scores if s.score < 0.1 and s.selected]
        if low_importance:
            recommendations.append(
                f"{len(low_importance)} features have low importance scores. "
                "Consider removing: " + ", ".join([s.name for s in low_importance[:5]])
            )

        # Missing target correlation
        no_target_corr = [s for s in feature_scores if 'target_correlation' not in s.statistics]
        if no_target_corr and len(feature_scores) > 0:
            recommendations.append(
                "No target column specified. Provide target column for supervised feature selection."
            )

        return recommendations

    def calculate_feature_importance(
        self,
        df: pd.DataFrame,
        target_column: str,
        method: str = 'random_forest'
    ) -> List[FeatureScore]:
        """
        Calculate feature importance using tree-based methods

        Args:
            df: Input DataFrame
            target_column: Target variable column
            method: 'random_forest' or 'gradient_boosting'

        Returns:
            List of FeatureScore with importance rankings
        """
        try:
            from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
            from sklearn.ensemble import GradientBoostingRegressor, GradientBoostingClassifier

            feature_columns = [col for col in df.columns if col != target_column]
            numeric_features = df[feature_columns].select_dtypes(include=[np.number]).columns.tolist()

            X = df[numeric_features].fillna(0)
            y = df[target_column]

            # Determine if classification or regression
            is_classification = y.dtype == 'object' or y.nunique() < 10

            if method == 'random_forest':
                if is_classification:
                    model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
                else:
                    model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
            else:
                if is_classification:
                    model = GradientBoostingClassifier(n_estimators=100, random_state=42)
                else:
                    model = GradientBoostingRegressor(n_estimators=100, random_state=42)

            if is_classification:
                y = pd.factorize(y)[0]

            model.fit(X, y)
            importances = model.feature_importances_

            scores = []
            for i, feat in enumerate(numeric_features):
                scores.append(FeatureScore(
                    name=feat,
                    score=round(float(importances[i]), 4),
                    rank=0,
                    selected=True,
                    method=method,
                    statistics={'importance': round(float(importances[i]), 4)},
                ))

            scores.sort(key=lambda x: x.score, reverse=True)
            for i, score in enumerate(scores):
                score.rank = i + 1

            return scores

        except ImportError:
            return []
        except Exception:
            return []

    def get_correlation_heatmap_data(
        self,
        df: pd.DataFrame,
        columns: Optional[List[str]] = None,
        method: CorrelationMethod = CorrelationMethod.PEARSON
    ) -> Dict[str, Any]:
        """
        Get correlation data formatted for heatmap visualization

        Returns:
            Dictionary with columns, data matrix, and annotations
        """
        if columns:
            numeric_cols = [c for c in columns if c in df.select_dtypes(include=[np.number]).columns]
        else:
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

        if not numeric_cols:
            return {'columns': [], 'data': [], 'annotations': []}

        corr_matrix = df[numeric_cols].corr(method=method.value)

        return {
            'columns': numeric_cols,
            'data': corr_matrix.values.tolist(),
            'annotations': [
                [f"{corr_matrix.iloc[i, j]:.2f}" for j in range(len(numeric_cols))]
                for i in range(len(numeric_cols))
            ],
        }


# Singleton instance
feature_selection_service = FeatureSelectionService()
