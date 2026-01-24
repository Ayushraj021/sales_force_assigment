/**
 * Calendar Heatmap Component
 *
 * Visualizes time-series data in a GitHub-style calendar grid.
 * Great for showing daily metrics, activity patterns, and seasonality.
 */

import { useMemo, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import * as d3 from 'd3';
import { cn } from '@/lib/utils';

// Types
interface CalendarDay {
  date: Date;
  value: number;
}

interface CalendarHeatmapProps {
  data: CalendarDay[];
  startDate?: Date;
  endDate?: Date;
  width?: number;
  cellSize?: number;
  cellGap?: number;
  className?: string;
  colorScheme?: string[];
  showMonthLabels?: boolean;
  showDayLabels?: boolean;
  showLegend?: boolean;
  animated?: boolean;
  onDayClick?: (date: Date, value: number) => void;
  onDayHover?: (date: Date | null, value: number | null) => void;
  valueFormatter?: (value: number) => string;
  emptyColor?: string;
}

interface TooltipData {
  x: number;
  y: number;
  date: Date;
  value: number;
}

// Default color scheme (green like GitHub)
const DEFAULT_COLORS = ['#ebedf0', '#9be9a8', '#40c463', '#30a14e', '#216e39'];

// Day names
const DAY_NAMES = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

export function CalendarHeatmap({
  data,
  startDate: propStartDate,
  endDate: propEndDate,
  width = 800,
  cellSize = 12,
  cellGap = 2,
  className,
  colorScheme = DEFAULT_COLORS,
  showMonthLabels = true,
  showDayLabels = true,
  showLegend = true,
  animated = true,
  onDayClick,
  onDayHover,
  valueFormatter = (v) => v.toLocaleString(),
  emptyColor = '#ebedf0',
}: CalendarHeatmapProps) {
  const [tooltip, setTooltip] = useState<TooltipData | null>(null);
  const [hoveredDate, setHoveredDate] = useState<string | null>(null);

  // Calculate date range
  const { startDate, endDate } = useMemo(() => {
    if (propStartDate && propEndDate) {
      return { startDate: propStartDate, endDate: propEndDate };
    }

    const dates = data.map((d) => d.date);
    const min = dates.length > 0 ? new Date(Math.min(...dates.map((d) => d.getTime()))) : new Date();
    const max = dates.length > 0 ? new Date(Math.max(...dates.map((d) => d.getTime()))) : new Date();

    // Adjust to start from Sunday
    const start = propStartDate || new Date(min);
    start.setDate(start.getDate() - start.getDay());

    // Adjust to end on Saturday
    const end = propEndDate || new Date(max);
    end.setDate(end.getDate() + (6 - end.getDay()));

    return { startDate: start, endDate: end };
  }, [data, propStartDate, propEndDate]);

  // Create data map for quick lookup
  const dataMap = useMemo(() => {
    const map = new Map<string, number>();
    data.forEach(({ date, value }) => {
      const key = d3.timeFormat('%Y-%m-%d')(date);
      map.set(key, value);
    });
    return map;
  }, [data]);

  // Calculate value range for color scale
  const { minValue, maxValue } = useMemo(() => {
    const values = data.map((d) => d.value);
    return {
      minValue: Math.min(0, ...values),
      maxValue: Math.max(...values) || 1,
    };
  }, [data]);

  // Color scale
  const getColor = useCallback(
    (value: number | undefined) => {
      if (value === undefined) return emptyColor;
      if (value === 0) return colorScheme[0];

      const normalized = (value - minValue) / (maxValue - minValue);
      const index = Math.min(
        colorScheme.length - 1,
        Math.floor(normalized * (colorScheme.length - 1)) + 1
      );
      return colorScheme[index];
    },
    [colorScheme, minValue, maxValue, emptyColor]
  );

  // Generate weeks and days
  const weeks = useMemo(() => {
    const result: Array<{ week: number; days: Array<{ date: Date; value?: number }> }> = [];
    let currentDate = new Date(startDate);
    let weekIndex = 0;

    while (currentDate <= endDate) {
      const week: Array<{ date: Date; value?: number }> = [];

      for (let day = 0; day < 7; day++) {
        if (currentDate <= endDate) {
          const dateKey = d3.timeFormat('%Y-%m-%d')(currentDate);
          week.push({
            date: new Date(currentDate),
            value: dataMap.get(dateKey),
          });
        }
        currentDate.setDate(currentDate.getDate() + 1);
      }

      result.push({ week: weekIndex, days: week });
      weekIndex++;
    }

    return result;
  }, [startDate, endDate, dataMap]);

  // Calculate month label positions
  const monthLabels = useMemo(() => {
    const labels: Array<{ month: string; x: number }> = [];
    let lastMonth = -1;

    weeks.forEach((week, weekIndex) => {
      const firstDay = week.days[0];
      if (firstDay) {
        const month = firstDay.date.getMonth();
        if (month !== lastMonth) {
          labels.push({
            month: MONTH_NAMES[month],
            x: weekIndex * (cellSize + cellGap),
          });
          lastMonth = month;
        }
      }
    });

    return labels;
  }, [weeks, cellSize, cellGap]);

  // Calculate dimensions
  const numWeeks = weeks.length;
  const chartWidth = numWeeks * (cellSize + cellGap);
  const chartHeight = 7 * (cellSize + cellGap);
  const marginLeft = showDayLabels ? 30 : 0;
  const marginTop = showMonthLabels ? 20 : 0;

  // Handle day hover
  const handleDayHover = useCallback(
    (date: Date, value: number | undefined, event: React.MouseEvent) => {
      const dateKey = d3.timeFormat('%Y-%m-%d')(date);
      setHoveredDate(dateKey);
      setTooltip({
        x: event.clientX,
        y: event.clientY,
        date,
        value: value ?? 0,
      });
      onDayHover?.(date, value ?? 0);
    },
    [onDayHover]
  );

  const handleMouseLeave = useCallback(() => {
    setHoveredDate(null);
    setTooltip(null);
    onDayHover?.(null, null);
  }, [onDayHover]);

  // Handle day click
  const handleDayClick = useCallback(
    (date: Date, value: number | undefined) => {
      onDayClick?.(date, value ?? 0);
    },
    [onDayClick]
  );

  return (
    <div className={cn('relative', className)}>
      <svg
        width={Math.max(width, chartWidth + marginLeft + 40)}
        height={chartHeight + marginTop + (showLegend ? 40 : 0)}
        className="overflow-visible"
      >
        <g transform={`translate(${marginLeft}, ${marginTop})`}>
          {/* Month labels */}
          {showMonthLabels && monthLabels.map(({ month, x }, i) => (
            <text
              key={`month-${i}`}
              x={x}
              y={-6}
              className="text-xs fill-muted-foreground"
            >
              {month}
            </text>
          ))}

          {/* Day labels */}
          {showDayLabels && [1, 3, 5].map((dayIndex) => (
            <text
              key={`day-${dayIndex}`}
              x={-8}
              y={dayIndex * (cellSize + cellGap) + cellSize / 2}
              textAnchor="end"
              dominantBaseline="middle"
              className="text-xs fill-muted-foreground"
            >
              {DAY_NAMES[dayIndex]}
            </text>
          ))}

          {/* Calendar cells */}
          {weeks.map((week, weekIndex) => (
            <g key={`week-${weekIndex}`} transform={`translate(${weekIndex * (cellSize + cellGap)}, 0)`}>
              {week.days.map((day, dayIndex) => {
                const dateKey = d3.timeFormat('%Y-%m-%d')(day.date);
                const isHovered = hoveredDate === dateKey;

                return (
                  <motion.rect
                    key={dateKey}
                    x={0}
                    y={dayIndex * (cellSize + cellGap)}
                    width={cellSize}
                    height={cellSize}
                    rx={2}
                    fill={getColor(day.value)}
                    stroke={isHovered ? 'hsl(var(--foreground))' : 'transparent'}
                    strokeWidth={isHovered ? 1.5 : 0}
                    initial={animated ? { opacity: 0, scale: 0 } : undefined}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{
                      duration: 0.2,
                      delay: animated ? (weekIndex * 7 + dayIndex) * 0.001 : 0,
                    }}
                    className="cursor-pointer"
                    onMouseEnter={(e) => handleDayHover(day.date, day.value, e)}
                    onMouseMove={(e) => {
                      if (tooltip) {
                        setTooltip((prev) => prev ? { ...prev, x: e.clientX, y: e.clientY } : null);
                      }
                    }}
                    onMouseLeave={handleMouseLeave}
                    onClick={() => handleDayClick(day.date, day.value)}
                  />
                );
              })}
            </g>
          ))}

          {/* Legend */}
          {showLegend && (
            <g transform={`translate(${chartWidth - 100}, ${chartHeight + 15})`}>
              <text x={-30} y={cellSize / 2} className="text-xs fill-muted-foreground" dominantBaseline="middle">
                Less
              </text>
              {colorScheme.map((color, i) => (
                <rect
                  key={`legend-${i}`}
                  x={i * (cellSize + 2)}
                  y={0}
                  width={cellSize}
                  height={cellSize}
                  rx={2}
                  fill={color}
                />
              ))}
              <text
                x={colorScheme.length * (cellSize + 2) + 5}
                y={cellSize / 2}
                className="text-xs fill-muted-foreground"
                dominantBaseline="middle"
              >
                More
              </text>
            </g>
          )}
        </g>
      </svg>

      {/* Tooltip */}
      <AnimatePresence>
        {tooltip && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            className="fixed z-50 px-3 py-2 bg-popover text-popover-foreground rounded-lg shadow-lg border text-sm pointer-events-none"
            style={{
              left: tooltip.x + 10,
              top: tooltip.y - 10,
            }}
          >
            <div className="font-medium">
              {d3.timeFormat('%B %d, %Y')(tooltip.date)}
            </div>
            <div className="text-muted-foreground">
              {valueFormatter(tooltip.value)}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// Helper to aggregate data by day
export function aggregateByDay(
  data: Array<{ date: Date | string; value: number }>,
  aggregation: 'sum' | 'mean' | 'max' | 'count' = 'sum'
): CalendarDay[] {
  const grouped = new Map<string, number[]>();

  data.forEach(({ date, value }) => {
    const d = typeof date === 'string' ? new Date(date) : date;
    const key = d3.timeFormat('%Y-%m-%d')(d);

    if (!grouped.has(key)) {
      grouped.set(key, []);
    }
    grouped.get(key)!.push(value);
  });

  return Array.from(grouped.entries()).map(([dateStr, values]) => {
    let aggregatedValue: number;

    switch (aggregation) {
      case 'sum':
        aggregatedValue = values.reduce((a, b) => a + b, 0);
        break;
      case 'mean':
        aggregatedValue = values.reduce((a, b) => a + b, 0) / values.length;
        break;
      case 'max':
        aggregatedValue = Math.max(...values);
        break;
      case 'count':
        aggregatedValue = values.length;
        break;
    }

    return {
      date: new Date(dateStr),
      value: aggregatedValue,
    };
  });
}

export default CalendarHeatmap;
