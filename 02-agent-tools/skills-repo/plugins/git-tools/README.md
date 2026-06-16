# Git Tools 插件

> 最后更新：2026-01-19 21:09

本插件提供 Git 相关的工作流辅助 Skills。

## 包含的 Skills

| Skill | 功能 |
|-------|------|
| [commit-msg](./skills/commit-msg/) | 基于 staged diff 生成 Conventional Commit message |

---

## 使用方式

### commit-msg

#### 触发条件

用户说"生成 commit message"、"帮我写提交信息"、"commit msg" 时触发。

#### 前置条件

使用本 Skill 前，需要：
1. 当前目录是一个 Git 仓库
2. 有已暂存（staged）的变更，或者用户指定了文件/路径

#### 推荐用法

在 `git add` 暂存变更后，调用此 Skill 自动生成符合 Conventional Commits 规范的 commit message。

---

手动参考：直接阅读 `skills/commit-msg/SKILL.md` 了解核心规范。
