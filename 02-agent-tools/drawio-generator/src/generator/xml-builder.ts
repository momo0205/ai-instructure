import { ResolvedGraph, ResolvedNode, ResolvedEdge } from '../types';

// ============================================================
// XML escaping
// ============================================================

function escapeXml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;')
    .replace(/\n/g, '&#xa;');
}

// ============================================================
// Build a single mxCell for a vertex node
// ============================================================

function buildNodeCell(node: ResolvedNode): string {
  const label = escapeXml(node.label);
  return `        <mxCell id="${node.id}" value="${label}" style="${node.style}" vertex="1" parent="${node.group ?? '1'}">
          <mxGeometry x="${node.x}" y="${node.y}" width="${node.width}" height="${node.height}" as="geometry" />
        </mxCell>`;
}

// ============================================================
// Build a single mxCell for an edge
// ============================================================

function buildEdgeCell(edge: ResolvedEdge): string {
  const label = edge.label ? escapeXml(edge.label) : '';

  // Edge label style - smaller font, positioned on edge
  const labelStyle = label
    ? ` labelBackgroundColor=none;fontSize=11;`
    : '';

  const fullStyle = edge.style + (labelStyle ? labelStyle.trim() : '');

  return `        <mxCell id="${edge.id}" value="${label}" style="${fullStyle}" edge="1" source="${edge.source}" target="${edge.target}" parent="1">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>`;
}

// ============================================================
// Build complete mxGraphModel XML
// ============================================================

export function buildDrawioXml(graph: ResolvedGraph, diagramTitle: string = 'Page-1'): string {
  const nodeCells = graph.nodes.map(buildNodeCell).join('\n');
  const edgeCells = graph.edges.map(buildEdgeCell).join('\n');

  // Compute canvas size based on node positions
  let maxX = 1169;
  let maxY = 827;
  for (const node of graph.nodes) {
    maxX = Math.max(maxX, node.x + node.width + 100);
    maxY = Math.max(maxY, node.y + node.height + 100);
  }

  return `<mxfile host="app.diagrams.net" modified="${new Date().toISOString()}" agent="drawio-generator" version="21.0.0">
  <diagram id="diagram-1" name="${escapeXml(diagramTitle)}">
    <mxGraphModel dx="1422" dy="762" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="${maxX}" pageHeight="${maxY}" math="0" shadow="0">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
${nodeCells}
${edgeCells}
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>`;
}
