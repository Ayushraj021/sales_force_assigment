/**
 * Heatmap Component
 *
 * Visualizes correlation matrices, performance metrics, and 2D data distributions.
 * Supports interactive features like tooltips, cell selection, and annotations.
 */

import { useMemo, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import * as d3 from 'd3';
import { cn } from '@/lib/utils';

// Types
interface HeatmapCell {
  row: number;
  col: number;
  value: number;
  label?: string;
}

interface HeatmapData {
  rows: string[];
  cols: string[];
  values: number[][];
}

interface HeatmapProps {
  data: HeatmapData;
  width?: number;
  height?: number;
  className?: string;
  colorScale?: 'sequential' | 'diverging' | 'categorical';
  colorScheme?: string[];
  minValue?: number;
  maxValue?: number;
  showLabels?: boolean;
  showValues?: boolean;
  showLegend?: boolean;
  cellBorderRadius?: number;
  cellPadding?: number;
  animated?: boolean;
  onCellClick?: (row: string, col: string, value: number) => void;
  onCellHover?: (row: string | null, col: string | null, value: number | null) => void;
  valueFormatter?: (value: number) => string;
  annotationThreshold?: number;
}

interface TooltipData {
  x: number;
  y: number;
  row: string;
  col: string;
  value: number;
}

// Default color schemes
const SEQUENTIAL_COLORS = ['#f0f9ff', '#bae6fd', '#7dd3fc', '#38bdf8', '#0ea5e9', '#0284c7', '#0369a1'];
const DIVERGING_COLORS = ['#ef4444', '#fca5a5', '#fef2f2', '#f0fdf4', '#86efac', '#22c55e'];

export function Heatmap({
  data,
  width = 600,
  height = 400,
  className,
  colorScale = 'sequential',
  colorScheme,
  minValue: propMinValue,
  maxValue: propMaxValue,
  showLabels = true,
  showValues = false,
  showLegend = true,
  cellBorderRadius = 2,
  cellPadding = 1,
  animated = true,
  onCellClick,
  onCellHover,
  valueFormatter = (v) => v.toFixed(2),
  annotationThreshold,
}: HeatmapProps) {
  const [tooltip, setTooltip] = useState<TooltipData | null>(null);
  const [hoveredCell, setHoveredCell] = useState<{ row: number; col: number } | null>(null);

  // Calculate margins
  const margin = {
    top: 20,
    right: showLegend ? 60 : 20,
    bottom: showLabels ? 80 : 20,
    left: showLabels ? 100 : 20,
  };

  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;

  // Flatten values for min/max calculation
  const allValues = useMemo(() => data.values.flat(), [data.values]);
  const minValue = propMinValue ?? Math.min(...allValues);
  const maxValue = propMaxValue ?? Math.max(...allValues);

  // Create color scale
  const getColorScale = useMemo(() => {
    const colors = colorScheme || (colorScale === 'diverging' ? DIVERGING_COLORS : SEQUENTIAL_COLORS);

    if (colorScale === 'diverging') {
      return d3.scaleDiverging<string>()
        .domain([minValue, 0, maxValue])
        .interpolator(d3.interpolateRgbBasis(colors));
    }

    return d3.scaleSequential<string>()
      .domain([minValue, maxValue])
      .interpolator(d3.interpolateRgbBasis(colors));
  }, [colorScale, colorScheme, minValue, maxValue]);

  // Cell dimensions
  const cellWidth = innerWidth / data.cols.length - cellPadding * 2;
  const cellHeight = innerHeight / data.rows.length - cellPadding * 2;

  // Generate cells
  const cells = useMemo(() => {
    const result: HeatmapCell[] = [];
    data.values.forEach((row, i) => {
      row.forEach((value, j) => {
        result.push({ row: i, col: j, value });
      });
    });
    return result;
  }, [data.values]);

  // Handle cell hover
  const handleCellHover = useCallback(
    (cell: HeatmapCell | null, event?: React.MouseEvent) => {
      if (cell && event) {
        setHoveredCell({ row: cell.row, col: cell.col });
        setTooltip({
          x: event.clientX,
          y: event.clientY,
          row: data.rows[cell.row],
          col: data.cols[cell.col],
          value: cell.value,
        });
        onCellHover?.(data.rows[cell.row], data.cols[cell.col], cell.value);
      } else {
        setHoveredCell(null);
        setTooltip(null);
        onCellHover?.(null, null, null);
      }
    },
    [data.rows, data.cols, onCellHover]
  );

  // Handle cell click
  const handleCellClick = useCallback(
    (cell: HeatmapCell) => {
      onCellClick?.(data.rows[cell.row], data.cols[cell.col], cell.value);
    },
    [data.rows, data.cols, onCellClick]
  );

  return (
    <div className={cn('relative', className)}>
      <svg width={width} height={height} className="overflow-visible">
        <g transform={`translate(${margin.left}, ${margin.top})`}>
          {/* Row labels */}
          {showLabels && data.rows.map((label, i) => (
            <text
              key={`row-${i}`}
              x={-8}
              y={i * (cellHeight + cellPadding * 2) + cellHeight / 2}
              textAnchor="end"
              dominantBaseline="middle"
              className={cn(
                'text-xs fill-muted-foreground transition-opacity',
                hoveredCell && hoveredCell.row !== i && 'opacity-40'
              )}
            >
              {label.length > 12 ? `${label.slice(0, 12)}...` : label}
            </text>
          ))}

          {/* Column labels */}
          {showLabels && data.cols.map((label, i) => (
            <text
              key={`col-${i}`}
              x={i * (cellWidth + cellPadding * 2) + cellWidth / 2}
              y={innerHeight + 12}
              textAnchor="start"
              transform={`rotate(45, ${i * (cellWidth + cellPadding * 2) + cellWidth / 2}, ${innerHeight + 12})`}
              className={cn(
                'text-xs fill-muted-foreground transition-opacity',
                hoveredCell && hoveredCell.col !== i && 'opacity-40'
              )}
            >
              {label.length > 12 ? `${label.slice(0, 12)}...` : label}
            </text>
          ))}

          {/* Cells */}
          {cells.map((cell, i) => {
            const x = cell.col * (cellWidth + cellPadding * 2) + cellPadding;
            const y = cell.row * (cellHeight + cellPadding * 2) + cellPadding;
            const isHovered = hoveredCell?.row === cell.row || hoveredCell?.col === cell.col;
            const isExactHover = hoveredCell?.row === cell.row && hoveredCell?.col === cell.col;
            const showAnnotation = annotationThreshold !== undefined && Math.abs(cell.value) >= annotationThreshold;

            return (
              <g key={`cell-${cell.row}-${cell.col}`}>
                <motion.rect
                  x={x}
                  y={y}
                  width={cellWidth}
                  height={cellHeight}
                  rx={cellBorderRadius}
                  fill={getColorScale(cell.value)}
                  stroke={isExactHover ? 'hsl(var(--foreground))' : 'transparent'}
                  strokeWidth={isExactHover ? 2 : 0}
                  initial={animated ? { opacity: 0, scale: 0.8 } : undefined}
                  animate={{ opacity: isHovered ? 1 : 0.9, scale: 1 }}
                  transition={{ duration: 0.3, delay: animated ? i * 0.005 : 0 }}
                  className="cursor-pointer"
                  onMouseEnter={(e) => handleCellHover(cell, e)}
                  onMouseMove={(e) => {
                    if (tooltip) {
                      setTooltip((prev) => prev ? { ...prev, x: e.clientX, y: e.clientY } : null);
                    }
                  }}
                  onMouseLeave={() => handleCellHover(null)}
                  onClick={() => handleCellClick(cell)}
                />

                {/* Cell value */}
                {(showValues || showAnnotation) && (
                  <motion.text
                    x={x + cellWidth / 2}
                    y={y + cellHeight / 2}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    className={cn(
                      'text-xs pointer-events-none',
                      cell.value > (maxValue - minValue) / 2 + minValue
                        ? 'fill-white'
                        : 'fill-foreground'
                    )}
                    initial={animated ? { opacity: 0 } : undefined}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.3 }}
                  >
                    {valueFormatter(cell.value)}
                  </motion.text>
                )}
              </g>
            );
          })}

          {/* Legend */}
          {showLegend && (
            <g transform={`translate(${innerWidth + 10}, 0)`}>
              <defs>
                <linearGradient id="heatmap-gradient" x1="0%" y1="100%" x2="0%" y2="0%">
                  {[0, 0.25, 0.5, 0.75, 1].map((stop) => (
                    <stop
                      key={stop}
                      offset={`${stop * 100}%`}
                      stopColor={getColorScale(minValue + (maxValue - minValue) * stop)}
                    />
                  ))}
                </linearGradient>
              </defs>
              <rect
                x={0}
                y={0}
                width={15}
                height={innerHeight}
                fill="url(#heatmap-gradient)"
                rx={2}
              />
              <text
                x={20}
                y={0}
                className="text-xs fill-muted-foreground"
                dominantBaseline="hanging"
              >
                {valueFormatter(maxValue)}
              </text>
              <text
                x={20}
                y={innerHeight}
                className="text-xs fill-muted-foreground"
                dominantBaseline="auto"
              >
                {valueFormatter(minValue)}
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
            <div className="font-medium">{tooltip.row} × {tooltip.col}</div>
            <div className="text-muted-foreground">
              Value: {valueFormatter(tooltip.value)}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// Helper to create correlation matrix data
export function createCorrelationMatrix(
  data: Record<string, number[]>
): HeatmapData {
  const variables = Object.keys(data);
  const n = variables.length;
  const values: number[][] = [];

  for (let i = 0; i < n; i++) {
    const row: number[] = [];
    for (let j = 0; j < n; j++) {
      if (i === j) {
        row.push(1);
      } else {
        const correlation = calculateCorrelation(
          data[variables[i]],
          data[variables[j]]
        );
        row.push(correlation);
      }
    }
    values.push(row);
  }

  return {
    rows: variables,
    cols: variables,
    values,
  };
}

function calculateCorrelation(x: number[], y: number[]): number {
  const n = Math.min(x.length, y.length);
  if (n === 0) return 0;

  const meanX = x.reduce((a, b) => a + b, 0) / n;
  const meanY = y.reduce((a, b) => a + b, 0) / n;

  let numerator = 0;
  let denomX = 0;
  let denomY = 0;

  for (let i = 0; i < n; i++) {
    const dx = x[i] - meanX;
    const dy = y[i] - meanY;
    numerator += dx * dy;
    denomX += dx * dx;
    denomY += dy * dy;
  }

  const denom = Math.sqrt(denomX * denomY);
  return denom === 0 ? 0 : numerator / denom;
}

export default Heatmap;
