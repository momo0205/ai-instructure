import { GraphDefinition, ResolvedGraph } from '../types';
import { resolveNodes, resolveEdges } from './layout-engine';
import { buildDrawioXml } from './xml-builder';

let edgeIdCounter = { value: 0 };

/**
 * Main generator function
 * Takes a GraphDefinition and returns a .drawio XML string
 */
export function generateDrawio(graph: GraphDefinition): string {
  edgeIdCounter.value = 0;

  // Step 1: Resolve nodes (infer types, compute styles + positions)
  const resolvedNodes = resolveNodes(
    graph.nodes,
    graph.edges,
    graph.layout
  );

  // Step 2: Resolve edges (compute styles)
  const resolvedEdges = resolveEdges(graph, edgeIdCounter);

  // Step 3: Build resolved graph
  const resolvedGraph: ResolvedGraph = {
    title: graph.title ?? 'Diagram',
    nodes: resolvedNodes,
    edges: resolvedEdges,
  };

  // Step 4: Build XML
  return buildDrawioXml(resolvedGraph, graph.title ?? 'Page-1');
}

/**
 * Validate GraphDefinition - check for required fields
 */
export function validateGraph(graph: unknown): { valid: boolean; errors: string[] } {
  const errors: string[] = [];

  if (!graph || typeof graph !== 'object') {
    return { valid: false, errors: ['Input must be a JSON object'] };
  }

  const g = graph as Record<string, unknown>;

  if (!Array.isArray(g.nodes)) {
    errors.push('"nodes" must be an array');
  } else {
    for (let i = 0; i < g.nodes.length; i++) {
      const node = g.nodes[i] as Record<string, unknown>;
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
  } else {
    const nodeIds = Array.isArray(g.nodes)
      ? new Set((g.nodes as Array<{ id: string }>).map(n => n.id))
      : new Set<string>();

    for (let i = 0; i < g.edges.length; i++) {
      const edge = g.edges[i] as Record<string, unknown>;
      if (!edge.source || typeof edge.source !== 'string') {
        errors.push(`edges[${i}]: "source" is required and must be a string`);
      } else if (!nodeIds.has(edge.source)) {
        errors.push(`edges[${i}]: source "${edge.source}" does not match any node id`);
      }
      if (!edge.target || typeof edge.target !== 'string') {
        errors.push(`edges[${i}]: "target" is required and must be a string`);
      } else if (!nodeIds.has(edge.target)) {
        errors.push(`edges[${i}]: target "${edge.target}" does not match any node id`);
      }
    }
  }

  return { valid: errors.length === 0, errors };
}
