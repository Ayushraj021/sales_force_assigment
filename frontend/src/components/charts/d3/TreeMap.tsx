/**
 * TreeMap Component
 *
 * Visualizes hierarchical budget allocation and category breakdowns
 * using D3.js treemap layout with interactive drill-down.
 */

import { useRef, useEffect, useState, useMemo, useCallback } from 'react';
import * as d3 from 'd3';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';

// Types
interface TreeMapNode {
  name: string;
  value?: number;
  children?: TreeMapNode[];
  color?: string;
  metadata?: Record<string, any>;
}

interface TreeMapProps {
  data: TreeMapNode;
  width?: number;
  height?: number;
  className?: string;
  colorScheme?: string[];
  showLabels?: boolean;
  showValues?: boolean;
  enableDrillDown?: boolean;
  padding?: number;
  borderRadius?: number;
  onNodeClick?: (node: TreeMapNode, path: string[]) => void;
  onNodeHover?: (node: TreeMapNode | null) => void;
  valueFormatter?: (value: number) => string;
}

interface TooltipData {
  x: number;
  y: number;
  node: TreeMapNode;
  percentage: number;
  path: string[];
}

// Default color scheme
const DEFAULT_COLORS = [
  '#6366f1', // Indigo
  '#8b5cf6', // Violet
  '#ec4899', // Pink
  '#f43f5e', // Rose
  '#f97316', // Orange
  '#eab308', // Yellow
  '#22c55e', // Green
  '#14b8a6', // Teal
  '#06b6d4', // Cyan
  '#3b82f6', // Blue
];

// Default value formatter
const defaultFormatter = (value: number): string => {
  if (value >= 1000000) {
    return `$${(value / 1000000).toFixed(1)}M`;
  }
  if (value >= 1000) {
    return `$${(value / 1000).toFixed(1)}K`;
  }
  return `$${value.toFixed(0)}`;
};

export function TreeMap({
  data,
  width = 800,
  height = 500,
  className,
  colorScheme = DEFAULT_COLORS,
  showLabels = true,
  showValues = true,
  enableDrillDown = true,
  padding = 2,
  borderRadius = 4,
  onNodeClick,
  onNodeHover,
  valueFormatter = defaultFormatter,
}: TreeMapProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [tooltip, setTooltip] = useState<TooltipData | null>(null);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [currentRoot, setCurrentRoot] = useState<TreeMapNode>(data);
  const [breadcrumb, setBreadcrumb] = useState<string[]>([data.name]);

  // Reset when data changes
  useEffect(() => {
    setCurrentRoot(data);
    setBreadcrumb([data.name]);
  }, [data]);

  // Create hierarchical structure
  const hierarchy = useMemo(() => {
    return d3.hierarchy(currentRoot)
      .sum((d) => d.value || 0)
      .sort((a, b) => (b.value || 0) - (a.value || 0));
  }, [currentRoot]);

  // Create treemap layout
  const treemapLayout = useMemo(() => {
    return d3.treemap<TreeMapNode>()
      .size([width, height])
      .paddingOuter(padding)
      .paddingInner(padding)
      .round(true);
  }, [width, height, padding]);

  // Apply layout
  const root = useMemo(() => {
    return treemapLayout(hierarchy);
  }, [treemapLayout, hierarchy]);

  // Color scale
  const colorScale = useMemo(() => {
    const leaves = hierarchy.leaves();
    const categories = [...new Set(leaves.map((d) => d.parent?.data.name || d.data.name))];
    return d3.scaleOrdinal<string>()
      .domain(categories)
      .range(colorScheme);
  }, [hierarchy, colorScheme]);

  // Get node color
  const getNodeColor = useCallback((node: d3.HierarchyRectangularNode<TreeMapNode>) => {
    if (node.data.color) return node.data.color;
    // Use parent category for color consistency
    const category = node.parent?.data.name || node.data.name;
    return colorScale(category);
  }, [colorScale]);

  // Calculate total value
  const totalValue = useMemo(() => root.value || 1, [root]);

  // Handle node click (drill down)
  const handleNodeClick = useCallback((node: d3.HierarchyRectangularNode<TreeMapNode>) => {
    if (enableDrillDown && node.data.children && node.data.children.length > 0) {
      setCurrentRoot(node.data);
      setBreadcrumb((prev) => [...prev, node.data.name]);
    }

    onNodeClick?.(node.data, [...breadcrumb, node.data.name]);
  }, [enableDrillDown, breadcrumb, onNodeClick]);

  // Handle breadcrumb navigation
  const navigateToBreadcrumb = useCallback((index: number) => {
    if (index === 0) {
      setCurrentRoot(data);
      setBreadcrumb([data.name]);
    } else {
      // Navigate up the hierarchy
      let current = data;
      const newPath = breadcrumb.slice(0, index + 1);

      for (let i = 1; i <= index; i++) {
        const child = current.children?.find((c) => c.name === breadcrumb[i]);
        if (child) {
          current = child;
        }
      }

      setCurrentRoot(current);
      setBreadcrumb(newPath);
    }
  }, [data, breadcrumb]);

  // Handle hover
  const handleNodeHover = useCallback(
    (node: d3.HierarchyRectangularNode<TreeMapNode> | null, event?: React.MouseEvent) => {
      if (node && event) {
        setHoveredNode(node.data.name);
        setTooltip({
          x: event.clientX,
          y: event.clientY,
          node: node.data,
          percentage: ((node.value || 0) / totalValue) * 100,
          path: [...breadcrumb, node.data.name],
        });
        onNodeHover?.(node.data);
      } else {
        setHoveredNode(null);
        setTooltip(null);
        onNodeHover?.(null);
      }
    },
    [totalValue, breadcrumb, onNodeHover]
  );

  // Get all leaf nodes for rendering
  const leaves = useMemo(() => root.leaves(), [root]);

  return (
    <div className={cn('relative', className)}>
      {/* Breadcrumb navigation */}
      {enableDrillDown && breadcrumb.length > 1 && (
        <div className="flex items-center gap-1 mb-3 text-sm">
          {breadcrumb.map((name, index) => (
            <span key={index} className="flex items-center">
              {index > 0 && <span className="mx-1 text-muted-foreground">/</span>}
              <button
                onClick={() => navigateToBreadcrumb(index)}
                className={cn(
                  'hover:text-primary transition-colors',
                  index === breadcrumb.length - 1
                    ? 'text-foreground font-medium'
                    : 'text-muted-foreground'
                )}
              >
                {name}
              </button>
            </span>
          ))}
        </div>
      )}

      <svg
        ref={svgRef}
        width={width}
        height={height}
        className="overflow-visible"
      >
        <g>
          {leaves.map((node, i) => {
            const nodeWidth = node.x1 - node.x0;
            const nodeHeight = node.y1 - node.y0;
            const isHovered = hoveredNode === node.data.name;
            const hasChildren = node.data.children && node.data.children.length > 0;
            const canShowLabel = nodeWidth > 40 && nodeHeight > 25;
            const canShowValue = nodeWidth > 60 && nodeHeight > 40;

            return (
              <motion.g
                key={`${node.data.name}-${i}`}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.3, delay: i * 0.02 }}
              >
                <motion.rect
                  x={node.x0}
                  y={node.y0}
                  width={nodeWidth}
                  height={nodeHeight}
                  rx={borderRadius}
                  fill={getNodeColor(node)}
                  fillOpacity={isHovered ? 1 : 0.85}
                  stroke={isHovered ? 'hsl(var(--primary))' : 'hsl(var(--background))'}
                  strokeWidth={isHovered ? 2 : 1}
                  className={cn(
                    'transition-all duration-200',
                    hasChildren && enableDrillDown && 'cursor-zoom-in'
                  )}
                  onMouseEnter={(e) => handleNodeHover(node, e)}
                  onMouseMove={(e) => {
                    if (tooltip) {
                      setTooltip((prev) =>
                        prev ? { ...prev, x: e.clientX, y: e.clientY } : null
                      );
                    }
                  }}
                  onMouseLeave={() => handleNodeHover(null)}
                  onClick={() => handleNodeClick(node)}
                  whileHover={{ scale: 1.01 }}
                  whileTap={{ scale: 0.99 }}
                />

                {/* Label */}
                {showLabels && canShowLabel && (
                  <motion.text
                    x={node.x0 + nodeWidth / 2}
                    y={node.y0 + (canShowValue ? nodeHeight / 2 - 8 : nodeHeight / 2)}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    className="fill-white text-xs font-medium pointer-events-none"
                    style={{
                      textShadow: '0 1px 2px rgba(0,0,0,0.3)',
                      fontSize: Math.min(12, nodeWidth / node.data.name.length * 1.5),
                    }}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.2 }}
                  >
                    {nodeWidth < 80 && node.data.name.length > 8
                      ? `${node.data.name.substring(0, 8)}...`
                      : node.data.name}
                  </motion.text>
                )}

                {/* Value */}
                {showValues && canShowValue && (
                  <motion.text
                    x={node.x0 + nodeWidth / 2}
                    y={node.y0 + nodeHeight / 2 + 10}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    className="fill-white/80 text-xs pointer-events-none"
                    style={{ textShadow: '0 1px 2px rgba(0,0,0,0.3)' }}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.3 }}
                  >
                    {valueFormatter(node.value || 0)}
                  </motion.text>
                )}

                {/* Drill-down indicator */}
                {hasChildren && enableDrillDown && nodeWidth > 30 && nodeHeight > 30 && (
                  <motion.text
                    x={node.x1 - 12}
                    y={node.y0 + 12}
                    className="fill-white/60 text-xs pointer-events-none"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                  >
                    +
                  </motion.text>
                )}
              </motion.g>
            );
          })}
        </g>
      </svg>

      {/* Legend */}
      <div className="flex flex-wrap gap-3 mt-4">
        {[...new Set(leaves.map((l) => l.parent?.data.name || l.data.name))].map((category) => (
          <div key={category} className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded"
              style={{ backgroundColor: colorScale(category) }}
            />
            <span className="text-xs text-muted-foreground">{category}</span>
          </div>
        ))}
      </div>

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
            <div className="font-medium">{tooltip.node.name}</div>
            <div className="text-muted-foreground">
              {valueFormatter(tooltip.node.value || 0)}
            </div>
            <div className="text-muted-foreground">
              {tooltip.percentage.toFixed(1)}% of total
            </div>
            {tooltip.node.children && tooltip.node.children.length > 0 && (
              <div className="text-xs text-primary mt-1">
                Click to expand ({tooltip.node.children.length} items)
              </div>
            )}
            {tooltip.node.metadata && Object.keys(tooltip.node.metadata).length > 0 && (
              <div className="mt-2 pt-2 border-t border-border">
                {Object.entries(tooltip.node.metadata).map(([key, value]) => (
                  <div key={key} className="text-xs text-muted-foreground">
                    {key}: {typeof value === 'number' ? value.toLocaleString() : value}
                  </div>
                ))}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// Helper to create budget allocation data
export function createBudgetTreeData(
  allocations: Array<{
    channel: string;
    subchannel?: string;
    budget: number;
    roi?: number;
  }>
): TreeMapNode {
  const channelMap = new Map<string, TreeMapNode>();

  allocations.forEach(({ channel, subchannel, budget, roi }) => {
    if (!channelMap.has(channel)) {
      channelMap.set(channel, {
        name: channel,
        children: [],
      });
    }

    const channelNode = channelMap.get(channel)!;

    if (subchannel) {
      channelNode.children?.push({
        name: subchannel,
        value: budget,
        metadata: roi !== undefined ? { ROI: `${roi.toFixed(1)}x` } : undefined,
      });
    } else {
      channelNode.value = (channelNode.value || 0) + budget;
      if (roi !== undefined) {
        channelNode.metadata = { ...channelNode.metadata, ROI: `${roi.toFixed(1)}x` };
      }
    }
  });

  return {
    name: 'Total Budget',
    children: Array.from(channelMap.values()),
  };
}

export default TreeMap;
