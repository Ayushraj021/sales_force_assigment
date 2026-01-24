"""
Hyperparameter Optimization Tuner

Uses Optuna for efficient hyperparameter search.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable, Union
from enum import Enum
import numpy as np
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class SamplerType(str, Enum):
    """Optuna sampler types."""
    TPE = "tpe"  # Tree-structured Parzen Estimator
    CMA_ES = "cmaes"  # Covariance Matrix Adaptation
    RANDOM = "random"
    GRID = "grid"


class PrunerType(str, Enum):
    """Optuna pruner types."""
    MEDIAN = "median"
    PERCENTILE = "percentile"
    HYPERBAND = "hyperband"
    NONE = "none"


@dataclass
class TrialResult:
    """Result of a single optimization trial."""
    trial_number: int
    params: Dict[str, Any]
    value: float
    duration: float
    state: str
    user_attrs: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OptimizationHistory:
    """History of optimization trials."""
    trials: List[TrialResult]
    best_trial: TrialResult
    best_value: float
    best_params: Dict[str, Any]
    total_time: float
    n_trials: int

    def to_dataframe(self):
        """Convert to pandas DataFrame."""
        import pandas as pd

        records = []
        for trial in self.trials:
            record = {
                "trial": trial.trial_number,
                "value": trial.value,
                "duration": trial.duration,
                "state": trial.state,
            }
            record.update(trial.params)
            records.append(record)

        return pd.DataFrame(records)


@dataclass
class TunerConfig:
    """Configuration for hyperparameter tuning."""
    # Search configuration
    n_trials: int = 100
    timeout: Optional[int] = 3600  # seconds

    # Sampler
    sampler: SamplerType = SamplerType.TPE
    seed: int = 42

    # Pruner
    pruner: PrunerType = PrunerType.MEDIAN
    warmup_steps: int = 5

    # Parallelization
    n_jobs: int = 1

    # Direction
    direction: str = "minimize"  # or "maximize"

    # Early stopping
    patience: int = 20  # Stop if no improvement for N trials


class HyperparameterTuner:
    """
    Hyperparameter Optimization using Optuna.

    Features:
    - Multiple samplers (TPE, CMA-ES, Random, Grid)
    - Pruning for early stopping of bad trials
    - Multi-objective optimization
    - Parallel trial execution
    - Study persistence

    Example:
        tuner = HyperparameterTuner()

        def objective(trial):
            lr = trial.suggest_float("lr", 1e-4, 1e-1, log=True)
            depth = trial.suggest_int("max_depth", 3, 10)

            model = train_model(lr=lr, max_depth=depth)
            return evaluate(model)

        history = tuner.optimize(objective)
        print(f"Best params: {history.best_params}")
    """

    def __init__(self, config: Optional[TunerConfig] = None):
        self.config = config or TunerConfig()
        self.study = None
        self._best_value = float('inf') if self.config.direction == "minimize" else float('-inf')
        self._no_improvement_count = 0

    def optimize(
        self,
        objective: Callable,
        param_space: Optional[Dict[str, Any]] = None,
        study_name: Optional[str] = None,
        storage: Optional[str] = None,
    ) -> OptimizationHistory:
        """
        Run hyperparameter optimization.

        Args:
            objective: Objective function that takes a trial and returns score
            param_space: Optional parameter space definition
            study_name: Optional study name for persistence
            storage: Optional storage URL (e.g., "sqlite:///study.db")

        Returns:
            OptimizationHistory with all trials and best params
        """
        try:
            import optuna
            optuna.logging.set_verbosity(optuna.logging.WARNING)
        except ImportError:
            logger.warning("Optuna not available, using random search")
            return self._random_search(objective, param_space)

        start_time = datetime.now()

        # Create sampler
        sampler = self._create_sampler()

        # Create pruner
        pruner = self._create_pruner()

        # Create or load study
        self.study = optuna.create_study(
            study_name=study_name,
            storage=storage,
            sampler=sampler,
            pruner=pruner,
            direction=self.config.direction,
            load_if_exists=True,
        )

        # Wrap objective with early stopping
        wrapped_objective = self._wrap_objective(objective)

        # Run optimization
        try:
            self.study.optimize(
                wrapped_objective,
                n_trials=self.config.n_trials,
                timeout=self.config.timeout,
                n_jobs=self.config.n_jobs,
                show_progress_bar=False,
            )
        except KeyboardInterrupt:
            logger.info("Optimization interrupted by user")

        total_time = (datetime.now() - start_time).total_seconds()

        # Convert trials to results
        trials = []
        for trial in self.study.trials:
            if trial.value is not None:
                trials.append(TrialResult(
                    trial_number=trial.number,
                    params=trial.params,
                    value=trial.value,
                    duration=trial.duration.total_seconds() if trial.duration else 0,
                    state=trial.state.name,
                    user_attrs=trial.user_attrs,
                ))

        best_trial = self.study.best_trial
        best_result = TrialResult(
            trial_number=best_trial.number,
            params=best_trial.params,
            value=best_trial.value,
            duration=best_trial.duration.total_seconds() if best_trial.duration else 0,
            state=best_trial.state.name,
            user_attrs=best_trial.user_attrs,
        )

        return OptimizationHistory(
            trials=trials,
            best_trial=best_result,
            best_value=self.study.best_value,
            best_params=self.study.best_params,
            total_time=total_time,
            n_trials=len(trials),
        )

    def _create_sampler(self):
        """Create Optuna sampler."""
        import optuna

        if self.config.sampler == SamplerType.TPE:
            return optuna.samplers.TPESampler(seed=self.config.seed)
        elif self.config.sampler == SamplerType.CMA_ES:
            return optuna.samplers.CmaEsSampler(seed=self.config.seed)
        elif self.config.sampler == SamplerType.RANDOM:
            return optuna.samplers.RandomSampler(seed=self.config.seed)
        elif self.config.sampler == SamplerType.GRID:
            return optuna.samplers.GridSampler({})
        else:
            return optuna.samplers.TPESampler(seed=self.config.seed)

    def _create_pruner(self):
        """Create Optuna pruner."""
        import optuna

        if self.config.pruner == PrunerType.MEDIAN:
            return optuna.pruners.MedianPruner(
                n_startup_trials=self.config.warmup_steps
            )
        elif self.config.pruner == PrunerType.PERCENTILE:
            return optuna.pruners.PercentilePruner(
                percentile=50.0,
                n_startup_trials=self.config.warmup_steps
            )
        elif self.config.pruner == PrunerType.HYPERBAND:
            return optuna.pruners.HyperbandPruner()
        else:
            return optuna.pruners.NopPruner()

    def _wrap_objective(self, objective: Callable) -> Callable:
        """Wrap objective with early stopping logic."""
        def wrapped(trial):
            try:
                value = objective(trial)

                # Check for improvement
                is_better = (
                    (self.config.direction == "minimize" and value < self._best_value) or
                    (self.config.direction == "maximize" and value > self._best_value)
                )

                if is_better:
                    self._best_value = value
                    self._no_improvement_count = 0
                else:
                    self._no_improvement_count += 1

                # Early stopping
                if self._no_improvement_count >= self.config.patience:
                    trial.study.stop()

                return value

            except Exception as e:
                logger.warning(f"Trial {trial.number} failed: {e}")
                raise

        return wrapped

    def _random_search(
        self,
        objective: Callable,
        param_space: Optional[Dict[str, Any]],
    ) -> OptimizationHistory:
        """Fallback random search when Optuna is not available."""
        import random

        start_time = datetime.now()
        trials = []
        best_value = float('inf') if self.config.direction == "minimize" else float('-inf')
        best_params = {}
        best_trial = None

        class MockTrial:
            def __init__(self, number):
                self.number = number
                self.params = {}

            def suggest_float(self, name, low, high, log=False):
                if log:
                    value = np.exp(random.uniform(np.log(low), np.log(high)))
                else:
                    value = random.uniform(low, high)
                self.params[name] = value
                return value

            def suggest_int(self, name, low, high):
                value = random.randint(low, high)
                self.params[name] = value
                return value

            def suggest_categorical(self, name, choices):
                value = random.choice(choices)
                self.params[name] = value
                return value

        for i in range(min(self.config.n_trials, 50)):
            trial = MockTrial(i)
            trial_start = datetime.now()

            try:
                value = objective(trial)
                duration = (datetime.now() - trial_start).total_seconds()

                result = TrialResult(
                    trial_number=i,
                    params=trial.params,
                    value=value,
                    duration=duration,
                    state="COMPLETE",
                )
                trials.append(result)

                is_better = (
                    (self.config.direction == "minimize" and value < best_value) or
                    (self.config.direction == "maximize" and value > best_value)
                )

                if is_better:
                    best_value = value
                    best_params = trial.params.copy()
                    best_trial = result

            except Exception as e:
                logger.warning(f"Trial {i} failed: {e}")

        total_time = (datetime.now() - start_time).total_seconds()

        if best_trial is None:
            best_trial = trials[0] if trials else TrialResult(0, {}, 0, 0, "FAIL")

        return OptimizationHistory(
            trials=trials,
            best_trial=best_trial,
            best_value=best_value,
            best_params=best_params,
            total_time=total_time,
            n_trials=len(trials),
        )

    def get_param_importance(self) -> Dict[str, float]:
        """Get hyperparameter importance scores."""
        if self.study is None:
            return {}

        try:
            import optuna
            importance = optuna.importance.get_param_importances(self.study)
            return dict(importance)
        except Exception:
            return {}

    def plot_optimization_history(self):
        """Plot optimization history."""
        if self.study is None:
            return None

        try:
            import optuna
            return optuna.visualization.plot_optimization_history(self.study)
        except Exception:
            return None

    def plot_param_importances(self):
        """Plot parameter importances."""
        if self.study is None:
            return None

        try:
            import optuna
            return optuna.visualization.plot_param_importances(self.study)
        except Exception:
            return None


# Predefined search spaces for common models
LIGHTGBM_SEARCH_SPACE = {
    "n_estimators": ("int", 50, 500),
    "learning_rate": ("float_log", 0.01, 0.3),
    "max_depth": ("int", 3, 12),
    "num_leaves": ("int", 20, 150),
    "min_child_samples": ("int", 5, 100),
    "subsample": ("float", 0.6, 1.0),
    "colsample_bytree": ("float", 0.6, 1.0),
    "reg_alpha": ("float_log", 1e-8, 10.0),
    "reg_lambda": ("float_log", 1e-8, 10.0),
}

XGBOOST_SEARCH_SPACE = {
    "n_estimators": ("int", 50, 500),
    "learning_rate": ("float_log", 0.01, 0.3),
    "max_depth": ("int", 3, 12),
    "min_child_weight": ("int", 1, 10),
    "subsample": ("float", 0.6, 1.0),
    "colsample_bytree": ("float", 0.6, 1.0),
    "gamma": ("float_log", 1e-8, 1.0),
    "reg_alpha": ("float_log", 1e-8, 10.0),
    "reg_lambda": ("float_log", 1e-8, 10.0),
}

NEURAL_SEARCH_SPACE = {
    "hidden_size": ("int", 16, 256),
    "num_layers": ("int", 1, 4),
    "learning_rate": ("float_log", 1e-5, 1e-2),
    "dropout": ("float", 0.0, 0.5),
    "batch_size": ("categorical", [16, 32, 64, 128]),
}


def create_objective_from_space(
    space: Dict[str, tuple],
    train_fn: Callable,
    eval_fn: Callable,
) -> Callable:
    """
    Create an Optuna objective from a parameter space definition.

    Args:
        space: Parameter space dict mapping name -> (type, *args)
        train_fn: Function that trains model given params
        eval_fn: Function that evaluates model

    Returns:
        Objective function for Optuna
    """
    def objective(trial):
        params = {}

        for name, spec in space.items():
            param_type = spec[0]

            if param_type == "int":
                params[name] = trial.suggest_int(name, spec[1], spec[2])
            elif param_type == "float":
                params[name] = trial.suggest_float(name, spec[1], spec[2])
            elif param_type == "float_log":
                params[name] = trial.suggest_float(name, spec[1], spec[2], log=True)
            elif param_type == "categorical":
                params[name] = trial.suggest_categorical(name, spec[1])

        model = train_fn(**params)
        score = eval_fn(model)

        return score

    return objective
