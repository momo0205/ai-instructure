# AI 工作空间 — Superpowers 方法论

本工作空间包含多个独立的 AI 工具项目，所有开发工作遵循 [Superpowers](superpowers/) 方法论。

## 项目性质

这是一个 **AI 工具集合空间**，不是单一代码仓库。每个子目录是一个独立项目，有各自的技术栈和构建方式。项目的全局索引见 [INDEX.md](INDEX.md)。

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
