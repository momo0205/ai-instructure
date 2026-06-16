import { NodeType, EdgeStyle, NodeStyleOverride } from '../types';

// ============================================================
// Default node dimensions by type
// ============================================================
export const NODE_DIMENSIONS: Record<NodeType, { width: number; height: number }> = {
  process: { width: 180, height: 60 },
  action: { width: 200, height: 60 },
  decision: { width: 120, height: 80 },
  start: { width: 200, height: 50 },
  end: { width: 120, height: 50 },
  note: { width: 180, height: 70 },
  async: { width: 200, height: 60 },
  group: { width: 300, height: 200 },
};

// ============================================================
// Base style strings for each node type
// ============================================================

const BASE_STYLES: Record<NodeType, string> = {
  // Heavy logic / service nodes - plain rectangle
  process:
    'rounded=0;whiteSpace=wrap;html=1;fontSize=12;fontFamily=Helvetica;',

  // Action nodes - rounded rectangle, blue
  action:
    'rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;fontSize=12;fontFamily=Helvetica;',

  // Decision - diamond
  decision:
    'rhombus;whiteSpace=wrap;html=1;fontSize=12;fontFamily=Helvetica;',

  // Start / entry - rounded, green
  start:
    'rounded=1;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;fontSize=12;fontFamily=Helvetica;fontStyle=1;',

  // End / return - ellipse
  end:
    'ellipse;whiteSpace=wrap;html=1;fontSize=12;fontFamily=Helvetica;',

  // Note / important annotation - note shape, yellow
  note:
    'shape=note;whiteSpace=wrap;html=1;fillColor=#ffffc0;strokeColor=#d6b656;fontSize=11;fontFamily=Helvetica;',

  // Async / MQ / Consumer / Task - dashed gray rectangle
  async:
    'rounded=0;whiteSpace=wrap;html=1;dashed=1;fillColor=#f5f5f5;strokeColor=#666666;fontColor=#333333;fontSize=12;fontFamily=Helvetica;',

  // Group / swimlane container
  group:
    'swimlane;startSize=30;fontSize=13;fontStyle=1;fillColor=#f5f5f5;strokeColor=#666666;',
};

// ============================================================
// Edge style strings
// ============================================================

const EDGE_STYLES: Record<EdgeStyle, string> = {
  default:
    'edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;exitX=0.5;exitY=1;exitDx=0;exitDy=0;',
  dashed:
    'edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;dashed=1;',
  async:
    'edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;dashed=1;endArrow=open;strokeColor=#666666;',
  thick:
    'edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;strokeWidth=2;',
};

// ============================================================
// Type inference from label keywords
// ============================================================

interface KeywordRule {
  keywords: string[];
  type: NodeType;
  priority: number; // higher = checked first
}

const KEYWORD_RULES: KeywordRule[] = [
  // Start / entry - highest priority
  {
    keywords: ['rpc', '接口', '入口', '客户端', '调用rpc', 'applypay', 'applyrefund'],
    type: 'start',
    priority: 100,
  },
  // Action nodes
  {
    keywords: ['action', '校验', '检查', '验证', 'check', 'validate', '风控', '风险'],
    type: 'action',
    priority: 90,
  },
  // Decision / conditional
  {
    keywords: ['是否', '判断', '条件', '?', '？', '成功?', '失败?', '通过?', '存在?'],
    type: 'decision',
    priority: 80,
  },
  // Note / annotation
  {
    keywords: ['注意', '说明', '重要', '备注', '标注', 'note', '补充'],
    type: 'note',
    priority: 70,
  },
  // End / return
  {
    keywords: ['返回', '结束', 'end', 'return', '拒绝', '成功返回', '失败返回'],
    type: 'end',
    priority: 60,
  },
  // Async / background processing
  {
    keywords: ['异步', 'mq', 'consumer', 'task', '定时', '消息', '队列', '监听'],
    type: 'async',
    priority: 50,
  },
  // Process / service (default for helpers, services)
  {
    keywords: ['helper', 'service', 'remote', 'execute', 'impl', '处理', '执行', '构建', '生成'],
    type: 'process',
    priority: 10,
  },
];

/**
 * Infer node type from label text using keyword rules
 */
export function inferNodeType(label: string): NodeType {
  const lowerLabel = label.toLowerCase();

  // Sort by priority descending
  const sortedRules = [...KEYWORD_RULES].sort((a, b) => b.priority - a.priority);

  for (const rule of sortedRules) {
    for (const keyword of rule.keywords) {
      if (lowerLabel.includes(keyword.toLowerCase())) {
        return rule.type;
      }
    }
  }

  // Default to process
  return 'process';
}

/**
 * Build full draw.io style string for a node
 */
export function resolveNodeStyle(type: NodeType, overrides?: Partial<NodeStyleOverride>): string {
  let base = BASE_STYLES[type];

  if (!overrides) {
    return base;
  }

  // Apply overrides
  const overrideParts: string[] = [];

  if (overrides.fillColor !== undefined) {
    overrideParts.push(`fillColor=${overrides.fillColor}`);
  }
  if (overrides.strokeColor !== undefined) {
    overrideParts.push(`strokeColor=${overrides.strokeColor}`);
  }
  if (overrides.fontColor !== undefined) {
    overrideParts.push(`fontColor=${overrides.fontColor}`);
  }
  if (overrides.fontSize !== undefined) {
    overrideParts.push(`fontSize=${overrides.fontSize}`);
  }
  if (overrides.fontStyle !== undefined) {
    overrideParts.push(`fontStyle=${overrides.fontStyle}`);
  }
  if (overrides.rounded !== undefined) {
    overrideParts.push(`rounded=${overrides.rounded ? 1 : 0}`);
  }
  if (overrides.dashed !== undefined) {
    overrideParts.push(`dashed=${overrides.dashed ? 1 : 0}`);
  }
  if (overrides.shape !== undefined) {
    overrideParts.push(`shape=${overrides.shape}`);
  }

  if (overrideParts.length > 0) {
    // Merge overrides into base style
    base = base.trimEnd();
    if (!base.endsWith(';')) base += ';';
    base += overrideParts.join(';') + ';';
  }

  return base;
}

/**
 * Get edge style string
 */
export function resolveEdgeStyle(style: EdgeStyle = 'default'): string {
  return EDGE_STYLES[style];
}
