"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.generateDrawio = generateDrawio;
exports.validateGraph = validateGraph;
const layout_engine_1 = require("./layout-engine");
const xml_builder_1 = require("./xml-builder");
let edgeIdCounter = { value: 0 };
/**
 * Main generator function
 * Takes a GraphDefinition and returns a .drawio XML string
 */
function generateDrawio(graph) {
    edgeIdCounter.value = 0;
    // Step 1: Resolve nodes (infer types, compute styles + positions)
    const resolvedNodes = (0, layout_engine_1.resolveNodes)(graph.nodes, graph.edges, graph.layout);
    // Step 2: Resolve edges (compute styles)
    const resolvedEdges = (0, layout_engine_1.resolveEdges)(graph, edgeIdCounter);
    // Step 3: Build resolved graph
    const resolvedGraph = {
        title: graph.title ?? 'Diagram',
        nodes: resolvedNodes,
        edges: resolvedEdges,
    };
    // Step 4: Build XML
    return (0, xml_builder_1.buildDrawioXml)(resolvedGraph, graph.title ?? 'Page-1');
}
/**
 * Validate GraphDefinition - check for required fields
 */
function validateGraph(graph) {
    const errors = [];
    if (!graph || typeof graph !== 'object') {
        return { valid: false, errors: ['Input must be a JSON object'] };
    }
    const g = graph;
    if (!Array.isArray(g.nodes)) {
        errors.push('"nodes" must be an array');
    }
    else {
        for (let i = 0; i < g.nodes.length; i++) {
            const node = g.nodes[i];
            if (!node.id || typeof node.id !== 'string') {
                errors.push(`nodes[${i}]: "id" is required and must be a string`);
            }
            if (!node.label || typeof node.label !== 'string') {
                errors.push(`nodes[${i}]: "label" is required and must be a string`);
            }
        }
    }
    if (!Array.isArray(g.edges)) {
        errors.push('"edges" must be an array');
    }
    else {
        const nodeIds = Array.isArray(g.nodes)
            ? new Set(g.nodes.map(n => n.id))
            : new Set();
        for (let i = 0; i < g.edges.length; i++) {
            const edge = g.edges[i];
            if (!edge.source || typeof edge.source !== 'string') {
                errors.push(`edges[${i}]: "source" is required and must be a string`);
            }
            else if (!nodeIds.has(edge.source)) {
                errors.push(`edges[${i}]: source "${edge.source}" does not match any node id`);
            }
            if (!edge.target || typeof edge.target !== 'string') {
                errors.push(`edges[${i}]: "target" is required and must be a string`);
            }
            else if (!nodeIds.has(edge.target)) {
                errors.push(`edges[${i}]: target "${edge.target}" does not match any node id`);
            }
        }
    }
    return { valid: errors.length === 0, errors };
}
//# sourceMappingURL=index.js.map