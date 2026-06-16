#!/usr/bin/env node
"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const generator_1 = require("./generator");
function parseArgs(args) {
    const opts = {
        output: 'output.drawio',
        help: false,
        version: false,
        pretty: false,
    };
    for (let i = 0; i < args.length; i++) {
        const arg = args[i];
        switch (arg) {
            case '-i':
            case '--input':
                opts.input = args[++i];
                break;
            case '-o':
            case '--output':
                opts.output = args[++i];
                break;
            case '-h':
            case '--help':
                opts.help = true;
                break;
            case '-v':
            case '--version':
                opts.version = true;
                break;
            case '--pretty':
                opts.pretty = true;
                break;
            default:
                // Positional arg - treat as input file
                if (!arg.startsWith('-') && !opts.input) {
                    opts.input = arg;
                }
        }
    }
    return opts;
}
function printHelp() {
    console.log(`
drawio-gen - AI-driven draw.io file generator

USAGE:
  drawio-gen [options] [input-file]
  echo '<json>' | drawio-gen --output output.drawio

OPTIONS:
  -i, --input <file>    Input JSON file (reads from stdin if not specified)
  -o, --output <file>   Output .drawio file path (default: output.drawio)
  -h, --help            Show this help message
  -v, --version         Show version
  --pretty              Pretty-print output XML

INPUT FORMAT (JSON):
  {
    "title": "My Flow",
    "nodes": [
      { "id": "n1", "label": "Start", "type": "start" },
      { "id": "n2", "label": "Process", "type": "process" },
      { "id": "n3", "label": "Decision?", "type": "decision" }
    ],
    "edges": [
      { "source": "n1", "target": "n2" },
      { "source": "n2", "target": "n3", "label": "check result" }
    ]
  }

NODE TYPES:
  process   - Rectangle (heavy logic, services, helpers)
  action    - Rounded rectangle, blue (BizAction, validation)
  decision  - Diamond (conditional branching)
  start     - Rounded rectangle, green (entry points, RPC)
  end       - Ellipse (return points, terminal)
  note      - Note shape, yellow (important annotations)
  async     - Dashed rectangle, gray (MQ, Consumer, Task)

EXAMPLES:
  drawio-gen --input examples/payment-flow.json --output payment.drawio
  cat graph.json | drawio-gen -o output.drawio
`);
}
function printVersion() {
    try {
        const pkg = JSON.parse(fs.readFileSync(path.join(__dirname, '../package.json'), 'utf-8'));
        console.log(`drawio-gen v${pkg.version}`);
    }
    catch {
        console.log('drawio-gen v1.0.0');
    }
}
// ============================================================
// Read input (file or stdin)
// ============================================================
async function readInput(inputFile) {
    if (inputFile) {
        const resolved = path.resolve(inputFile);
        if (!fs.existsSync(resolved)) {
            throw new Error(`Input file not found: ${resolved}`);
        }
        return fs.readFileSync(resolved, 'utf-8');
    }
    // Read from stdin
    return new Promise((resolve, reject) => {
        // Check if stdin has data (not a TTY)
        if (process.stdin.isTTY) {
            reject(new Error('No input provided. Use --input <file> or pipe JSON via stdin.'));
            return;
        }
        let data = '';
        process.stdin.setEncoding('utf-8');
        process.stdin.on('data', (chunk) => { data += chunk; });
        process.stdin.on('end', () => resolve(data));
        process.stdin.on('error', reject);
    });
}
// ============================================================
// Main
// ============================================================
async function main() {
    const args = process.argv.slice(2);
    const opts = parseArgs(args);
    if (opts.help) {
        printHelp();
        process.exit(0);
    }
    if (opts.version) {
        printVersion();
        process.exit(0);
    }
    try {
        // Read input
        const rawInput = await readInput(opts.input);
        // Parse JSON
        let graph;
        try {
            graph = JSON.parse(rawInput);
        }
        catch (e) {
            throw new Error(`Invalid JSON input: ${e.message}`);
        }
        // Validate
        const { valid, errors } = (0, generator_1.validateGraph)(graph);
        if (!valid) {
            console.error('❌ Invalid graph definition:');
            for (const err of errors) {
                console.error(`   - ${err}`);
            }
            process.exit(1);
        }
        // Generate
        console.error(`🎨 Generating draw.io diagram: "${graph.title ?? 'Diagram'}"...`);
        console.error(`   Nodes: ${graph.nodes.length}, Edges: ${graph.edges.length}`);
        const xml = (0, generator_1.generateDrawio)(graph);
        // Write output
        const outputPath = path.resolve(opts.output);
        const outputDir = path.dirname(outputPath);
        if (!fs.existsSync(outputDir)) {
            fs.mkdirSync(outputDir, { recursive: true });
        }
        fs.writeFileSync(outputPath, xml, 'utf-8');
        console.error(`✅ Generated: ${outputPath}`);
        console.error(`   Open in draw.io: https://app.diagrams.net/`);
    }
    catch (err) {
        console.error(`❌ Error: ${err.message}`);
        process.exit(1);
    }
}
main();
//# sourceMappingURL=index.js.map