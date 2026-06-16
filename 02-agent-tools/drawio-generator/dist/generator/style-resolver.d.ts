import { NodeType, EdgeStyle, NodeStyleOverride } from '../types';
export declare const NODE_DIMENSIONS: Record<NodeType, {
    width: number;
    height: number;
}>;
/**
 * Infer node type from label text using keyword rules
 */
export declare function inferNodeType(label: string): NodeType;
/**
 * Build full draw.io style string for a node
 */
export declare function resolveNodeStyle(type: NodeType, overrides?: Partial<NodeStyleOverride>): string;
/**
 * Get edge style string
 */
export declare function resolveEdgeStyle(style?: EdgeStyle): string;
//# sourceMappingURL=style-resolver.d.ts.map