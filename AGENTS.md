# AI 工作空间 — Superpowers 方法论

本工作空间包含多个独立的 AI 工具项目，所有开发工作遵循 [Superpowers](superpowers/) 方法论。

## 项目性质

这是一个 **AI 工具集合空间**，不是单一代码仓库。每个子目录是一个独立项目，有各自的技术栈和构建方式。项目的全局索引见 [projects.yaml](projects.yaml)（机器可读）与 [README.md](README.md)（人可读）。

## Superpowers 技能体系

> **在 DeepSeek Harness（DSH）里**：这些技能尚未注册为 DSH 原生 skill（本会话的技能列表里没有它们）。
> 因此「调用技能」= 先用 read 工具读取 `superpowers/skills/<name>/SKILL.md`，再按其中的步骤执行。
> 在 Claude Code / Codex 等已注册的客户端里，可以直接按名称触发。

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

## 并发写规则（多 Agent）

父仓 `main` 只接受两类提交：

| 类型 | 规则 |
|---|---|
| 代码 / 文档 | 有并发写者时走 worktree + 短命分支 + PR；**同一时间只有一个写者**时可直接推 main |
| 记忆账本 | 允许直接提交，但必须走 `./scripts/mem-commit.sh`，且只包含 `.memory/ledger.jsonl` |

为什么 ledger 是例外：`.memory/` 属于父仓库，**子模块的 worktree 里没有它**，
所以任何 Agent 回写记忆都只能落到主检出。这不是谁走错了目录，是结构决定的。

并发安全由机制保证，而不是靠"冲突概率低"：

- `.gitattributes` 给 ledger 配了 `merge=union` —— 两边追加的行自动取并集，不产生冲突；
- `scripts/mem-commit.sh` 会先 `pull --rebase`、只提交 ledger、推送被拒自动重试。

```bash
./scripts/mem-commit.sh "memory: 【项目】做了什么 / 关键决策 / 踩坑"
```

另外：子模块的改动只推到子模块自己的分支，父仓的**子模块指针等合并时一起更新**，
不要每做一步就单独提交一次指针。

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
git pull --rebase

# 2. 获取项目上下文
python3 .memory/mem.py search "项目架构 关键决策"
python3 .memory/mem.py search "已知问题 踩坑"

# 3. 换机器后或索引丢失时，从账本重建向量索引
python3 .memory/mem.py rebuild
```

**完成任务后（必须执行）**：

```bash
# 回写记忆（做了什么、关键决策、遇到的问题）
python3 .memory/mem.py add "【模块/项目名】具体完成了什么。关键决策：xxx。遇到问题：xxx"

# 用统一入口提交：自动 rebase、只提交 ledger、推送被拒自动重试
./scripts/mem-commit.sh "memory: 【模块/项目名】做了什么"
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

### 两层结构：账本是真相源

```
.memory/ledger.jsonl   ← 只追加，进 git，纯文本可 diff / 可 review
        │ rebuild
        ▼
.memory/qdrant/        ← 向量索引，gitignore，随时可从账本重建
```

- **写入顺序**：先落 ledger，再更新索引。索引失败也不丢记忆。
- **没有 `DEEPSEEK_API_KEY` 时**：`add` 仍写账本，`search` 自动降级为账本关键词检索。
- `mem0` 自己的配置/迁移目录被固定在 `.memory/.cache`（`MEM0_DIR`），不写 `~/.mem0`，
  因此在 DSH 这类只允许写工作区的沙箱里也能运行。
- **不要把向量库当真相源**：它只是缓存，换机器必须能重建。

### CLI 参考

```bash
python3 .memory/mem.py add "内容"       # 写入（账本 + 索引）
python3 .memory/mem.py search "关键词"   # 语义搜索（失败时降级为关键词）
python3 .memory/mem.py list             # 列出账本全部记忆
python3 .memory/mem.py rebuild          # 从账本重建索引
python3 .memory/mem.py export           # 把旧索引导出进账本
python3 .memory/mem.py reset            # 清空索引（不动账本）
```

### 跨机器同步

```
机器 A / Agent ──add──┐
                      ├──> .memory/ledger.jsonl ──git push/pull──> 机器 B
机器 B / Agent ──add──┘             │
                                    └──rebuild──> .memory/qdrant/（本地索引，不入库）
```

> 新机器首次使用：`pip3 install mem0ai sentence-transformers qdrant-client`，
> 配好 `DEEPSEEK_API_KEY`，然后 `python3 .memory/mem.py rebuild`。
