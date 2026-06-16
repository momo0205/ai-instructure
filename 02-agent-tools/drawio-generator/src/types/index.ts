// Core type definitions for drawio-generator

/**
 * Diagram type - determines overall layout and node defaults
 */
export type DiagramType = 'flowchart' | 'architecture' | 'sequence' | 'er' | 'mindmap';

/**
 * Node visual types - determines shape and color
 */
export type NodeType =
  | 'process'    // Rectangle - heavy logic, services, helpers
  | 'action'     // Rounded rectangle, blue - BizAction, validation steps
  | 'decision'   // Diamond - conditional branching
  | 'start'      // Rounded rectangle, green - entry points, RPC interfaces
  | 'end'        // Ellipse - return points, terminal states
  | 'note'       // Note shape, yellow - important annotations
  | 'async'      // Dashed rectangle, gray - async flows, MQ, Consumer, Task
  | 'group';     // Swimlane container

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
  label: string;           // Display text (use \n for line breaks)
  type?: NodeType;         // Auto-inferred from label if not provided
  style?: Partial<NodeStyleOverride>;
  group?: string;          // Parent group/swimlane id
  width?: number;          // Override default width
  height?: number;         // Override default height
}

/**
 * Edge (connection) definition
 */
export interface EdgeDef {
  source: string;          // Source node id
  target: string;          // Target node id
  label?: string;          // Edge label (important logic description)
  style?: EdgeStyle;
}

/**
 * Layout options
 */
export interface LayoutOptions {
  direction?: LayoutDirection;  // Default: 'TB'
  nodeWidth?: number;           // Default node width: 160
  nodeHeight?: number;          // Default node height: 60
  horizontalPadding?: number;   // Horizontal spacing between nodes: 40
  verticalPadding?: number;     // Vertical spacing between layers: 60
  startX?: number;              // Canvas start X: 80
  startY?: number;              // Canvas start Y: 80
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
  fontStyle: number;       // 0=normal, 1=bold, 2=italic, 3=bold+italic
  rounded: boolean;
  dashed: boolean;
  shape: string;           // e.g. 'rhombus', 'note', 'ellipse'
}

/**
 * Resolved node with computed position and style
 */
export interface ResolvedNode {
  id: string;
  label: string;
  type: NodeType;
  style: string;           // Full drawio style string
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
  style: string;           // Full drawio style string
}

/**
 * Intermediate resolved graph (before XML generation)
 */
export interface ResolvedGraph {
  title: string;
  nodes: ResolvedNode[];
  edges: ResolvedEdge[];
}
