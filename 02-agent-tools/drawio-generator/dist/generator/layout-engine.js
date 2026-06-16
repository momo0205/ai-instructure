"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.computeLayout = computeLayout;
exports.resolveNodes = resolveNodes;
exports.resolveEdges = resolveEdges;
const style_resolver_1 = require("./style-resolver");
// Default layout options
const DEFAULT_LAYOUT = {
    direction: 'TB',
    nodeWidth: 0, // 0 = use type default
    nodeHeight: 0, // 0 = use type default
    horizontalPadding: 60,
    verticalPadding: 80,
    startX: 80,
    startY: 80,
};
/**
 * Build an adjacency list and compute node layers via BFS
 */
function computeLayers(nodes, edges) {
    const nodeIds = new Set(nodes.map(n => n.id));
    const inDegree = new Map();
    const adjacency = new Map();
    // Init
    for (const id of nodeIds) {
        inDegree.set(id, 0);
        adjacency.set(id, []);
    }
    // Build graph
    for (const edge of edges) {
        if (nodeIds.has(edge.source) && nodeIds.has(edge.target)) {
            adjacency.get(edge.source).push(edge.target);
            inDegree.set(edge.target, (inDegree.get(edge.target) ?? 0) + 1);
        }
    }
    // BFS layer assignment (topological sort with layer tracking)
    const layers = new Map();
    const queue = [];
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
        const current = queue.shift();
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
function computeLayout(nodes, edges, options = {}) {
    const opts = { ...DEFAULT_LAYOUT, ...options };
    const isLR = opts.direction === 'LR' || opts.direction === 'RL';
    // Compute layers
    const layers = computeLayers(nodes, edges);
    // Group nodes by layer
    const layerGroups = new Map();
    for (const node of nodes) {
        const layer = layers.get(node.id) ?? 0;
        if (!layerGroups.has(layer))
            layerGroups.set(layer, []);
        layerGroups.get(layer).push(node);
    }
    const sortedLayers = Array.from(layerGroups.keys()).sort((a, b) => a - b);
    // Compute max layer width (for centering)
    const layerWidths = new Map();
    for (const [layerIdx, layerNodes] of layerGroups.entries()) {
        let totalWidth = 0;
        for (const node of layerNodes) {
            const type = node.type ?? (0, style_resolver_1.inferNodeType)(node.label);
            const dims = style_resolver_1.NODE_DIMENSIONS[type];
            const w = opts.nodeWidth > 0 ? opts.nodeWidth : dims.width;
            totalWidth += w;
        }
        totalWidth += opts.horizontalPadding * (layerNodes.length - 1);
        layerWidths.set(layerIdx, totalWidth);
    }
    const maxLayerWidth = Math.max(...Array.from(layerWidths.values()));
    // Assign positions
    const positions = new Map();
    let currentY = opts.startY;
    for (const layerIdx of sortedLayers) {
        const layerNodes = layerGroups.get(layerIdx);
        const layerW = layerWidths.get(layerIdx);
        // Center this layer relative to the widest layer
        let currentX = opts.startX + (maxLayerWidth - layerW) / 2;
        let maxNodeHeight = 0;
        for (const node of layerNodes) {
            const type = node.type ?? (0, style_resolver_1.inferNodeType)(node.label);
            const dims = style_resolver_1.NODE_DIMENSIONS[type];
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
            }
            else {
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
function resolveNodes(nodeDefs, edges, layoutOptions = {}) {
    const positions = computeLayout(nodeDefs, edges, layoutOptions);
    return nodeDefs.map(node => {
        const type = node.type ?? (0, style_resolver_1.inferNodeType)(node.label);
        const pos = positions.get(node.id) ?? { x: 0, y: 0, width: 160, height: 60 };
        const style = (0, style_resolver_1.resolveNodeStyle)(type, node.style);
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
function resolveEdges(graph, nodeIdCounter) {
    return graph.edges.map((edge, idx) => {
        const style = (0, style_resolver_1.resolveEdgeStyle)(edge.style ?? 'default');
        return {
            id: `edge_${idx + 1}`,
            source: edge.source,
            target: edge.target,
            label: edge.label,
            style,
        };
    });
}
//# sourceMappingURL=layout-engine.js.map