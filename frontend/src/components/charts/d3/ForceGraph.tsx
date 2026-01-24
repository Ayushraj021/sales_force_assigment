/**
 * Force-Directed Graph Component
 *
 * Visualizes causal DAGs, network relationships, and entity connections
 * using D3.js force simulation with interactive features.
 */

import { useRef, useEffect, useState, useCallback, useMemo } from 'react';
import * as d3 from 'd3';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';

// Types
interface GraphNode {
  id: string;
  label: string;
  group?: string;
  value?: number;
  color?: string;
  size?: number;
  fixed?: boolean;
  fx?: number | null;
  fy?: number | null;
  x?: number;
  y?: number;
}

interface GraphLink {
  source: string | GraphNode;
  target: string | GraphNode;
  value?: number;
  label?: string;
  directed?: boolean;
  color?: string;
}

interface ForceGraphProps {
  nodes: GraphNode[];
  links: GraphLink[];
  width?: number;
  height?: number;
  className?: string;
  directed?: boolean;
  showLabels?: boolean;
  showLinkLabels?: boolean;
  showArrows?: boolean;
  nodeRadius?: number | ((node: GraphNode) => number);
  linkDistance?: number;
  chargeStrength?: number;
  colorScheme?: string[];
  onNodeClick?: (node: GraphNode) => void;
  onNodeDoubleClick?: (node: GraphNode) => void;
  onLinkClick?: (link: GraphLink) => void;
  enableZoom?: boolean;
  enableDrag?: boolean;
}

interface TooltipData {
  x: number;
  y: number;
  node?: GraphNode;
  link?: GraphLink;
}

// Default color scheme for groups
const DEFAULT_COLORS = [
  '#6366f1', // Indigo
  '#22c55e', // Green
  '#f97316', // Orange
  '#ec4899', // Pink
  '#8b5cf6', // Violet
  '#14b8a6', // Teal
  '#f43f5e', // Rose
  '#eab308', // Yellow
];

export function ForceGraph({
  nodes: initialNodes,
  links: initialLinks,
  width = 800,
  height = 600,
  className,
  directed = true,
  showLabels = true,
  showLinkLabels = false,
  showArrows = true,
  nodeRadius = 8,
  linkDistance = 100,
  chargeStrength = -300,
  colorScheme = DEFAULT_COLORS,
  onNodeClick,
  onNodeDoubleClick,
  onLinkClick,
  enableZoom = true,
  enableDrag = true,
}: ForceGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const simulationRef = useRef<d3.Simulation<GraphNode, GraphLink> | null>(null);
  const [tooltip, setTooltip] = useState<TooltipData | null>(null);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  // Prepare nodes and links with proper indexing
  const { nodes, links } = useMemo(() => {
    const nodesCopy = initialNodes.map((n) => ({ ...n }));
    const nodeMap = new Map(nodesCopy.map((n) => [n.id, n]));

    const linksCopy = initialLinks.map((l) => ({
      ...l,
      source: typeof l.source === 'string' ? l.source : l.source.id,
      target: typeof l.target === 'string' ? l.target : l.target.id,
    }));

    return { nodes: nodesCopy, links: linksCopy };
  }, [initialNodes, initialLinks]);

  // Color scale for groups
  const colorScale = useMemo(() => {
    const groups = [...new Set(nodes.map((n) => n.group || 'default'))];
    return d3.scaleOrdinal<string>()
      .domain(groups)
      .range(colorScheme);
  }, [nodes, colorScheme]);

  // Get node color
  const getNodeColor = useCallback((node: GraphNode) => {
    if (node.color) return node.color;
    return colorScale(node.group || 'default');
  }, [colorScale]);

  // Get node radius
  const getNodeRadius = useCallback((node: GraphNode) => {
    if (typeof nodeRadius === 'function') {
      return nodeRadius(node);
    }
    if (node.size) {
      return node.size;
    }
    return nodeRadius;
  }, [nodeRadius]);

  // Initialize force simulation
  useEffect(() => {
    if (!svgRef.current) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    // Create container groups
    const container = svg.append('g').attr('class', 'graph-container');

    // Arrow marker definition
    if (directed && showArrows) {
      svg.append('defs').selectAll('marker')
        .data(['arrow'])
        .join('marker')
        .attr('id', 'arrow')
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 20)
        .attr('refY', 0)
        .attr('markerWidth', 6)
        .attr('markerHeight', 6)
        .attr('orient', 'auto')
        .append('path')
        .attr('fill', 'currentColor')
        .attr('class', 'text-muted-foreground')
        .attr('d', 'M0,-5L10,0L0,5');
    }

    // Create links
    const link = container.append('g')
      .attr('class', 'links')
      .selectAll('line')
      .data(links)
      .join('line')
      .attr('stroke', (d: any) => d.color || 'hsl(var(--muted-foreground))')
      .attr('stroke-opacity', 0.6)
      .attr('stroke-width', (d: any) => Math.sqrt(d.value || 1))
      .attr('marker-end', directed && showArrows ? 'url(#arrow)' : null)
      .style('cursor', 'pointer')
      .on('click', (event: any, d: any) => {
        event.stopPropagation();
        onLinkClick?.(d);
      })
      .on('mouseenter', (event: any, d: any) => {
        if (showLinkLabels) {
          setTooltip({
            x: event.clientX,
            y: event.clientY,
            link: d,
          });
        }
      })
      .on('mouseleave', () => setTooltip(null));

    // Link labels
    const linkLabels = showLinkLabels
      ? container.append('g')
          .attr('class', 'link-labels')
          .selectAll('text')
          .data(links.filter((l) => l.label))
          .join('text')
          .attr('class', 'text-xs fill-muted-foreground')
          .attr('text-anchor', 'middle')
          .attr('dy', -5)
          .text((d: any) => d.label || '')
      : null;

    // Create nodes
    const node = container.append('g')
      .attr('class', 'nodes')
      .selectAll('g')
      .data(nodes)
      .join('g')
      .style('cursor', 'pointer')
      .on('click', (event: any, d: GraphNode) => {
        event.stopPropagation();
        setSelectedNode((prev) => (prev === d.id ? null : d.id));
        onNodeClick?.(d);
      })
      .on('dblclick', (event: any, d: GraphNode) => {
        event.stopPropagation();
        // Release fixed position on double-click
        d.fx = null;
        d.fy = null;
        onNodeDoubleClick?.(d);
      })
      .on('mouseenter', (event: any, d: GraphNode) => {
        setHoveredNode(d.id);
        setTooltip({
          x: event.clientX,
          y: event.clientY,
          node: d,
        });
      })
      .on('mouseleave', () => {
        setHoveredNode(null);
        setTooltip(null);
      });

    // Node circles
    node.append('circle')
      .attr('r', (d) => getNodeRadius(d))
      .attr('fill', (d) => getNodeColor(d))
      .attr('stroke', 'hsl(var(--background))')
      .attr('stroke-width', 2)
      .attr('class', 'transition-all duration-200');

    // Node labels
    if (showLabels) {
      node.append('text')
        .attr('dx', (d) => getNodeRadius(d) + 5)
        .attr('dy', '.35em')
        .attr('class', 'text-xs fill-foreground pointer-events-none')
        .text((d) => d.label);
    }

    // Drag behavior
    const drag = d3.drag<SVGGElement, GraphNode>()
      .on('start', (event, d) => {
        if (!event.active && simulationRef.current) {
          simulationRef.current.alphaTarget(0.3).restart();
        }
        d.fx = d.x;
        d.fy = d.y;
      })
      .on('drag', (event, d) => {
        d.fx = event.x;
        d.fy = event.y;
      })
      .on('end', (event, d) => {
        if (!event.active && simulationRef.current) {
          simulationRef.current.alphaTarget(0);
        }
        if (!d.fixed) {
          d.fx = null;
          d.fy = null;
        }
      });

    if (enableDrag) {
      node.call(drag as any);
    }

    // Zoom behavior
    if (enableZoom) {
      const zoom = d3.zoom<SVGSVGElement, unknown>()
        .scaleExtent([0.1, 4])
        .on('zoom', (event) => {
          container.attr('transform', event.transform.toString());
        });

      svg.call(zoom);

      // Initial centering
      const initialTransform = d3.zoomIdentity
        .translate(width / 2, height / 2);
      svg.call(zoom.transform, initialTransform);
    }

    // Force simulation
    const simulation = d3.forceSimulation<GraphNode>(nodes)
      .force('link', d3.forceLink<GraphNode, any>(links)
        .id((d) => d.id)
        .distance(linkDistance)
      )
      .force('charge', d3.forceManyBody().strength(chargeStrength))
      .force('center', d3.forceCenter(0, 0))
      .force('collision', d3.forceCollide<GraphNode>()
        .radius((d) => getNodeRadius(d) + 5)
      );

    simulationRef.current = simulation;

    // Update positions on tick
    simulation.on('tick', () => {
      link
        .attr('x1', (d: any) => d.source.x)
        .attr('y1', (d: any) => d.source.y)
        .attr('x2', (d: any) => d.target.x)
        .attr('y2', (d: any) => d.target.y);

      if (linkLabels) {
        linkLabels
          .attr('x', (d: any) => (d.source.x + d.target.x) / 2)
          .attr('y', (d: any) => (d.source.y + d.target.y) / 2);
      }

      node.attr('transform', (d) => `translate(${d.x || 0}, ${d.y || 0})`);
    });

    // Cleanup
    return () => {
      simulation.stop();
      simulationRef.current = null;
    };
  }, [
    nodes,
    links,
    width,
    height,
    directed,
    showLabels,
    showLinkLabels,
    showArrows,
    linkDistance,
    chargeStrength,
    enableZoom,
    enableDrag,
    getNodeColor,
    getNodeRadius,
    onNodeClick,
    onNodeDoubleClick,
    onLinkClick,
  ]);

  // Update visual states based on hover/selection
  useEffect(() => {
    if (!svgRef.current) return;

    const svg = d3.select(svgRef.current);

    // Update node styles
    svg.selectAll('.nodes circle')
      .attr('stroke-width', (d: any) => {
        if (selectedNode === d.id) return 4;
        if (hoveredNode === d.id) return 3;
        return 2;
      })
      .attr('opacity', (d: any) => {
        if (!hoveredNode && !selectedNode) return 1;
        if (hoveredNode === d.id || selectedNode === d.id) return 1;

        // Check if connected
        const isConnected = links.some(
          (l: any) =>
            (l.source === d.id || l.target === d.id ||
             l.source.id === d.id || l.target.id === d.id) &&
            (l.source === hoveredNode || l.target === hoveredNode ||
             l.source.id === hoveredNode || l.target.id === hoveredNode ||
             l.source === selectedNode || l.target === selectedNode ||
             l.source.id === selectedNode || l.target.id === selectedNode)
        );
        return isConnected ? 1 : 0.3;
      });

    // Update link styles
    svg.selectAll('.links line')
      .attr('stroke-opacity', (d: any) => {
        if (!hoveredNode && !selectedNode) return 0.6;
        const sourceId = typeof d.source === 'string' ? d.source : d.source.id;
        const targetId = typeof d.target === 'string' ? d.target : d.target.id;
        const activeNode = hoveredNode || selectedNode;
        if (sourceId === activeNode || targetId === activeNode) return 0.9;
        return 0.1;
      });
  }, [hoveredNode, selectedNode, links]);

  return (
    <div className={cn('relative', className)}>
      <svg
        ref={svgRef}
        width={width}
        height={height}
        className="bg-background rounded-lg"
      />

      {/* Legend */}
      <div className="absolute top-4 left-4 bg-background/80 backdrop-blur-sm rounded-lg p-3 shadow-sm border">
        <div className="text-xs font-medium mb-2">Legend</div>
        <div className="space-y-1">
          {[...new Set(nodes.map((n) => n.group || 'default'))].map((group) => (
            <div key={group} className="flex items-center gap-2">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: colorScale(group) }}
              />
              <span className="text-xs text-muted-foreground capitalize">
                {group}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Controls */}
      <div className="absolute bottom-4 right-4 flex gap-2">
        <button
          onClick={() => {
            if (simulationRef.current) {
              simulationRef.current.alpha(0.5).restart();
            }
          }}
          className="px-3 py-1.5 bg-primary text-primary-foreground text-xs rounded-md hover:bg-primary/90 transition-colors"
        >
          Reheat
        </button>
        <button
          onClick={() => {
            nodes.forEach((n) => {
              n.fx = null;
              n.fy = null;
            });
            if (simulationRef.current) {
              simulationRef.current.alpha(0.3).restart();
            }
          }}
          className="px-3 py-1.5 bg-secondary text-secondary-foreground text-xs rounded-md hover:bg-secondary/90 transition-colors"
        >
          Unpin All
        </button>
      </div>

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
            {tooltip.node && (
              <>
                <div className="font-medium">{tooltip.node.label}</div>
                {tooltip.node.group && (
                  <div className="text-xs text-muted-foreground">
                    Group: {tooltip.node.group}
                  </div>
                )}
                {tooltip.node.value !== undefined && (
                  <div className="text-xs text-muted-foreground">
                    Value: {tooltip.node.value.toLocaleString()}
                  </div>
                )}
              </>
            )}
            {tooltip.link && (
              <>
                <div className="font-medium">
                  {typeof tooltip.link.source === 'string'
                    ? tooltip.link.source
                    : tooltip.link.source.label}
                  {' → '}
                  {typeof tooltip.link.target === 'string'
                    ? tooltip.link.target
                    : tooltip.link.target.label}
                </div>
                {tooltip.link.value !== undefined && (
                  <div className="text-xs text-muted-foreground">
                    Weight: {tooltip.link.value}
                  </div>
                )}
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// Helper to create causal graph from adjacency matrix
export function createCausalGraph(
  nodes: string[],
  adjacencyMatrix: number[][],
  nodeGroups?: Record<string, string>
): { nodes: GraphNode[]; links: GraphLink[] } {
  const graphNodes: GraphNode[] = nodes.map((id, i) => ({
    id,
    label: id,
    group: nodeGroups?.[id] || 'variable',
    value: adjacencyMatrix[i]?.reduce((sum, v) => sum + v, 0) || 0,
  }));

  const graphLinks: GraphLink[] = [];

  for (let i = 0; i < adjacencyMatrix.length; i++) {
    for (let j = 0; j < adjacencyMatrix[i].length; j++) {
      if (adjacencyMatrix[i][j] > 0) {
        graphLinks.push({
          source: nodes[i],
          target: nodes[j],
          value: adjacencyMatrix[i][j],
          directed: true,
        });
      }
    }
  }

  return { nodes: graphNodes, links: graphLinks };
}

export default ForceGraph;
