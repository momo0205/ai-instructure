import { GraphDefinition, NodeDef, NodeType, ResolvedNode, ResolvedEdge, LayoutOptions } from '../types';
import { NODE_DIMENSIONS, inferNodeType, resolveNodeStyle, resolveEdgeStyle } from './style-resolver';

// Default layout options
const DEFAULT_LAYOUT: Required<LayoutOptions> = {
  direction: 'TB',
  nodeWidth: 0,        // 0 = use type default
  nodeHeight: 0,       // 0 = use type default
  horizontalPadding: 60,
  verticalPadding: 80,
  startX: 80,
  startY: 80,
};

/**
 * Build an adjacency list and compute node layers via BFS
 */
function computeLayers(nodes: NodeDef[], edges: Array<{ source: string; target: string }>): Map<string, number> {
  const nodeIds = new Set(nodes.map(n => n.id));
  const inDegree = new Map<string, number>();
  const adjacency = new Map<string, string[]>();

  // Init
  for (const id of nodeIds) {
    inDegree.set(id, 0);
    adjacency.set(id, []);
  }

  // Build graph
  for (const edge of edges) {
    if (nodeIds.has(edge.source) && nodeIds.has(edge.target)) {
      adjacency.get(edge.source)!.push(edge.target);
      inDegree.set(edge.target, (inDegree.get(edge.target) ?? 0) + 1);
    }
  }

  // BFS layer assignment (topological sort with layer tracking)
  const layers = new Map<string, number>();
  const queue: string[] = [];

  // Start from nodes with no incoming edges
  for (const [id, deg] of inDegree.entries()) {
    if (deg === 0) {
      queue.push(id);
      layers.set(id, 0);
    }
  }

  // If no root nodes found (cycle or all nodes have incoming edges),
  // assign first node as root
  if (queue.length === 0 && nodes.length > 0) {
    queue.push(nodes[0].id);
    layers.set(nodes[0].id, 0);
  }

  while (queue.length > 0) {
    const current = queue.shift()!;
    const currentLayer = layers.get(current) ?? 0;

    for (const neighbor of (adjacency.get(current) ?? [])) {
      const existingLayer = layers.get(neighbor);
      const newLayer = currentLayer + 1;

      if (existingLayer === undefined || existingLayer < newLayer) {
        layers.set(neighbor, newLayer);
        queue.push(neighbor);
      }
    }
  }

  // Assign any unvisited nodes to layer 0
  for (const id of nodeIds) {
    if (!layers.has(id)) {
      layers.set(id, 0);
    }
  }

  return layers;
}

/**
 * Compute x/y positions for all nodes using hierarchical layout
 */
export function computeLayout(
  nodes: NodeDef[],
  edges: Array<{ source: string; target: string }>,
  options: LayoutOptions = {}
): Map<string, { x: number; y: number; width: number; height: number }> {
  const opts: Required<LayoutOptions> = { ...DEFAULT_LAYOUT, ...options };
  const isLR = opts.direction === 'LR' || opts.direction === 'RL';

  // Compute layers
  const layers = computeLayers(nodes, edges);

  // Group nodes by layer
  const layerGroups = new Map<number, NodeDef[]>();
  for (const node of nodes) {
    const layer = layers.get(node.id) ?? 0;
    if (!layerGroups.has(layer)) layerGroups.set(layer, []);
    layerGroups.get(layer)!.push(node);
  }

  const sortedLayers = Array.from(layerGroups.keys()).sort((a, b) => a - b);

  // Compute max layer width (for centering)
  const layerWidths = new Map<number, number>();
  for (const [layerIdx, layerNodes] of layerGroups.entries()) {
    let totalWidth = 0;
    for (const node of layerNodes) {
      const type: NodeType = node.type ?? inferNodeType(node.label);
      const dims = NODE_DIMENSIONS[type];
      const w = opts.nodeWidth > 0 ? opts.nodeWidth : dims.width;
      totalWidth += w;
    }
    totalWidth += opts.horizontalPadding * (layerNodes.length - 1);
    layerWidths.set(layerIdx, totalWidth);
  }

  const maxLayerWidth = Math.max(...Array.from(layerWidths.values()));

  // Assign positions
  const positions = new Map<string, { x: number; y: number; width: number; height: number }>();

  let currentY = opts.startY;

  for (const layerIdx of sortedLayers) {
    const layerNodes = layerGroups.get(layerIdx)!;
    const layerW = layerWidths.get(layerIdx)!;

    // Center this layer relative to the widest layer
    let currentX = opts.startX + (maxLayerWidth - layerW) / 2;

    let maxNodeHeight = 0;

    for (const node of layerNodes) {
      const type: NodeType = node.type ?? inferNodeType(node.label);
      const dims = NODE_DIMENSIONS[type];
      const w = node.width ?? (opts.nodeWidth > 0 ? opts.nodeWidth : dims.width);
      const h = node.height ?? (opts.nodeHeight > 0 ? opts.nodeHeight : dims.height);

      if (isLR) {
        // Left-to-right: swap x/y semantics
        positions.set(node.id, {
          x: currentY,
          y: currentX,
          width: h,
          height: w,
        });
      } else {
        positions.set(node.id, {
          x: currentX,
          y: currentY,
          width: w,
          height: h,
        });
      }

      currentX += w + opts.horizontalPadding;
      maxNodeHeight = Math.max(maxNodeHeight, h);
    }

    currentY += maxNodeHeight + opts.verticalPadding;
  }

  return positions;
}

/**
 * Resolve all nodes - infer types, compute styles and positions
 */
export function resolveNodes(
  nodeDefs: NodeDef[],
  edges: Array<{ source: string; target: string }>,
  layoutOptions: LayoutOptions = {}
): ResolvedNode[] {
  const positions = computeLayout(nodeDefs, edges, layoutOptions);

  return nodeDefs.map(node => {
    const type: NodeType = node.type ?? inferNodeType(node.label);
    const pos = positions.get(node.id) ?? { x: 0, y: 0, width: 160, height: 60 };
    const style = resolveNodeStyle(type, node.style);

    return {
      id: node.id,
      label: node.label,
      type,
      style,
      x: pos.x,
      y: pos.y,
      width: pos.width,
      height: pos.height,
      group: node.group,
    };
  });
}

/**
 * Resolve all edges - compute styles
 */
export function resolveEdges(
  graph: GraphDefinition,
  nodeIdCounter: { value: number }
): ResolvedEdge[] {
  return graph.edges.map((edge, idx) => {
    const style = resolveEdgeStyle(edge.style ?? 'default');
    return {
      id: `edge_${idx + 1}`,
      source: edge.source,
      target: edge.target,
      label: edge.label,
      style,
    };
  });
}
