---
name: duet3-log-analyzer
description: Professional Duet3 diagnostic analyzer with deep architecture knowledge. Supports two analysis modes - (1) Log Analysis - analyzing MCP connections, extension host, window communication, and network issues from log archives (2) SQLite Data Analysis - analyzing session data loss, migration failures, and multi-process concurrency issues from SQLite database directories. Use when users provide Duet3 log archive URLs OR SQLite database directories for troubleshooting.
---

# Duet3 Log Analyzer (Enhanced)

## Quick Start

### Mode 1: Log Analysis (从日志 URL)

When user provides a Duet3 log URL and problem description:
1. Run `scripts/download_and_analyze.sh <url> [problem-description]`
2. Review the generated `analysis_report.md` in the temp directory
3. Use architecture knowledge to provide targeted recommendations

### Mode 2: SQLite Data Analysis (从数据库目录)

When user provides a SQLite database directory and reports data-related issues:
1. Run `scripts/analyze_sqlite.sh <sqlite_directory> [workspace_id]`
2. Review the output for data consistency issues
3. Use the detailed analysis patterns in this document to dig deeper

## Duet3 Architecture Overview

### Process Model

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Duet 主进程 (Main Process)                          │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    DuetExtensionHostManager                          │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │  workspaceId → DuetExtensionHostLauncher 映射                 │   │   │
│  │  │  Map<workspaceId, { proxy, rpc, extensionHostId, ... }>      │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    │ MessagePort                            │
│                                    ↓                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │              DuetAgentExtensionHostConnection                       │   │
│  │  - 消息透传 (根据 workspaceId 路由)                                  │   │
│  │  - workspaceId 注入/校验                                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    │ IPC                                    │
│                                    ↓                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    DuetAgentWindowService                           │   │
│  │  - 消息路由 (workspaceId -> connection)                             │   │
│  │  - 窗口管理                                                         │   │
│  │  - currentActiveWorkspaceId 维护（仅用于 UI 选中态）                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ IPC (duet-agent-message)
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Duet 窗口 (Renderer Process)                         │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         preload.ts                                  │   │
│  │  - 协议处理                                                         │   │
│  │  - source 注入: 'duet'                                              │   │
│  │  - $workspaceId 智能解析（resolveWorkspaceIdForMessage）              │   │
│  │    * 优先级1: message.$workspaceId（消息顶层，推荐）                  │   │
│  │    * 优先级2: message.payload.$workspaceId（RPC payload）            │   │
│  │    * 优先级3: message.payload.args[0].$workspaceId（args 数组）      │   │
│  │    * 优先级4: currentActiveWorkspaceId（兜底，不推荐）               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ↓                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         Duet UI (React)                              │   │
│  │  - Workspace 列表管理                                               │   │
│  │  - 对话界面                                                         │   │
│  │  - 消息发送时注入 workspaceId                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘

                        ↑ MessagePort ↓

┌─────────────────────────────────────────────────────────────────────────────┐
│                  Extension Host Process (独立进程，每 Workspace 一个)         │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    extensionHostProcess.ts                           │   │
│  │  - 接收 InitData                                                    │   │
│  │  - 创建 MessagePort 连接                                            │   │
│  │  - RPC 连接绑定 workspaceId                                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ↓                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    vscodeNativeView + BaseBridge                     │   │
│  │  - 监听 MessagePort                                                 │   │
│  │  - Handler 注册与消息分发                                           │   │
│  │  - source 注入: 'ide'                                               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Core Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `DuetExtensionHostManager` | Main Process | 管理所有 Extension Host 生命周期 |
| `DuetExtensionHostLauncher` | Main Process | 启动单个 Extension Host |
| `DuetAgentExtensionHostConnection` | Main Process | 与 Extension Host 的 MessagePort 连接 |
| `DuetAgentExtensionHostRpc` | Main Process | RPC 连接，已绑定 workspaceId |
| `DuetAgentWindowService` | Main Process | IPC 消息路由（workspaceId -> connection） |
| `preload.ts` | Renderer Process | 协议处理，workspaceId 智能解析 |
| `vscodeNativeView` | Extension Host | MessagePort 监听，消息转发 |
| `BaseBridge` | Extension Host | Handler 注册与协议处理 |

## workspaceId 路由机制

### 核心原则

```
┌─────────────────────────────────────────────────────────────────┐
│                    消息路由核心原则                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. 所有消息必须携带 workspaceId（顶层字段 message.$workspaceId）│
│                                                                 │
│  2. 主进程根据 workspaceId 选择目标 Extension Host connection   │
│                                                                 │
│  3. workspaceId 缺失或非法时：直接返回错误，禁止 silent fallback │
│                                                                 │
│  4. currentActiveWorkspaceId 不参与路由，仅用于 UI 选中态        │
│                                                                 │
│  5. workspaceId 必须来自 workspaceIdentifier.id，禁止使用路径   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### workspaceId 注入时机

| 场景 | 注入方式 | 说明 |
|------|----------|------|
| Session 维度动作 | `sessionId -> workspaceId` 反查 | session 创建时已绑定 workspaceId |
| 视图级动作 | 当前 UI context | 从 Workspace 列表的选中项获取 |
| Extension Host 上行 | connection 自带 | connection 创建时即绑定 workspaceId |

### 消息协议 (BridgeMessage)

```typescript
interface BridgeMessage {
  protocol: 'callHandler' | 'callback' | 'message';
  name?: string;           // callHandler 时使用
  callbackId?: number;     // callHandler/callback 时使用
  data?: any;              // 消息数据
  event?: string;          // message 时使用
  source?: 'duet' | 'ide'; // ✅ 消息来源标识（由基础设施层自动注入）
  $workspaceId: string;    // ✅ 消息路由关键字段
}
```

## Three-Tier Log Architecture

Duet3 日志采用三层架构，通过 sessionid 关联整个调用链路：

```
┌─────────────────────────────────────────────────────────────────┐
│                    Duet3 日志架构                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────────┐                                             │
│   │ Duet 窗口     │  duet.log                                   │
│   │ 渲染进程      │  - 消息发送/接收                             │
│   │              │  - source: 'duet' 注入                        │
│   │              │  - workspaceId 解析                           │
│   └──────┬───────┘                                             │
│          │ IPC                                                 │
│          ▼                                                     │
│   ┌──────────────┐                                             │
│   │ 主进程        │  main.log                                   │
│   │              │  - 窗口生命周期管理                           │
│   │              │  - IPC 消息路由                               │
│   │              │  - windowId/workspaceId 映射                  │
│   │              │  - Extension Host 连接管理                    │
│   │              │  - DuetAgentExtensionHostConnection          │
│   └──────┬───────┘                                             │
│          │                                                     │
│          ▼ MessagePort                                         │
│   ┌──────────────┐                                             │
│   │ kwaipilot    │  windowN/exthost/kuaishou.kwaipilot/*.log   │
│   │ 插件进程      │  - source: 'ide' 注入                        │
│   │ (Extension   │  - Handler 处理                              │
│   │  Host)       │  - 业务逻辑执行                               │
│   └──────────────┘                                             │
│                                                                 │
│   同一个 sessionId/requestId 可在三層日志中關聯查詢              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 日志文件说明

| 文件/目录 | 进程 | 主要用途 | 关键日志模式 |
|-----------|------|---------|-------------|
| `duet.log` | Duet窗口渲染进程 | Duet Agent 自身业务、消息处理 | `callHandler`, `sendMessage`, `source: 'duet'` |
| `main.log` | 主进程 | 窗口管理、IPC 路由、Extension Host 管理 | `duet-agent-message`, `workspaceId`, `ExtensionHostProcess`, `MessagePort` |
| `windowN/exthost/kuaishou.kwaipilot/*.log` | 插件进程 | kwaipilot 插件实现、MCP 调用 | `source: 'ide'`, `callHandler`, `handler` |

### Log File Mapping (from main.log)

```bash
# 查找 windowId 和 workspaceId 的映射
grep -E "(windowId|workspaceId|ExtensionHostProcess)" main.log

# 查找 MessagePort 连接状态
grep -E "MessagePort.*(connected|closed|error)" main.log

# 查找 IPC 消息路由
grep -E "duet-agent-message" main.log
```

## Log File Reference

### Log Priority & Location

| File | Process | Priority | Description |
|------|---------|----------|-------------|
| `main.log` | Main | 1 (Highest) | Main process events, window management, IPC routing |
| `duet.log` | DuetAgent | 1 | DuetAgent-specific logs, message handling |
| `renderer.log` | Renderer | 2 | Renderer process |
| `network.log` | Network | 2 | HTTP/WebSocket requests |
| `kwaipilot.log` | Extension | 2 | kwaipilot extension (in windowN/exthost/) |
| `windowN.log` | Window | 3 | Individual window logs |
| `exthost/*/*.log` | Extension Host | 3 | Extension host processes |

### Log File Size Limits

- **单个文件限制**: 5MB（自动轮转，保留 5 个备份）
- **总大小限制**: 100MB（上传时优先保留 main.log 和 duet.log）
- **目录保留**: 最近 10 个会话目录

## MCP Connection Analysis

### Connection State Machine

```
Stopped(0) ──start()──> Starting(1) ──success──> Running(2)
                            │
                            └── failure ──> Error(3)
                                                 │
                            stop() <─────────────┘
```

### MCP Error Codes

| Code | Name | Meaning |
|------|------|---------|
| -32700 | PARSE_ERROR | JSON parsing failed |
| -32600 | INVALID_REQUEST | Invalid request structure |
| -32601 | METHOD_NOT_FOUND | Method doesn't exist |
| -32602 | INVALID_PARAMS | Invalid parameters |
| -32603 | INTERNAL_ERROR | Internal server error |

### MCP Analysis Patterns

```bash
# Connection failures
grep -E "McpServerConnection.*(failed|Error|timeout|disconnected)" mcpServer.*.log

# State transitions
grep -E "state.*(Starting|Running|Error|Stopped)" mcpServer.*.log

# Error details
grep -E "errorState\.(message|code)" mcpServer.*.log

# Command not found (ENOENT)
grep -E "ENOENT|command.*not.*found" mcpServer.*.log
```

## Extension Host Analysis

### Common Exit Patterns

| Exit Code/Signal | Meaning |
|------------------|---------|
| `code: 1` | General error |
| `signal: SIGTERM` | Forced termination |
| `signal: SIGKILL` | Kill signal (forced) |
| `signal: SIGSEGV` | Segmentation fault |

### Extension Host Patterns

```bash
# Process exit events
grep -E "ExtensionHostProcess.*(exited|exit|code|signal)" main.log

# stderr output
grep -E "stderr.*(error|exception|Error)" exthost/*.log

# kwaipilot crashes
grep -E "kwaipilot.*(crash|exception|Fatal|SIGTERM)" kwaipilot*.log

# Connection closed
grep -E "ExtensionHostConnection.*(closed|error)" main.log
```

## Issue Diagnosis Patterns

### Critical Issues (High Priority)

| Pattern | Source | Likely Cause |
|---------|--------|--------------|
| `McpServerConnection.*failed` | mcp*.log | MCP server unreachable |
| `ExtensionHostProcess.*exited` | main.log | Extension crash |
| `DuetAgentExtensionHostConnection.*closed` | main.log | MessagePort broken |
| `kwaipilot.*crash` | kwaipilot.log | Extension error |
| `WebSocket.*error` | network.log | Connection lost |
| `ENOENT` | any log | Missing command/file |
| `$workspaceId.*missing` | duet.log/main.log | WorkspaceId 缺失 |
| `duet-agent-message.*error` | main.log | IPC 路由失败 |

### Warning Issues (Medium Priority)

| Pattern | Source | Likely Cause |
|---------|--------|--------------|
| `duet.*timeout` | duet.log | Slow response |
| `network.*timeout` | network.log | Network latency |
| `Context.*expired` | duet.log | Context overflow |
| `mcp.*retry` | mcp*.log | Reconnection attempts |
| `[warn]` | any log | Warning level logs |
| `currentActiveWorkspaceId` | duet.log | UI 选中态变化 |

### IPC Channel Reference

| Channel | Direction | Description |
|---------|-----------|-------------|
| `duet-agent-message` | UI → Main → ExtHost | BridgeMessage 路由 |
| `duet:workspace:activated` | Main → UI | Workspace 激活通知 |
| `duet:window:focusChanged` | Main → UI | 窗口焦点变化 |
| `vscode:confirmShadow` | Main → Workspace | 关闭确认对话框 |
| `vscode:shadow{token}` | Workspace → Main | 保持后台运行 |

## Enhanced Analysis Script Usage

```bash
# Basic analysis
./download_and_analyze.sh <log-url>

# With problem description (auto-triggers targeted analysis)
./download_and_analyze.sh <log-url> "MCP connection timeout"

# Full analysis with problem context
./download_and_analyze.sh <log-url> "Extension host crashes on startup"

# Duet-specific issues (triggers Duet Agent analysis)
./download_and_analyze.sh <log-url> "duet 窗口工作区无法重连"
./download_and_analyze.sh <log-url> "duet 消息接收有问题"
./download_and_analyze.sh <log-url> "duet 巴拉巴拉"
```

## Keyword-Triggered Analysis

The analyzer automatically detects keywords in the problem description and performs targeted analysis:

| Keywords | Analysis Triggered |
|----------|-------------------|
| `mcp`, `connection`, `connect` | MCP Connection Analysis |
| `extension`, `exthost`, `crash`, `exit` | Extension Host Analysis |
| `window`, `ui`, `render`, `freeze`, `display` | Window/UI Analysis |
| `network`, `websocket`, `http`, `fetch`, `timeout` | Network Analysis |
| `duet` | **Duet Agent Issues Analysis** |

### Duet-Specific Keywords (when "duet" is detected)

When the problem description contains "duet", the analyzer performs:

1. **Window Reconnection Issues**
   - `reconnect`, `workspaceWindow`, `verifyConnection`
   - `MessagePort.*closed`

2. **Message Reception/Sending Issues**
   - `sendMessage`, `onMessage`
   - `IPC.*(error|failed|timeout)`
   - `BridgeMessage.*(error|failed)`
   - `duet-agent-message`

3. **workspaceId Routing Issues**
   - `$workspaceId.*missing`
   - `currentActiveWorkspaceId`
   - `resolveWorkspaceIdForMessage`

4. **Duet Agent Service Issues**
   - `DuetAgentService`, `DuetAgentWindowService`
   - `duet.*error`, `duet.*failed`

5. **Extension Host Connection Issues**
   - `DuetAgentExtensionHostConnection`
   - `extensionHostConnection`

## Duet-Specific Troubleshooting Guide

### Three-Tier Cross-Reference Debugging

当排查 Duet 相关问题时，需要跨三个日志文件关联查询：

```bash
cd /tmp/duet-logs-XXXXXX/extracted_logs

# 1. 先从 main.log 找到 windowId 映射关系
echo "=== Window ID Mapping ===" && grep -E "(windowId|workspaceId|ExtensionHostProcess)" main.log | tail -20

# 2. 找到对应的 sessionId 或 requestId
echo "=== Session/Request ID ===" && grep -E "(sessionId|requestId).*" main.log duet.log | tail -10

# 3. 跨日志查询该 sessionId
ID="abc123-def456"

echo "=== Duet Window (duet.log) ===" && grep "$ID" duet.log | head -20
echo "=== Main Process (main.log) ===" && grep "$ID" main.log | head -20
echo "=== Kwaipilot Plugin (exthost) ===" && find . -path "*/exthost/kuaishou.kwaipilot/*.log" -exec grep "$ID" {} \; | head -20
```

### Window Reconnection Issues

**Symptoms:**
- Workspace window fails to reconnect after restart
- "DuetAgentWindowService verifyConnection failed"
- MessagePort connection closed unexpectedly

**排查步骤:**
```bash
# 1. 检查主进程中的窗口重连日志
echo "=== Main Process Reconnection ===" && grep -E "(reconnect|workspaceWindow|verifyConnection)" main.log

# 2. 检查 MessagePort 状态
echo "=== MessagePort Status ===" && grep -E "MessagePort.*(closed|error|connected)" main.log duet.log

# 3. 检查 windowId 和 workspaceId 映射
echo "=== Window Mapping ===" && grep -E "(windowId|workspaceId)" main.log

# 4. 检查 kwaipilot 插件进程是否异常退出
echo "=== Extension Host ===" && grep -E "ExtensionHostProcess.*(exited|exit)" main.log
```

**常见原因:**
- Extension host 进程异常退出 → 查看 `main.log` 中的 `ExtensionHostProcess.exited`
- MessagePort 连接断开 → 对比 `duet.log` 和 `main.log` 中的 MessagePort 状态
- workspaceId 映射丢失 → 检查 `main.log` 中的 `windowId` 和 `workspaceId` 映射关系

### Message Reception Issues

**Symptoms:**
- 消息发送后无响应
- IPC 通信超时
- BridgeMessage 处理失败

**排查步骤:**
```bash
# 1. Duet 窗口发送消息 (source: 'duet')
echo "=== Duet Message Send ===" && grep -E "(sendMessage|source.*duet)" duet.log | head -20

# 2. 主进程接收消息 (duet-agent-message)
echo "=== Main Process Receive ===" && grep -E "(duet-agent-message|IPC.*receive)" main.log | head -20

# 3. 检查 workspaceId 路由
echo "=== workspaceId Routing ===" && grep -E "workspaceId" main.log | head -20

# 4. 检查 BridgeMessage 处理
echo "=== BridgeMessage ===" && grep -E "BridgeMessage" main.log duet.log | head -20
```

**常见原因:**
- IPC 通道断开 → `duet.log` 发送成功但 `main.log` 无接收记录
- workspaceId 缺失/错误 → 检查 `message.$workspaceId` 是否正确
- 消息处理器未注册 → `main.log` 中无对应 handler 的日志

### Extension Host Connection Issues

**Symptoms:**
- DuetAgent 无法连接到扩展宿主
- `DuetAgentExtensionHostConnection` 错误
- 扩展功能无响应（如 MCP 调用失败）

**排查步骤:**
```bash
# 1. 主进程中的扩展宿主连接日志
echo "=== Extension Host Connection ===" && grep -E "DuetAgentExtensionHostConnection" main.log

# 2. 扩展宿主进程状态
echo "=== Extension Host Process ===" && grep -E "ExtensionHostProcess.*(exited|start|create)" main.log

# 3. kwaipilot 插件日志
echo "=== Kwaipilot Plugin ===" && find . -path "*/exthost/kuaishou.kwaipilot/*.log" -exec grep -l "error" {} \;

# 4. 检查 windowId 和 Extension Host 的映射
echo "=== Window-Extension Mapping ===" && grep -E "window.*ExtensionHost|workspaceId.*ExtensionHost" main.log
```

### workspaceId 路由问题排查

```bash
# 1. 检查 workspaceId 是否存在
echo "=== Missing workspaceId ===" && grep -E "\$workspaceId.*missing|workspaceId.*required" duet.log main.log

# 2. 检查 workspaceId 格式（不能包含路径字符）
echo "=== Invalid workspaceId ===" && grep -E "Invalid.*workspaceId.*path" main.log

# 3. 检查 currentActiveWorkspaceId 同步
echo "=== Active Workspace Sync ===" && grep -E "currentActiveWorkspaceId" duet.log | tail -10

# 4. 检查消息路由到错误的 workspace
echo "=== Wrong Routing ===" && grep -E "No.*connection.*workspace" main.log
```

## Debug Variables (When Inspecting Live)

```javascript
window.__DUET_AGENT__          // Marks DuetAgent window
window.__DUET_AGENT_CONFIG__   // Window configuration
window.duetWindow.isDuetWindowFocused()  // Focus state
window.__DUET_AGENT_SERVICES__ // Available services
```

## 案例分析技巧（经验总结）

### 案例：工作区 loading 卡住问题分析

**分析流程**：
1. 首先对比所有工作区的 `WorkspaceList` 状态，找出差异点
2. 检查 `extensionHostId` 字段是否缺失
3. 核对 `main.log` 中的 `Sending workspace connected event` 记录
4. 确认哪些工作区没有收到 `workspace initialized` 事件

**关键日志模式**：
```bash
# 对比 extensionHostId 是否缺失
grep "extensionHostId" duet.log

# 查找 initialized 事件接收记录
grep "workspace initialized" duet.log

# 查看事件发送记录
grep "Sending workspace connected event" main.log
```

**常见根因**：
- 消息遍历遗漏：DuetWorkspaceExtensionHostManager 遍历工作区时部分被遗漏
- SQLite 写入冲突导致状态同步失败
- 工作区验证逻辑的边界条件问题

### 工作区状态快速对比脚本

```bash
cd /tmp/duet-logs-XXXXXX/extracted_logs

echo "=== 工作区 extensionHostId 对比 ==="
grep -oE '"name":"[^"]+".*"extensionHostId":"[^"]*"' duet.log | sort | uniq

echo ""
echo "=== loading 状态统计 ==="
grep -oE '"name":"[^"]+".*"loading":[^,}]+' duet.log | sort | uniq

echo ""
echo "=== 初始化时间戳对比 ==="
grep -oE '"name":"[^"]+".*"initializedAt":[0-9]+' duet.log | sort | uniq
```

### 消息漏发问题排查

当发现部分工作区 `loading: true` 且 `extensionHostId: null` 时：

1. 检查 `main.log` 中 `Sending workspace connected event` 的工作区列表
2. 对比 duet.log 中 `Received workspace initialized` 的工作区列表
3. 找出差集即为漏发的工作区
4. 排查 DuetWorkspaceExtensionHostManager 的遍历逻辑

### Extension Host 状态对比

```bash
# 检查各工作区 Extension Host 是否正常运行
grep -E "MessagePort.*connected|__duet_ready__" main.log | grep "workspaceId="

# 对比 kwaipilot 插件日志中的错误
for log in window*/exthost/kuaishou.kwaipilot/kwaipilot.log; do
  echo "=== $(basename $(dirname $log)) ==="
  grep -c "error\|Error\|ERROR" "$log" 2>/dev/null || echo "0 errors"
done
```

### 跨日志关联查询模式

```bash
# 1. 从 duet.log 提取 workspaceId 列表
WORKSPACE_IDS=$(grep -oE '"workspaceId":"[a-f0-9]+"' duet.log | cut -d'"' -f4 | sort | uniq)

# 2. 查询各工作区的初始化状态
for id in $WORKSPACE_IDS; do
  echo "=== workspaceId: $id ==="
  echo "Main log events:"
  grep "$id" main.log | grep -E "(Sending|initialized)" | head -5
  echo "Duet log initialized:"
  grep "$id" duet.log | grep "workspace initialized" | head -2
done
```

## ⚠️ 重要：问题分类与日志分析的局限性

### 日志分析不是万能的

**核心原则：先理解问题的表现层，再决定是否需要日志分析**

日志分析擅长解决的问题：
- ✅ 进程间通信失败（IPC、MessagePort）
- ✅ 消息路由错误（workspaceId 路由）
- ✅ Extension Host 启动/崩溃问题
- ✅ 网络请求失败（MCP、HTTP）
- ✅ 状态同步问题（工作区连接状态）

日志分析 **不擅长** 解决的问题：
- ❌ **UI 渲染逻辑问题**（如下拉框显示错误的选项）
- ❌ **前端状态管理问题**（如 React 组件订阅了错误的数据源）
- ❌ **数据过滤/转换逻辑问题**（数据正确传递但被错误地使用）
- ❌ **CSS/样式问题**
- ❌ **用户交互逻辑问题**

### 案例：文件下拉框显示错误文件的问题

**用户反馈**：duet 内文件下拉框显示的不是当前工作区的文件，py-888 是其他项目的

**错误的分析路径** ❌：
1. 看到日志中 `activeFileUri: "file:///Users/.../py-888.py"`
2. 认为是 workspaceId 路由问题
3. 花大量时间分析 IPC 消息传递、Extension Host 连接
4. 最终方向跑偏

**正确的分析路径** ✅：
1. 先理解问题表现：**"文件下拉框显示错误"** → 这是一个 **UI 层问题**
2. 定位到具体 UI 组件代码：`UserInputTextArea.tsx` → `MentionPanel` → `useOptions.ts`
3. 阅读代码发现：`currentFileAndSelection` 来自 IDE 主窗口的 `activeTextEditor`，而非 Duet 当前工作区
4. 问题根因：`useOptions.ts` 中没有按当前工作区过滤 `currentFileAndSelection`

**教训总结**：
- 日志只能告诉你 **数据流动了什么**，不能告诉你 **数据被如何使用**
- UI 相关问题应该 **先看代码**，日志只是辅助验证
- 用户说的"显示错误"通常指的是 **渲染逻辑问题**，不是通信问题

### 问题分类决策流程

收到问题后，先进行分类：

```
用户问题
    │
    ├─ 关键词包含: "显示/展示/下拉框/选项/列表/UI/界面"
    │   └─→ 🎨 UI 层问题 → 先看前端代码（webview-ui/src）
    │
    ├─ 关键词包含: "超时/无响应/卡住/连接失败/断开"
    │   └─→ 🔌 通信层问题 → 日志分析（main.log, duet.log）
    │
    ├─ 关键词包含: "崩溃/退出/启动失败"
    │   └─→ 💥 进程层问题 → 日志分析 + 错误堆栈
    │
    └─ 关键词包含: "数据错误/丢失/不一致"
        └─→ 🔄 需要双管齐下：先看日志确认数据流，再看代码确认处理逻辑
```

### 多工作区场景的常见 UI 层问题

在 Duet 多工作区场景下，以下问题通常是 **前端代码问题**，不需要日志分析：

| 症状 | 可能的根因 | 排查方向 |
|------|-----------|---------|
| 文件列表显示其他工作区文件 | `currentFileAndSelection` 没有按工作区过滤 | `useOptions.ts` |
| 切换工作区后数据没更新 | Observable 没有重新订阅或没有工作区隔离 | `useBridgeObservableAPI.tsx` |
| 会话历史混乱 | sessionId 和 workspaceId 映射错误 | `composerSessionsStore` |
| 工作区状态不同步 | zustand store 订阅粒度太粗 | `useNavigationStore` |

### 如何避免分析方向跑偏

1. **先问用户更多细节**：
   - "文件下拉框"具体指哪个 UI 组件？
   - 问题是在什么操作后出现的？
   - 预期看到什么 vs 实际看到什么？

2. **先看代码再看日志**：
   - 对于 UI 相关问题，用 `grep_search` 定位到具体组件
   - 理解数据来源和渲染逻辑
   - 日志只用于验证假设

3. **日志分析时保持谨慎**：
   - 日志中的数据正确，不代表数据被正确使用
   - 不要被底层架构知识"带偏"——不是所有问题都是 IPC/MessagePort 问题

4. **建立问题→代码路径的直觉**：
   - 文件相关 → `MentionPanel/useOptions.ts`
   - 工作区列表 → `WorkspaceList.tsx`
   - 会话状态 → `composerSessionsStore`
   - 消息渲染 → `ComposerConversation/`

---

## SQLite 数据分析

除了日志分析外，本 Skill 还支持对 Duet3 的 SQLite 数据库进行分析，用于排查会话数据丢失、迁移失败等问题。

### 使用场景

当用户报告以下问题时，需要进行 SQLite 数据分析：

| 问题类型 | 关键词 | 分析方向 |
|---------|--------|---------|
| 会话历史丢失 | `历史记录丢失`、`会话消失`、`看不到历史` | 检查 composerHistory、composerMeta、composerWorkspaceIndex |
| 数据迁移失败 | `迁移`、`migration`、`matchingLegacyCount: 0` | 检查新旧库数据一致性 |
| 多进程并发问题 | `Atomic update failed`、`Version conflict` | 检查 SQLite 并发错误 |
| 数据不一致 | `数据丢失`、`数据错误`、`不同步` | 对比多个数据库的状态 |

### 数据库架构（Duet3 并行化改造后）

Duet3 采用 5 个独立数据库，按业务隔离：

```
~/.kwaipilot/data/vscode/
├── session_data.sqlite     # 旧版数据（Legacy）
│   └── composerHistory     # 大数组，包含所有会话元数据（旧）
│   └── composerData:{sid}  # 会话消息数据（旧）
│
├── index.sqlite            # 索引和元数据（新）
│   └── composerMeta:{sid}  # 单个会话元数据
│   └── composerWorkspaceIndex:{uri} # 工作区→会话ID索引
│
├── composer_data.sqlite    # 会话消息数据（新）
│   └── composerData:{sid}  # 会话完整消息
│
├── api_history.sqlite      # API 对话历史
│   └── apiConversationHistory:{sid}
│
└── cache.sqlite            # 缓存数据（可丢失）
    └── blockCodeCache:{sid}
```

### 数据结构详解

#### composerHistory（旧库 - session_data.sqlite）

```json
// key: "composerHistory"
// value: ComposerSessionData[] 大数组
[
  {
    "sessionId": "abc123",
    "name": "会话名称",
    "createdAt": 1737123456789,
    "lastUpdatedAt": 1737123456789,
    "workspaceUri": "file:///Users/.../workspaceStorage/{workspaceId}/kuaishou.kwaipilot",
    "agentMode": "agent"
  },
  // ... 更多会话
]
```

#### composerMeta（新库 - index.sqlite）

```json
// key: "composerMeta:{sessionId}"
{
  "sessionId": "abc123",
  "name": "会话名称",
  "createdAt": 1737123456789,
  "lastUpdatedAt": 1737123456789,
  "workspaceUri": "file:///Users/.../workspaceStorage/{workspaceId}/kuaishou.kwaipilot",
  "agentMode": "agent"
}
```

#### composerWorkspaceIndex（新库 - index.sqlite）

```json
// key: "composerWorkspaceIndex:{workspaceUri}"
{
  "sessionIds": ["abc123", "def456", "ghi789"],
  "lastModified": 1737123456789
}
```

### 快速分析脚本

当用户提供 SQLite 数据库目录时，使用以下命令进行分析：

```bash
# 设置数据库目录
DB_DIR="/path/to/sqlite/directory"

# 1. 查看数据库文件
ls -la "$DB_DIR"/*.sqlite*

# 2. 检查各数据库的 key 分布
echo "=== session_data.sqlite (旧库) ==="
sqlite3 "$DB_DIR/session_data.sqlite" "SELECT substr(key, 1, 20) as prefix, COUNT(*) FROM KwaipilotKV GROUP BY substr(key, 1, instr(key || ':', ':')-1);"

echo "=== index.sqlite (索引) ==="
sqlite3 "$DB_DIR/index.sqlite" "SELECT substr(key, 1, 25) as prefix, COUNT(*) FROM KwaipilotKV GROUP BY substr(key, 1, instr(key || ':', ':')-1);"

echo "=== composer_data.sqlite (会话数据) ==="
sqlite3 "$DB_DIR/composer_data.sqlite" "SELECT COUNT(*) as total FROM KwaipilotKV WHERE key LIKE 'composerData:%';"

echo "=== cache.sqlite (缓存) ==="
sqlite3 "$DB_DIR/cache.sqlite" "SELECT substr(key, 1, 20) as prefix, COUNT(*) FROM KwaipilotKV GROUP BY substr(key, 1, instr(key || ':', ':')-1);" 2>/dev/null || echo "无数据或表不存在"
```

### 会话数据丢失问题排查

当用户报告某个工作区的历史记录丢失时：

```bash
# 设置变量
DB_DIR="/path/to/sqlite"
WORKSPACE_ID="21e800fcbe27e287547285beac619c38"  # 从工作区 URI 中提取

# 1. 检查旧库中的 composerHistory
echo "=== 旧库 composerHistory ==="
sqlite3 "$DB_DIR/session_data.sqlite" "SELECT value FROM KwaipilotKV WHERE key = 'composerHistory';" | python3 -c "
import sys, json
from datetime import datetime

data = json.load(sys.stdin)
target_ws = '$WORKSPACE_ID'

matching = [item for item in data if target_ws in item.get('workspaceUri', '')]
print(f'匹配的会话数: {len(matching)}')
for item in matching[:5]:
    ts = item.get('lastUpdatedAt', 0)
    dt = datetime.fromtimestamp(ts/1000).strftime('%Y-%m-%d %H:%M:%S') if ts else 'N/A'
    print(f'  {dt} | {item.get(\"sessionId\", \"\")[:20]}... | {item.get(\"name\", \"\")[:30]}')
"

# 2. 检查新库中的 composerWorkspaceIndex
echo "=== 新库 composerWorkspaceIndex ==="
sqlite3 "$DB_DIR/index.sqlite" "SELECT value FROM KwaipilotKV WHERE key LIKE '%$WORKSPACE_ID%';"

# 3. 检查 cache.sqlite 中是否有数据（证明会话确实存在过）
echo "=== cache.sqlite 中的会话数据 ==="
sqlite3 "$DB_DIR/cache.sqlite" "SELECT key FROM KwaipilotKV WHERE key LIKE '%$WORKSPACE_ID%';" 2>/dev/null | head -20
```

### 数据迁移问题排查

Duet3 使用 Read-Through Migration 策略，访问时按需迁移：

```bash
# 检查迁移相关日志
grep -r "matchingLegacyCount\|migration\|Missing legacy" --include="*.log" /path/to/logs/

# 对比旧库和新库的数据量
echo "=== 旧库 composerHistory 条目数 ==="
sqlite3 "$DB_DIR/session_data.sqlite" "SELECT value FROM KwaipilotKV WHERE key = 'composerHistory';" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))"

echo "=== 新库 composerMeta 条目数 ==="
sqlite3 "$DB_DIR/index.sqlite" "SELECT COUNT(*) FROM KwaipilotKV WHERE key LIKE 'composerMeta:%';"

echo "=== 新库 composerWorkspaceIndex 条目数 ==="
sqlite3 "$DB_DIR/index.sqlite" "SELECT COUNT(*) FROM KwaipilotKV WHERE key LIKE 'composerWorkspaceIndex:%';"
```

### 多进程并发问题排查

检查 SQLite 并发写入错误：

```bash
# 搜索并发相关错误
grep -r "Atomic update failed\|Version conflict\|Failed to sync table\|SQLITE_BUSY\|SQLITE_LOCKED" --include="*.log" /path/to/logs/

# 检查 KwaipilotKV_backup 表错误
grep -r "no such table: KwaipilotKV_backup\|Validation error" --include="*.log" /path/to/logs/
```

### 常见问题与根因

| 症状 | 可能的根因 | 排查命令 |
|------|-----------|---------|
| `matchingLegacyCount: 0` | workspaceUri 格式不匹配 | 对比 `composerHistory` 中的 URI 和当前 URI |
| `Atomic update failed after 5 retries` | 多进程并发写入冲突 | 检查同时运行的窗口数 |
| `Failed to sync table` | 表结构变更冲突 | 检查多个进程启动时间 |
| `no such table: KwaipilotKV_backup` | 原子更新依赖的备份表不存在 | 检查数据库版本 |
| 会话在 cache 中存在但 index 中不存在 | 写入流程中断或清理机制误删 | 检查 `cleanupOrphanedData` 日志 |

### 数据一致性验证脚本

验证 composer_data 和 index 的一致性：

```bash
DB_DIR="/path/to/sqlite"

echo "=== 检查 composer_data 中的会话是否在 index 中有对应的 meta ==="
sqlite3 "$DB_DIR/composer_data.sqlite" "SELECT key FROM KwaipilotKV WHERE key LIKE 'composerData:%';" | while read key; do
  sid=$(echo "$key" | cut -d':' -f2)
  meta_exists=$(sqlite3 "$DB_DIR/index.sqlite" "SELECT COUNT(*) FROM KwaipilotKV WHERE key = 'composerMeta:$sid';")
  if [ "$meta_exists" = "0" ]; then
    echo "❌ 孤儿数据: $sid 在 composer_data 中存在但 index 中无 meta"
  fi
done

echo "=== 检查 composerMeta 是否都被 composerWorkspaceIndex 引用 ==="
# 收集所有被索引引用的 sessionId
sqlite3 "$DB_DIR/index.sqlite" "SELECT value FROM KwaipilotKV WHERE key LIKE 'composerWorkspaceIndex:%';" | python3 -c "
import sys, json

indexed_sids = set()
for line in sys.stdin:
    try:
        index = json.loads(line.strip())
        for sid in index.get('sessionIds', []):
            indexed_sids.add(sid)
    except:
        pass
print(f'被索引引用的 sessionId 数: {len(indexed_sids)}')
" > /tmp/indexed_sids.txt

cat /tmp/indexed_sids.txt
```

### 时间线分析

当需要分析数据丢失发生的时间点时：

```bash
DB_DIR="/path/to/sqlite"

echo "=== composerHistory 最后更新时间 ==="
sqlite3 "$DB_DIR/session_data.sqlite" "SELECT value FROM KwaipilotKV WHERE key = 'composerHistory';" | python3 -c "
import sys, json
from datetime import datetime

data = json.load(sys.stdin)
sorted_data = sorted(data, key=lambda x: x.get('lastUpdatedAt', 0), reverse=True)

print('最近更新的 5 条:')
for item in sorted_data[:5]:
    ts = item.get('lastUpdatedAt', 0)
    dt = datetime.fromtimestamp(ts/1000).strftime('%Y-%m-%d %H:%M:%S') if ts else 'N/A'
    print(f'  {dt} | {item.get(\"sessionId\", \"\")[:20]}... | {item.get(\"name\", \"\")[:30]}')
"

echo "=== index.sqlite composerMeta 最后更新时间 ==="
sqlite3 "$DB_DIR/index.sqlite" "SELECT value FROM KwaipilotKV WHERE key LIKE 'composerMeta:%';" | python3 -c "
import sys, json
from datetime import datetime

metas = []
for line in sys.stdin:
    try:
        meta = json.loads(line.strip())
        metas.append(meta)
    except:
        pass

sorted_metas = sorted(metas, key=lambda x: x.get('lastUpdatedAt', 0), reverse=True)

print('最近更新的 5 条:')
for meta in sorted_metas[:5]:
    ts = meta.get('lastUpdatedAt', 0)
    dt = datetime.fromtimestamp(ts/1000).strftime('%Y-%m-%d %H:%M:%S') if ts else 'N/A'
    print(f'  {dt} | {meta.get(\"sessionId\", \"\")[:20]}... | {meta.get(\"name\", \"\")[:30]}')
"
```

### 孤儿数据清理机制

Duet3 在启动后 5 分钟执行 `cleanupOrphanedData()`：

```
cleanupOrphanedData()
├── cleanupOrphanedIndexes()
│   └── 遍历所有 composerWorkspaceIndex
│   └── 检查每个 sessionId 是否有对应的 composerMeta
│   └── 如果 meta 不存在 → 从索引中移除该 sessionId
│
└── cleanupOrphanedMetas()
    └── 收集所有索引中引用的 sessionId
    └── 遍历所有 composerMeta
    └── 如果 meta 的 sessionId 未被任何索引引用 → 删除该 meta
```

**⚠️ 潜在问题**：如果 `createOrUpdateSession()` 过程中：
1. composerMeta 写入成功
2. 但 composerWorkspaceIndex 的 atomicUpdate 失败
3. 5 分钟后 cleanupOrphanedMetas 运行
4. 发现这个 meta 没有被任何索引引用 → 删除！

这就解释了为什么会出现"数据曾经存在但后来消失"的情况。

### 检查孤儿清理日志

```bash
# 搜索孤儿数据清理相关日志
grep -r "Orphaned data cleanup\|Cleaned orphaned metas\|Cleaned orphaned index" --include="*.log" /path/to/logs/

# 如果看到 "Cleaned orphaned metas: count: N"，说明有 N 条 meta 被清理
# 这可能是数据丢失的原因
```

### SQLite WAL 文件检查

SQLite 使用 WAL 模式，数据可能暂存在 .sqlite-wal 文件中：

```bash
# 检查 WAL 文件大小
ls -la "$DB_DIR"/*.sqlite-wal

# 如果 WAL 文件为 0 字节，说明所有数据已 checkpoint 到主数据库
# 如果 WAL 文件较大，可能有未提交的数据

# 手动触发 checkpoint（谨慎操作）
# sqlite3 "$DB_DIR/index.sqlite" "PRAGMA wal_checkpoint(TRUNCATE);"
```
