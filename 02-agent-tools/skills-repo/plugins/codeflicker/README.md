# CodeFlicker

> 最后更新：2026-01-22 17:11

CodeFlicker 团队自用插件，包含团队内部开发和维护的专用技能工具。

## 包含技能

| 技能 | 说明 |
|------|------|
| [duet3-log-analyzer](skills/duet3-log-analyzer/SKILL.md) | 专业的 Duet3 诊断日志分析工具，基于 Duet3 多进程 Electron 架构，分析 MCP 连接、Extension Host、窗口通信和网络问题 |
| [tech-doc-organizer](skills/tech-doc-organizer/SKILL.md) | 技术文档扫描与优化工具，检测文档与代码不一致、查找合并/拆分机会、应用 lint 规则、精简长文档、归档旧内容、根据代码变更更新文档 |

## 适用场景

- Duet3 问题诊断和排查
- 日志分析和错误定位
- 架构层面的问题分析
- 技术文档整理和优化
- 团队内部工具使用

## 用法指南

### tech-doc-organizer

技术文档扫描与优化工具，支持文档一致性检查、精简、归档、更新和重组。

#### 触发关键词

| 关键词                         | 默认行为                         |
|--------------------------------|----------------------------------|
| 整理文档 / 优化文档 / 检查文档 | 展示操作菜单让用户选择           |
| 更新文档                       | 根据代码变更或当前任务上下文信息更新文档（git diff） |
| 精简文档 / 精简过长文档        | 扫描并精简过长文档               |
| 归档文档 / 旧文档归档          | 归档旧文档                       |
| 根据代码变更更新文档           | 分析 diff 并更新相关文档         |
| 文档和代码不一致               | 扫描一致性检查                   |



### duet3-log-analyzer

专业的 Duet3 诊断日志分析工具，支持日志分析和 SQLite 数据分析两种模式。

#### 快速开始

**日志分析（从日志 URL）**
```bash
./scripts/download_and_analyze.sh <url> [problem-description]
```

**SQLite 数据分析（从数据库目录）**
```bash
./scripts/analyze_sqlite.sh <sqlite_directory> [workspace_id]
```

#### 关键词触发分析

分析器会自动检测问题描述中的关键词并执行针对性分析：

| 关键词 | 触发的分析 |
|--------|-----------|
| `mcp`, `connection`, `connect` | MCP 连接分析 |
| `extension`, `exthost`, `crash`, `exit` | Extension Host 分析 |
| `window`, `ui`, `render`, `freeze`, `display` | 窗口/UI 分析 |
| `network`, `websocket`, `http`, `fetch`, `timeout` | 网络分析 |
| `duet` | Duet Agent 问题分析 |

更多详细信息请参考各技能的 SKILL.md 文档。

