# AI 工作空间 — Superpowers 方法论

本工作空间包含多个独立的 AI 工具项目，所有开发工作遵循 [Superpowers](superpowers/) 方法论。

## 项目性质

这是一个 **AI 工具集合空间**，不是单一代码仓库。每个子目录是一个独立项目，有各自的技术栈和构建方式。项目的全局索引见 [README.md](README.md)。

## Superpowers 技能体系

开发任何子项目时，自动使用以下 Superpowers 技能：

### 开发流程（必须按顺序触发）

| 阶段 | 技能 | 触发条件 |
|------|------|----------|
| 1. 需求澄清 | `brainstorming` | 提出新功能、修改行为、不确定需求时 |
| 2. 环境准备 | `using-git-worktrees` | 需要在子项目的 git 仓库中隔离开发时 |
| 3. 制定计划 | `writing-plans` | 需求明确后、写代码前 |
| 4. 执行实现 | `subagent-driven-development` 或 `executing-plans` | 有计划需要执行时 |
| 5. 测试驱动 | `test-driven-development` | 任何代码实现过程中 |
| 6. 代码审查 | `requesting-code-review` | 任务间审查 |
| 7. 收尾 | `finishing-a-development-branch` | 任务全部完成时 |

### 问题处理

| 场景 | 技能 |
|------|------|
| Bug 修复 | `systematic-debugging` |
| 任何声称完成 | `verification-before-completion` |
| 并行独立任务 | `dispatching-parallel-agents` |
| 接受 Code Review 反馈 | `receiving-code-review` |

### 元能力

| 场景 | 技能 |
|------|------|
| 首次使用 | `using-superpowers` |
| 创建/修改技能 | `writing-skills` |

## 重要规则

1. **技能优先** — 即使只有 1% 可能相关，也必须先调用技能
2. **先澄清后编码** — 不要直接跳到写代码
3. **先测试后实现** — TDD: RED → GREEN → REFACTOR
4. **验证后声称完成** — 先跑测试确认，再声称完成
5. **子项目独立** — 每个子项目有自己的 git 仓库、构建系统、测试体系，不要混淆

## 跨 Agent 记忆系统 (Mem0)

本项目使用 Mem0 实现跨 Agent 共享记忆，确保在不同机器、不同 Agent（Claude Code / Codex / CodeWhale）之间无缝衔接。

### 环境准备（一次性）

```bash
pip3 install mem0ai sentence-transformers qdrant-client
echo DEEPSEEK_API_KEY=sk-xxxx > .env    # key 从项目所有者获取
```

### SOP：Agent 生命周期

**启动时（必须执行）**：

```bash
# 1. 拉取最新记忆（包括其他 Agent 的更新）
git pull

# 2. 获取项目上下文
python3 .memory/mem.py search "项目架构 关键决策"
python3 .memory/mem.py search "已知问题 踩坑"
```

**完成任务后（必须执行）**：

```bash
# 回写记忆（做了什么、关键决策、遇到的问题）
python3 .memory/mem.py add "【模块/项目名】具体完成了什么。关键决策：xxx。遇到问题：xxx"

# 提交到 git 同步
git add -A && git commit -m "memory: xxx" && git push
```

### 记忆规范

| 字段 | 说明 | 示例 |
|------|------|------|
| 前缀 | `【项目名/模块】` 标注归属 | `【IRON Flutter】【mira-server】` |
| 内容 | 做了什么 + 关键决策 + 踩坑 | 见下方示例 |
| 格式 | 一段话，不要拆分过细 | 1 条记忆覆盖 1 个任务 |

```
【IRON Flutter】修复 INTERNET 权限缺失导致无法连接服务器。App 名称改为 IRON，
默认服务器地址为 https://mira.ironmao.win，收藏系统重构为使用 reportId+serviceId，
支持收藏弹窗跳转。Keystore 密码改用 key.properties 读取。
```

### CLI 参考

```bash
python3 .memory/mem.py add "内容"           # 写入记忆
python3 .memory/mem.py search "关键词"       # 语义搜索
python3 .memory/mem.py list                 # 列出所有记忆
python3 .memory/mem.py reset                # 清空（慎用）
```

### 架构

```
┌──────────────┐      ┌──────────────┐
│  Claude Code  │      │  CodeWhale   │
│  (机器 A)     │      │  (机器 B)    │
└──────┬───────┘      └──────┬───────┘
       │ add/search          │ add/search
       ▼                     ▼
   .memory/ (git 仓库内)
   ├── config.py      # Mem0 配置 (DeepSeek LLM + 本地嵌入)
   ├── mem.py         # CLI 工具
   ├── qdrant/        # 向量库 (gitignored)
   └── history.db     # 历史 (gitignored)
        │
        ▼ git push/pull → 跨机器同步
```

> **注意**：数据文件 (qdrant/、history.db) 不进入 git，通过 git 同步的只有代码和记忆的元数据层。首次在新机器上使用需重新执行 `pip3 install`。
