"""
Creative Refresh Optimizer

Optimizes timing for creative refreshes to maximize campaign performance.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import numpy as np
import pandas as pd
from scipy.optimize import minimize, differential_evolution
import logging

logger = logging.getLogger(__name__)


class RefreshStrategy(str, Enum):
    """Creative refresh strategies."""
    THRESHOLD = "threshold"  # Refresh when effectiveness drops below threshold
    SCHEDULED = "scheduled"  # Regular schedule (e.g., every 2 weeks)
    ADAPTIVE = "adaptive"  # ML-optimized timing
    STAGGERED = "staggered"  # Stagger refreshes across creatives


@dataclass
class RefreshConfig:
    """Configuration for refresh optimization."""
    min_days_between_refresh: int = 7
    max_days_between_refresh: int = 60
    effectiveness_threshold: float = 0.5
    budget_weight: float = 0.3  # Weight for budget considerations
    performance_weight: float = 0.7  # Weight for performance
    lookahead_days: int = 30


@dataclass
class RefreshSchedule:
    """Optimized refresh schedule for a creative."""
    creative_id: str
    recommended_refresh_date: datetime
    days_until_refresh: int
    expected_effectiveness_at_refresh: float
    estimated_lost_performance: float  # If not refreshed
    confidence: float
    strategy_used: RefreshStrategy
    alternatives: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class PortfolioRefreshPlan:
    """Refresh plan for a portfolio of creatives."""
    schedules: List[RefreshSchedule]
    total_refreshes: int
    estimated_budget_impact: float
    optimized_performance_score: float
    timeline: pd.DataFrame = field(default_factory=pd.DataFrame)


class RefreshOptimizer:
    """
    Creative Refresh Timing Optimizer.

    Features:
    - Multiple refresh strategies
    - Portfolio-level optimization
    - Budget-aware scheduling
    - Performance forecasting

    Example:
        optimizer = RefreshOptimizer()

        # Get optimal refresh timing
        schedule = optimizer.optimize_single(
            creative_id="ad_123",
            fatigue_metrics=metrics,
            production_cost=5000,
        )

        # Portfolio optimization
        plan = optimizer.optimize_portfolio(
            creatives=[...],
            total_refresh_budget=50000,
        )
    """

    def __init__(self, config: Optional[RefreshConfig] = None):
        self.config = config or RefreshConfig()
        self._creative_costs: Dict[str, float] = {}
        self._historical_performance: Dict[str, List[float]] = {}

    def optimize_single(
        self,
        creative_id: str,
        current_effectiveness: float,
        fatigue_rate: float,  # Daily decay rate
        production_cost: float = 0,
        daily_spend: float = 0,
        strategy: RefreshStrategy = RefreshStrategy.ADAPTIVE,
    ) -> RefreshSchedule:
        """
        Optimize refresh timing for a single creative.

        Args:
            creative_id: Creative identifier
            current_effectiveness: Current effectiveness (0-1)
            fatigue_rate: Daily effectiveness decay rate
            production_cost: Cost to produce new creative
            daily_spend: Daily ad spend on this creative
            strategy: Refresh strategy to use

        Returns:
            RefreshSchedule with optimal timing
        """
        self._creative_costs[creative_id] = production_cost

        if strategy == RefreshStrategy.THRESHOLD:
            return self._threshold_strategy(
                creative_id, current_effectiveness, fatigue_rate
            )
        elif strategy == RefreshStrategy.SCHEDULED:
            return self._scheduled_strategy(
                creative_id, current_effectiveness, fatigue_rate
            )
        elif strategy == RefreshStrategy.ADAPTIVE:
            return self._adaptive_strategy(
                creative_id, current_effectiveness, fatigue_rate,
                production_cost, daily_spend
            )
        else:
            return self._threshold_strategy(
                creative_id, current_effectiveness, fatigue_rate
            )

    def _threshold_strategy(
        self,
        creative_id: str,
        effectiveness: float,
        decay_rate: float,
    ) -> RefreshSchedule:
        """Simple threshold-based strategy."""
        threshold = self.config.effectiveness_threshold

        if effectiveness <= threshold:
            days_until = 0
        elif decay_rate > 0:
            # Calculate days until threshold
            days_until = max(0, int(
                (effectiveness - threshold) / decay_rate
            ))
        else:
            days_until = self.config.max_days_between_refresh

        days_until = min(days_until, self.config.max_days_between_refresh)

        refresh_date = datetime.now() + timedelta(days=days_until)
        effectiveness_at_refresh = max(0, effectiveness - decay_rate * days_until)

        return RefreshSchedule(
            creative_id=creative_id,
            recommended_refresh_date=refresh_date,
            days_until_refresh=days_until,
            expected_effectiveness_at_refresh=effectiveness_at_refresh,
            estimated_lost_performance=self._estimate_lost_performance(
                effectiveness, decay_rate, days_until
            ),
            confidence=0.7,
            strategy_used=RefreshStrategy.THRESHOLD,
        )

    def _scheduled_strategy(
        self,
        creative_id: str,
        effectiveness: float,
        decay_rate: float,
    ) -> RefreshSchedule:
        """Fixed schedule strategy."""
        # Default: refresh every 14 days
        schedule_interval = 14
        days_until = schedule_interval

        refresh_date = datetime.now() + timedelta(days=days_until)
        effectiveness_at_refresh = max(0, effectiveness - decay_rate * days_until)

        return RefreshSchedule(
            creative_id=creative_id,
            recommended_refresh_date=refresh_date,
            days_until_refresh=days_until,
            expected_effectiveness_at_refresh=effectiveness_at_refresh,
            estimated_lost_performance=self._estimate_lost_performance(
                effectiveness, decay_rate, days_until
            ),
            confidence=0.6,
            strategy_used=RefreshStrategy.SCHEDULED,
        )

    def _adaptive_strategy(
        self,
        creative_id: str,
        effectiveness: float,
        decay_rate: float,
        production_cost: float,
        daily_spend: float,
    ) -> RefreshSchedule:
        """ML-optimized adaptive strategy."""

        def objective(days: np.ndarray) -> float:
            """Objective function to minimize (negative ROI)."""
            d = int(days[0])

            # Performance over period
            total_performance = 0
            current_eff = effectiveness
            for day in range(d):
                total_performance += current_eff * daily_spend
                current_eff = max(0, current_eff - decay_rate)

            # Cost of refresh
            refresh_cost = production_cost

            # ROI = (performance - cost) / cost
            if refresh_cost > 0:
                roi = (total_performance - refresh_cost) / refresh_cost
            else:
                roi = total_performance

            return -roi  # Minimize negative ROI

        # Optimize
        result = minimize(
            objective,
            x0=[14],  # Start with 14 days
            bounds=[(
                self.config.min_days_between_refresh,
                self.config.max_days_between_refresh
            )],
            method="L-BFGS-B",
        )

        optimal_days = int(result.x[0])
        refresh_date = datetime.now() + timedelta(days=optimal_days)
        effectiveness_at_refresh = max(0, effectiveness - decay_rate * optimal_days)

        # Generate alternatives
        alternatives = []
        for days in [7, 14, 21, 30]:
            if days != optimal_days:
                eff_at_d = max(0, effectiveness - decay_rate * days)
                alternatives.append({
                    "days": days,
                    "effectiveness": eff_at_d,
                    "estimated_roi": -objective(np.array([days])),
                })

        return RefreshSchedule(
            creative_id=creative_id,
            recommended_refresh_date=refresh_date,
            days_until_refresh=optimal_days,
            expected_effectiveness_at_refresh=effectiveness_at_refresh,
            estimated_lost_performance=self._estimate_lost_performance(
                effectiveness, decay_rate, optimal_days
            ),
            confidence=0.85,
            strategy_used=RefreshStrategy.ADAPTIVE,
            alternatives=alternatives,
        )

    def _estimate_lost_performance(
        self,
        effectiveness: float,
        decay_rate: float,
        days: int,
    ) -> float:
        """Estimate cumulative lost performance due to fatigue."""
        # Compare to baseline (100% effectiveness)
        optimal_performance = days * 1.0  # If always at 100%

        actual_performance = 0
        current_eff = effectiveness
        for _ in range(days):
            actual_performance += current_eff
            current_eff = max(0, current_eff - decay_rate)

        return float(optimal_performance - actual_performance)

    def optimize_portfolio(
        self,
        creatives: List[Dict[str, Any]],
        total_refresh_budget: float,
        max_simultaneous_refreshes: int = 3,
    ) -> PortfolioRefreshPlan:
        """
        Optimize refresh timing across a portfolio of creatives.

        Args:
            creatives: List of creative info dicts with:
                - creative_id
                - current_effectiveness
                - fatigue_rate
                - production_cost
                - daily_spend
            total_refresh_budget: Total budget for refreshes
            max_simultaneous_refreshes: Max refreshes at once

        Returns:
            PortfolioRefreshPlan with optimized schedule
        """
        n_creatives = len(creatives)

        # Calculate individual optimal timings first
        individual_schedules = []
        for creative in creatives:
            schedule = self.optimize_single(
                creative_id=creative["creative_id"],
                current_effectiveness=creative.get("current_effectiveness", 0.7),
                fatigue_rate=creative.get("fatigue_rate", 0.02),
                production_cost=creative.get("production_cost", 1000),
                daily_spend=creative.get("daily_spend", 100),
                strategy=RefreshStrategy.ADAPTIVE,
            )
            individual_schedules.append(schedule)

        # Sort by urgency (earliest recommended refresh first)
        individual_schedules.sort(key=lambda s: s.days_until_refresh)

        # Apply budget constraints
        final_schedules = []
        remaining_budget = total_refresh_budget
        refreshes_this_period = {}  # day -> count

        for schedule in individual_schedules:
            creative_cost = self._creative_costs.get(schedule.creative_id, 1000)

            if remaining_budget >= creative_cost:
                # Check simultaneous refresh constraint
                refresh_day = schedule.days_until_refresh
                if refreshes_this_period.get(refresh_day, 0) >= max_simultaneous_refreshes:
                    # Stagger to next available day
                    for d in range(refresh_day + 1, self.config.max_days_between_refresh):
                        if refreshes_this_period.get(d, 0) < max_simultaneous_refreshes:
                            schedule.days_until_refresh = d
                            schedule.recommended_refresh_date = (
                                datetime.now() + timedelta(days=d)
                            )
                            schedule.strategy_used = RefreshStrategy.STAGGERED
                            break

                final_schedules.append(schedule)
                remaining_budget -= creative_cost
                refreshes_this_period[schedule.days_until_refresh] = (
                    refreshes_this_period.get(schedule.days_until_refresh, 0) + 1
                )

        # Build timeline
        timeline_data = []
        for schedule in final_schedules:
            timeline_data.append({
                "creative_id": schedule.creative_id,
                "refresh_date": schedule.recommended_refresh_date,
                "days_until": schedule.days_until_refresh,
                "effectiveness_at_refresh": schedule.expected_effectiveness_at_refresh,
                "strategy": schedule.strategy_used.value,
            })

        timeline_df = pd.DataFrame(timeline_data)
        if not timeline_df.empty:
            timeline_df = timeline_df.sort_values("refresh_date")

        # Calculate overall metrics
        total_lost_performance = sum(s.estimated_lost_performance for s in final_schedules)
        optimized_score = 1 - (total_lost_performance / (n_creatives * self.config.lookahead_days))

        return PortfolioRefreshPlan(
            schedules=final_schedules,
            total_refreshes=len(final_schedules),
            estimated_budget_impact=total_refresh_budget - remaining_budget,
            optimized_performance_score=max(0, min(1, optimized_score)),
            timeline=timeline_df,
        )

    def simulate_refresh_scenarios(
        self,
        creative_id: str,
        effectiveness: float,
        decay_rate: float,
        production_cost: float,
        daily_spend: float,
        simulation_days: int = 90,
    ) -> pd.DataFrame:
        """
        Simulate different refresh scenarios.

        Args:
            creative_id: Creative identifier
            effectiveness: Starting effectiveness
            decay_rate: Daily decay rate
            production_cost: Cost per refresh
            daily_spend: Daily ad spend
            simulation_days: Days to simulate

        Returns:
            DataFrame comparing scenarios
        """
        scenarios = [
            {"name": "No Refresh", "interval": None},
            {"name": "Weekly", "interval": 7},
            {"name": "Bi-weekly", "interval": 14},
            {"name": "Monthly", "interval": 30},
            {"name": "Adaptive", "interval": "adaptive"},
        ]

        results = []

        for scenario in scenarios:
            total_performance = 0
            total_cost = production_cost  # Initial creative
            current_eff = effectiveness
            day_since_refresh = 0

            for day in range(simulation_days):
                # Daily performance
                daily_performance = current_eff * daily_spend
                total_performance += daily_performance

                # Decay
                current_eff = max(0, current_eff - decay_rate)
                day_since_refresh += 1

                # Check for refresh
                should_refresh = False

                if scenario["interval"] is None:
                    should_refresh = False
                elif scenario["interval"] == "adaptive":
                    # Refresh when effectiveness drops below threshold
                    should_refresh = current_eff < self.config.effectiveness_threshold
                else:
                    should_refresh = day_since_refresh >= scenario["interval"]

                if should_refresh:
                    current_eff = 1.0  # Reset effectiveness
                    total_cost += production_cost
                    day_since_refresh = 0

            roi = (total_performance - total_cost) / total_cost if total_cost > 0 else 0

            results.append({
                "scenario": scenario["name"],
                "total_performance": total_performance,
                "total_cost": total_cost,
                "roi": roi,
                "final_effectiveness": current_eff,
            })

        return pd.DataFrame(results)

    def get_refresh_calendar(
        self,
        schedules: List[RefreshSchedule],
        weeks: int = 8,
    ) -> pd.DataFrame:
        """
        Generate a refresh calendar view.

        Args:
            schedules: List of refresh schedules
            weeks: Number of weeks to show

        Returns:
            DataFrame with calendar view
        """
        start_date = datetime.now()
        calendar_data = []

        for week in range(weeks):
            week_start = start_date + timedelta(weeks=week)
            week_end = week_start + timedelta(days=6)

            week_refreshes = [
                s for s in schedules
                if week_start <= s.recommended_refresh_date <= week_end
            ]

            calendar_data.append({
                "week": week + 1,
                "start_date": week_start.strftime("%Y-%m-%d"),
                "end_date": week_end.strftime("%Y-%m-%d"),
                "num_refreshes": len(week_refreshes),
                "creative_ids": [s.creative_id for s in week_refreshes],
            })

        return pd.DataFrame(calendar_data)
