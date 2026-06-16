/**
 * Diagram type - determines overall layout and node defaults
 */
export type DiagramType = 'flowchart' | 'architecture' | 'sequence' | 'er' | 'mindmap';
/**
 * Node visual types - determines shape and color
 */
export type NodeType = 'process' | 'action' | 'decision' | 'start' | 'end' | 'note' | 'async' | 'group';
/**
 * Edge (connection) style
 */
export type EdgeStyle = 'default' | 'dashed' | 'async' | 'thick';
/**
 * Layout direction
 */
export type LayoutDirection = 'TB' | 'LR' | 'BT' | 'RL';
/**
 * Node definition
 */
export interface NodeDef {
    id: string;
    label: string;
    type?: NodeType;
    style?: Partial<NodeStyleOverride>;
    group?: string;
    width?: number;
    height?: number;
}
/**
 * Edge (connection) definition
 */
export interface EdgeDef {
    source: string;
    target: string;
    label?: string;
    style?: EdgeStyle;
}
/**
 * Layout options
 */
export interface LayoutOptions {
    direction?: LayoutDirection;
    nodeWidth?: number;
    nodeHeight?: number;
    horizontalPadding?: number;
    verticalPadding?: number;
    startX?: number;
    startY?: number;
}
/**
 * Full graph definition - main input structure
 */
export interface GraphDefinition {
    title?: string;
    type?: DiagramType;
    nodes: NodeDef[];
    edges: EdgeDef[];
    layout?: LayoutOptions;
}
/**
 * Style override for individual nodes
 */
export interface NodeStyleOverride {
    fillColor: string;
    strokeColor: string;
    fontColor: string;
    fontSize: number;
    fontStyle: number;
    rounded: boolean;
    dashed: boolean;
    shape: string;
}
/**
 * Resolved node with computed position and style
 */
export interface ResolvedNode {
    id: string;
    label: string;
    type: NodeType;
    style: string;
    x: number;
    y: number;
    width: number;
    height: number;
    group?: string;
}
/**
 * Resolved edge with style
 */
export interface ResolvedEdge {
    id: string;
    source: string;
    target: string;
    label?: string;
    style: string;
}
/**
 * Intermediate resolved graph (before XML generation)
 */
export interface ResolvedGraph {
    title: string;
    nodes: ResolvedNode[];
    edges: ResolvedEdge[];
}
//# sourceMappingURL=index.d.ts.map