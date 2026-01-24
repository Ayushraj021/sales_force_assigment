/**
 * Chord Diagram Component
 *
 * Visualizes channel synergies and relationships between marketing channels
 * using D3.js chord layout.
 */

import { useRef, useEffect, useState, useMemo, useCallback } from 'react';
import * as d3 from 'd3';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';

// Types
interface ChordDataMatrix {
  names: string[];
  matrix: number[][];
  colors?: string[];
}

interface ChordDiagramProps {
  data: ChordDataMatrix;
  width?: number;
  height?: number;
  className?: string;
  colorScheme?: string[];
  innerRadiusRatio?: number;
  padAngle?: number;
  showLabels?: boolean;
  showValues?: boolean;
  animated?: boolean;
  onChordClick?: (source: string, target: string, value: number) => void;
  onGroupClick?: (name: string) => void;
  valueFormatter?: (value: number) => string;
}

interface TooltipData {
  x: number;
  y: number;
  type: 'group' | 'chord';
  content: {
    title: string;
    value?: number;
    percentage?: number;
    description?: string;
  };
}

// Default color scheme
const DEFAULT_COLORS = [
  '#6366f1', // Indigo
  '#22c55e', // Green
  '#f97316', // Orange
  '#ec4899', // Pink
  '#8b5cf6', // Violet
  '#14b8a6', // Teal
  '#f43f5e', // Rose
  '#eab308', // Yellow
  '#06b6d4', // Cyan
  '#3b82f6', // Blue
];

// Default value formatter
const defaultFormatter = (value: number): string => {
  if (value >= 1000000) {
    return `${(value / 1000000).toFixed(1)}M`;
  }
  if (value >= 1000) {
    return `${(value / 1000).toFixed(1)}K`;
  }
  return value.toFixed(0);
};

export function ChordDiagram({
  data,
  width = 600,
  height = 600,
  className,
  colorScheme = DEFAULT_COLORS,
  innerRadiusRatio = 0.9,
  padAngle = 0.04,
  showLabels = true,
  showValues = true,
  animated = true,
  onChordClick,
  onGroupClick,
  valueFormatter = defaultFormatter,
}: ChordDiagramProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [tooltip, setTooltip] = useState<TooltipData | null>(null);
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);

  // Calculate dimensions
  const outerRadius = Math.min(width, height) / 2 - 40;
  const innerRadius = outerRadius * innerRadiusRatio;

  // Color scale
  const colorScale = useMemo(() => {
    return d3.scaleOrdinal<number, string>()
      .domain(data.names.map((_, i) => i))
      .range(data.colors || colorScheme);
  }, [data.names, data.colors, colorScheme]);

  // Create chord layout
  const chord = useMemo(() => {
    return d3.chord()
      .padAngle(padAngle)
      .sortSubgroups(d3.descending)
      .sortChords(d3.descending);
  }, [padAngle]);

  // Generate chords from matrix
  const chords = useMemo(() => {
    try {
      return chord(data.matrix);
    } catch (error) {
      console.error('Chord layout error:', error);
      return null;
    }
  }, [chord, data.matrix]);

  // Arc generator for groups
  const arc = useMemo(() => {
    return d3.arc<d3.ChordGroup>()
      .innerRadius(innerRadius)
      .outerRadius(outerRadius);
  }, [innerRadius, outerRadius]);

  // Ribbon generator for chords
  const ribbon = useMemo(() => {
    return d3.ribbon<d3.Chord, d3.ChordSubgroup>()
      .radius(innerRadius);
  }, [innerRadius]);

  // Total value for percentage calculation
  const totalValue = useMemo(() => {
    return data.matrix.reduce((sum, row) => sum + row.reduce((s, v) => s + v, 0), 0);
  }, [data.matrix]);

  // Get group value (sum of outgoing)
  const getGroupValue = useCallback((index: number) => {
    return data.matrix[index].reduce((sum, v) => sum + v, 0);
  }, [data.matrix]);

  // Handle group hover
  const handleGroupHover = useCallback(
    (index: number, event: React.MouseEvent) => {
      setHoveredIndex(index);
      const value = getGroupValue(index);
      setTooltip({
        x: event.clientX,
        y: event.clientY,
        type: 'group',
        content: {
          title: data.names[index],
          value,
          percentage: (value / totalValue) * 100,
          description: `${data.matrix[index].filter((v) => v > 0).length} connections`,
        },
      });
    },
    [data.names, data.matrix, getGroupValue, totalValue]
  );

  // Handle chord hover
  const handleChordHover = useCallback(
    (chord: d3.Chord, event: React.MouseEvent) => {
      const sourceValue = chord.source.value;
      const targetValue = chord.target.value;

      setTooltip({
        x: event.clientX,
        y: event.clientY,
        type: 'chord',
        content: {
          title: `${data.names[chord.source.index]} ↔ ${data.names[chord.target.index]}`,
          value: sourceValue + targetValue,
          percentage: ((sourceValue + targetValue) / totalValue) * 100,
          description: `${data.names[chord.source.index]}: ${valueFormatter(sourceValue)}\n${data.names[chord.target.index]}: ${valueFormatter(targetValue)}`,
        },
      });
    },
    [data.names, totalValue, valueFormatter]
  );

  // Clear hover
  const handleMouseLeave = useCallback(() => {
    setHoveredIndex(null);
    setTooltip(null);
  }, []);

  // Handle group click
  const handleGroupClick = useCallback(
    (index: number) => {
      setSelectedIndex((prev) => (prev === index ? null : index));
      onGroupClick?.(data.names[index]);
    },
    [data.names, onGroupClick]
  );

  // Handle chord click
  const handleChordClick = useCallback(
    (chord: d3.Chord) => {
      onChordClick?.(
        data.names[chord.source.index],
        data.names[chord.target.index],
        chord.source.value + chord.target.value
      );
    },
    [data.names, onChordClick]
  );

  if (!chords) {
    return (
      <div className={cn('flex items-center justify-center', className)} style={{ width, height }}>
        <p className="text-muted-foreground">Unable to render chord diagram</p>
      </div>
    );
  }

  return (
    <div className={cn('relative', className)}>
      <svg
        ref={svgRef}
        width={width}
        height={height}
        className="overflow-visible"
      >
        <g transform={`translate(${width / 2}, ${height / 2})`}>
          {/* Groups (arcs) */}
          <g className="groups">
            {chords.groups.map((group, i) => {
              const isHovered = hoveredIndex === i;
              const isSelected = selectedIndex === i;
              const opacity = hoveredIndex !== null && !isHovered
                ? 0.3
                : selectedIndex !== null && !isSelected
                  ? 0.3
                  : 1;

              return (
                <g key={`group-${i}`}>
                  <motion.path
                    d={arc(group) || ''}
                    fill={colorScale(i)}
                    fillOpacity={opacity}
                    stroke={isHovered || isSelected ? 'hsl(var(--foreground))' : 'hsl(var(--background))'}
                    strokeWidth={isHovered || isSelected ? 2 : 1}
                    initial={animated ? { opacity: 0 } : undefined}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.5, delay: i * 0.05 }}
                    className="cursor-pointer transition-all duration-200"
                    onMouseEnter={(e) => handleGroupHover(i, e)}
                    onMouseLeave={handleMouseLeave}
                    onClick={() => handleGroupClick(i)}
                  />

                  {/* Labels */}
                  {showLabels && (
                    <motion.g
                      initial={animated ? { opacity: 0 } : undefined}
                      animate={{ opacity: 1 }}
                      transition={{ duration: 0.3, delay: 0.5 }}
                    >
                      <text
                        transform={(() => {
                          const angle = (group.startAngle + group.endAngle) / 2;
                          const rotate = (angle * 180) / Math.PI - 90;
                          const flip = angle > Math.PI;
                          return `rotate(${rotate}) translate(${outerRadius + 10}) ${flip ? 'rotate(180)' : ''}`;
                        })()}
                        textAnchor={(() => {
                          const angle = (group.startAngle + group.endAngle) / 2;
                          return angle > Math.PI ? 'end' : 'start';
                        })()}
                        dominantBaseline="middle"
                        className="text-xs fill-foreground pointer-events-none"
                        style={{ opacity }}
                      >
                        {data.names[i]}
                      </text>
                    </motion.g>
                  )}
                </g>
              );
            })}
          </g>

          {/* Chords (ribbons) */}
          <g className="chords">
            {chords.map((chord, i) => {
              const sourceIndex = chord.source.index;
              const targetIndex = chord.target.index;
              const isConnectedToHovered =
                hoveredIndex !== null &&
                (sourceIndex === hoveredIndex || targetIndex === hoveredIndex);
              const isConnectedToSelected =
                selectedIndex !== null &&
                (sourceIndex === selectedIndex || targetIndex === selectedIndex);

              const opacity =
                hoveredIndex !== null
                  ? isConnectedToHovered
                    ? 0.7
                    : 0.1
                  : selectedIndex !== null
                    ? isConnectedToSelected
                      ? 0.7
                      : 0.1
                    : 0.4;

              return (
                <motion.path
                  key={`chord-${i}`}
                  d={ribbon(chord) || ''}
                  fill={colorScale(sourceIndex)}
                  fillOpacity={opacity}
                  stroke={isConnectedToHovered ? 'hsl(var(--foreground) / 0.3)' : 'none'}
                  initial={animated ? { opacity: 0, pathLength: 0 } : undefined}
                  animate={{ opacity: 1, pathLength: 1 }}
                  transition={{ duration: 0.8, delay: 0.3 + i * 0.02 }}
                  className="cursor-pointer transition-opacity duration-200"
                  onMouseEnter={(e) => handleChordHover(chord, e)}
                  onMouseLeave={handleMouseLeave}
                  onClick={() => handleChordClick(chord)}
                />
              );
            })}
          </g>
        </g>
      </svg>

      {/* Legend */}
      <div className="absolute bottom-4 left-4 bg-background/80 backdrop-blur-sm rounded-lg p-3 shadow-sm border">
        <div className="text-xs font-medium mb-2">Channels</div>
        <div className="grid grid-cols-2 gap-x-4 gap-y-1">
          {data.names.map((name, i) => (
            <button
              key={name}
              onClick={() => handleGroupClick(i)}
              className={cn(
                'flex items-center gap-2 text-left transition-opacity',
                selectedIndex !== null && selectedIndex !== i && 'opacity-40'
              )}
            >
              <div
                className="w-3 h-3 rounded-sm"
                style={{ backgroundColor: colorScale(i) }}
              />
              <span className="text-xs text-foreground">{name}</span>
            </button>
          ))}
        </div>
        {selectedIndex !== null && (
          <button
            onClick={() => setSelectedIndex(null)}
            className="mt-2 text-xs text-primary hover:underline"
          >
            Clear selection
          </button>
        )}
      </div>

      {/* Summary stats */}
      {showValues && (
        <div className="absolute top-4 right-4 bg-background/80 backdrop-blur-sm rounded-lg p-3 shadow-sm border">
          <div className="text-xs font-medium mb-1">Total Flow</div>
          <div className="text-lg font-semibold">{valueFormatter(totalValue)}</div>
          <div className="text-xs text-muted-foreground mt-1">
            {data.names.length} channels
          </div>
        </div>
      )}

      {/* Tooltip */}
      <AnimatePresence>
        {tooltip && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            className="fixed z-50 px-3 py-2 bg-popover text-popover-foreground rounded-lg shadow-lg border text-sm pointer-events-none max-w-xs"
            style={{
              left: tooltip.x + 10,
              top: tooltip.y - 10,
            }}
          >
            <div className="font-medium">{tooltip.content.title}</div>
            {tooltip.content.value !== undefined && (
              <div className="text-muted-foreground">
                Value: {valueFormatter(tooltip.content.value)}
              </div>
            )}
            {tooltip.content.percentage !== undefined && (
              <div className="text-muted-foreground">
                {tooltip.content.percentage.toFixed(1)}% of total
              </div>
            )}
            {tooltip.content.description && (
              <div className="text-xs text-muted-foreground mt-1 whitespace-pre-line">
                {tooltip.content.description}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// Helper to create synergy matrix from channel interactions
export function createSynergyMatrix(
  interactions: Array<{
    channelA: string;
    channelB: string;
    synergy: number;
  }>
): ChordDataMatrix {
  // Get unique channels
  const channels = [...new Set(
    interactions.flatMap((i) => [i.channelA, i.channelB])
  )].sort();

  const n = channels.length;
  const channelIndex = new Map(channels.map((c, i) => [c, i]));

  // Initialize matrix
  const matrix: number[][] = Array.from({ length: n }, () => Array(n).fill(0));

  // Fill matrix
  interactions.forEach(({ channelA, channelB, synergy }) => {
    const i = channelIndex.get(channelA);
    const j = channelIndex.get(channelB);
    if (i !== undefined && j !== undefined) {
      matrix[i][j] = synergy;
      matrix[j][i] = synergy; // Symmetric
    }
  });

  return {
    names: channels,
    matrix,
  };
}

// Helper to create flow matrix from journey transitions
export function createFlowMatrix(
  transitions: Array<{
    from: string;
    to: string;
    count: number;
  }>
): ChordDataMatrix {
  // Get unique channels
  const channels = [...new Set(
    transitions.flatMap((t) => [t.from, t.to])
  )].sort();

  const n = channels.length;
  const channelIndex = new Map(channels.map((c, i) => [c, i]));

  // Initialize matrix
  const matrix: number[][] = Array.from({ length: n }, () => Array(n).fill(0));

  // Fill matrix (asymmetric - directional flow)
  transitions.forEach(({ from, to, count }) => {
    const i = channelIndex.get(from);
    const j = channelIndex.get(to);
    if (i !== undefined && j !== undefined) {
      matrix[i][j] = count;
    }
  });

  return {
    names: channels,
    matrix,
  };
}

export default ChordDiagram;
