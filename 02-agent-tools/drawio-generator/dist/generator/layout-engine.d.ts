import { GraphDefinition, NodeDef, ResolvedNode, ResolvedEdge, LayoutOptions } from '../types';
/**
 * Compute x/y positions for all nodes using hierarchical layout
 */
export declare function computeLayout(nodes: NodeDef[], edges: Array<{
    source: string;
    target: string;
}>, options?: LayoutOptions): Map<string, {
    x: number;
    y: number;
    width: number;
    height: number;
}>;
/**
 * Resolve all nodes - infer types, compute styles and positions
 */
export declare function resolveNodes(nodeDefs: NodeDef[], edges: Array<{
    source: string;
    target: string;
}>, layoutOptions?: LayoutOptions): ResolvedNode[];
/**
 * Resolve all edges - compute styles
 */
export declare function resolveEdges(graph: GraphDefinition, nodeIdCounter: {
    value: number;
}): ResolvedEdge[];
//# sourceMappingURL=layout-engine.d.ts.map