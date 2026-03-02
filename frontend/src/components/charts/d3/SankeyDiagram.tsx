/**
 * Sankey Diagram Component
 *
 * Visualizes customer journeys and channel flows using D3.js Sankey layout.
 * Shows how customers move through marketing channels toward conversion.
 */

import { useRef, useEffect, useMemo, useState } from 'react';
import * as d3 from 'd3';
import { sankey, sankeyLinkHorizontal, SankeyGraph, SankeyNode, SankeyLink } from 'd3-sankey';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';

// Types
interface SankeyNodeData {
  id: string;
  name: string;
  category?: string;
  value?: number;
  color?: string;
}

interface SankeyLinkData {
  source: string;
  target: string;
  value: number;
}

interface SankeyDiagramProps {
  nodes: SankeyNodeData[];
  links: SankeyLinkData[];
  width?: number;
  height?: number;
  nodeWidth?: number;
  nodePadding?: number;
  className?: string;
  colorScheme?: string[];
  showValues?: boolean;
  showTooltip?: boolean;
  animated?: boolean;
  onNodeClick?: (node: SankeyNodeData) => void;
  onLinkClick?: (link: SankeyLinkData) => void;
}

interface TooltipData {
  x: number;
  y: number;
  content: {
    title: string;
    value?: number;
    percentage?: number;
    details?: string;
  };
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

// Category-based colors
const CATEGORY_COLORS: Record<string, string> = {
  paid: '#6366f1',
  organic: '#22c55e',
  social: '#ec4899',
  email: '#f97316',
  direct: '#3b82f6',
  referral: '#8b5cf6',
  conversion: '#10b981',
  exit: '#ef4444',
};

export function SankeyDiagram({
  nodes,
  links,
  width = 800,
  height = 500,
  nodeWidth = 20,
  nodePadding = 15,
  className,
  colorScheme = DEFAULT_COLORS,
  showValues = true,
  showTooltip = true,
  animated = true,
  onNodeClick,
  onLinkClick,
}: SankeyDiagramProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [tooltip, setTooltip] = useState<TooltipData | null>(null);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [hoveredLink, setHoveredLink] = useState<string | null>(null);

  // Margins
  const margin = { top: 20, right: 120, bottom: 20, left: 20 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;

  // Build node index map
  const nodeMap = useMemo(() => {
    const map = new Map<string, number>();
    nodes.forEach((node, i) => map.set(node.id, i));
    return map;
  }, [nodes]);

  // Prepare sankey data
  const sankeyData = useMemo(() => {
    // Create sankey generator
    const sankeyGenerator = sankey<SankeyNodeData, SankeyLinkData>()
      .nodeId((d) => d.id)
      .nodeWidth(nodeWidth)
      .nodePadding(nodePadding)
      .extent([[0, 0], [innerWidth, innerHeight]]);

    // Process nodes and links
    const graph: SankeyGraph<SankeyNodeData, SankeyLinkData> = {
      nodes: nodes.map((n) => ({ ...n })),
      links: links.map((l) => ({
        ...l,
        source: l.source,
        target: l.target,
      })),
    };

    try {
      return sankeyGenerator(graph as any);
    } catch (error) {
      console.error('Sankey layout error:', error);
      return null;
    }
  }, [nodes, links, innerWidth, innerHeight, nodeWidth, nodePadding]);

  // Color scale
  const colorScale = useMemo(() => {
    return d3.scaleOrdinal<string>()
      .domain(nodes.map((n) => n.category || n.id))
      .range(colorScheme);
  }, [nodes, colorScheme]);

  // Get node color
  const getNodeColor = (node: SankeyNodeData) => {
    if (node.color) return node.color;
    if (node.category && CATEGORY_COLORS[node.category]) {
      return CATEGORY_COLORS[node.category];
    }
    return colorScale(node.category || node.id);
  };

  // Get link color (gradient between source and target)
  const getLinkColor = (link: any) => {
    const sourceColor = getNodeColor(link.source);
    return d3.color(sourceColor)?.copy({ opacity: 0.4 })?.toString() || 'rgba(100, 100, 100, 0.4)';
  };

  // Total flow for percentage calculations
  const totalFlow = useMemo(() => {
    return links.reduce((sum, l) => sum + l.value, 0);
  }, [links]);

  // Handle node hover
  const handleNodeHover = (node: any, event: React.MouseEvent) => {
    if (!showTooltip) return;

    setHoveredNode(node.id);

    // Calculate incoming and outgoing values
    const incoming = (sankeyData?.links || [])
      .filter((l: any) => l.target.id === node.id)
      .reduce((sum: number, l: any) => sum + l.value, 0);

    const outgoing = (sankeyData?.links || [])
      .filter((l: any) => l.source.id === node.id)
      .reduce((sum: number, l: any) => sum + l.value, 0);

    setTooltip({
      x: event.clientX,
      y: event.clientY,
      content: {
        title: node.name,
        value: node.value || Math.max(incoming, outgoing),
        percentage: ((node.value || Math.max(incoming, outgoing)) / totalFlow) * 100,
        details: `In: ${incoming.toLocaleString()} | Out: ${outgoing.toLocaleString()}`,
      },
    });
  };

  // Handle link hover
  const handleLinkHover = (link: any, event: React.MouseEvent) => {
    if (!showTooltip) return;

    setHoveredLink(`${link.source.id}-${link.target.id}`);

    setTooltip({
      x: event.clientX,
      y: event.clientY,
      content: {
        title: `${link.source.name} → ${link.target.name}`,
        value: link.value,
        percentage: (link.value / totalFlow) * 100,
      },
    });
  };

  // Clear hover state
  const handleMouseLeave = () => {
    setHoveredNode(null);
    setHoveredLink(null);
    setTooltip(null);
  };

  if (!sankeyData) {
    return (
      <div className={cn('flex items-center justify-center', className)} style={{ width, height }}>
        <p className="text-muted-foreground">Unable to render Sankey diagram</p>
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
        <g transform={`translate(${margin.left}, ${margin.top})`}>
          {/* Links */}
          <g className="sankey-links">
            {sankeyData.links.map((link: any, i) => {
              const linkId = `${link.source.id}-${link.target.id}`;
              const isHovered = hoveredLink === linkId;
              const isConnected = hoveredNode === link.source.id || hoveredNode === link.target.id;
              const opacity = hoveredNode || hoveredLink
                ? (isHovered || isConnected ? 0.6 : 0.1)
                : 0.4;

              return (
                <motion.path
                  key={`link-${i}`}
                  d={sankeyLinkHorizontal()(link) || ''}
                  fill="none"
                  stroke={getLinkColor(link)}
                  strokeWidth={Math.max(1, link.width)}
                  initial={animated ? { pathLength: 0, opacity: 0 } : undefined}
                  animate={{ pathLength: 1, opacity }}
                  transition={{ duration: 0.8, delay: i * 0.02 }}
                  className="cursor-pointer transition-opacity duration-200"
                  onMouseEnter={(e) => handleLinkHover(link, e)}
                  onMouseLeave={handleMouseLeave}
                  onClick={() => onLinkClick?.({
                    source: link.source.id,
                    target: link.target.id,
                    value: link.value,
                  })}
                />
              );
            })}
          </g>

          {/* Nodes */}
          <g className="sankey-nodes">
            {sankeyData.nodes.map((node: any, i) => {
              const isHovered = hoveredNode === node.id;
              const nodeHeight = (node.y1 || 0) - (node.y0 || 0);

              return (
                <g key={`node-${i}`}>
                  <motion.rect
                    x={node.x0}
                    y={node.y0}
                    width={(node.x1 || 0) - (node.x0 || 0)}
                    height={nodeHeight}
                    fill={getNodeColor(node)}
                    rx={3}
                    initial={animated ? { scaleY: 0, opacity: 0 } : undefined}
                    animate={{ scaleY: 1, opacity: 1 }}
                    transition={{ duration: 0.4, delay: i * 0.05 }}
                    className={cn(
                      'cursor-pointer transition-all duration-200',
                      isHovered && 'filter brightness-110'
                    )}
                    style={{ transformOrigin: 'center' }}
                    onMouseEnter={(e) => handleNodeHover(node, e)}
                    onMouseLeave={handleMouseLeave}
                    onClick={() => onNodeClick?.(node)}
                  />

                  {/* Node label */}
                  <motion.text
                    x={(node.x0 || 0) < innerWidth / 2
                      ? (node.x1 || 0) + 8
                      : (node.x0 || 0) - 8
                    }
                    y={(node.y0 || 0) + nodeHeight / 2}
                    dy="0.35em"
                    textAnchor={(node.x0 || 0) < innerWidth / 2 ? 'start' : 'end'}
                    className="text-xs fill-foreground pointer-events-none"
                    initial={animated ? { opacity: 0 } : undefined}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.3, delay: 0.5 + i * 0.02 }}
                  >
                    {node.name}
                    {showValues && (
                      <tspan className="fill-muted-foreground ml-1">
                        {' '}({node.value?.toLocaleString() || ''})
                      </tspan>
                    )}
                  </motion.text>
                </g>
              );
            })}
          </g>
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
            <div className="font-medium">{tooltip.content.title}</div>
            {tooltip.content.value !== undefined && (
              <div className="text-muted-foreground">
                Value: {tooltip.content.value.toLocaleString()}
              </div>
            )}
            {tooltip.content.percentage !== undefined && (
              <div className="text-muted-foreground">
                {tooltip.content.percentage.toFixed(1)}% of total
              </div>
            )}
            {tooltip.content.details && (
              <div className="text-xs text-muted-foreground mt-1">
                {tooltip.content.details}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// Helper function to create journey data from touchpoints
export function createJourneyData(
  journeys: Array<{ touchpoints: string[]; converted: boolean; value?: number }>
): { nodes: SankeyNodeData[]; links: SankeyLinkData[] } {
  const nodeSet = new Set<string>();
  const linkMap = new Map<string, number>();

  // Add special nodes
  nodeSet.add('start');
  nodeSet.add('conversion');
  nodeSet.add('exit');

  journeys.forEach((journey) => {
    const { touchpoints, converted, value = 1 } = journey;

    if (touchpoints.length === 0) return;

    // Add all touchpoint nodes
    touchpoints.forEach((tp) => nodeSet.add(tp));

    // Add start -> first touchpoint
    const startKey = `start|${touchpoints[0]}`;
    linkMap.set(startKey, (linkMap.get(startKey) || 0) + value);

    // Add touchpoint -> touchpoint links
    for (let i = 0; i < touchpoints.length - 1; i++) {
      const key = `${touchpoints[i]}|${touchpoints[i + 1]}`;
      linkMap.set(key, (linkMap.get(key) || 0) + value);
    }

    // Add last touchpoint -> conversion/exit
    const lastTp = touchpoints[touchpoints.length - 1];
    const endKey = converted ? `${lastTp}|conversion` : `${lastTp}|exit`;
    linkMap.set(endKey, (linkMap.get(endKey) || 0) + value);
  });

  // Create nodes array
  const nodes: SankeyNodeData[] = Array.from(nodeSet).map((id) => ({
    id,
    name: id.charAt(0).toUpperCase() + id.slice(1),
    category: id === 'conversion' ? 'conversion' : id === 'exit' ? 'exit' : undefined,
  }));

  // Create links array
  const links: SankeyLinkData[] = Array.from(linkMap.entries()).map(([key, value]) => {
    const [source, target] = key.split('|');
    return { source, target, value };
  });

  return { nodes, links };
}

export default SankeyDiagram;
