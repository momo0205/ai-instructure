# Agent Skills 仓库

![](./assets/2.jpg)

> **⚠️ 首次使用必须先执行初始化脚本**
>
> ```bash
> git clone <仓库地址>
> cd agent-skills
> source scripts/setup.sh
> ```
>
> 此脚本用于检测和配置环境，确保代码贡献符合仓库规范。

## 简介

Agent Skills 是一个公司内部开源项目，用于统一托管和分发各类 Agent Skills。

## 首次使用

**首次使用必须运行初始化脚本**：

```bash
git clone <仓库地址>
cd agent-skills
source scripts/setup.sh
```

此脚本会：

1. 检查 Git Hook 是否已配置
2. 如果未配置，自动进行配置
3. 验证配置是否成功

## 什么是 Skill？

Skill 是智能体在特定领域执行任务的能力单元。每个 Skill 包含完成特定任务所需的所有信息和指令，使智能体能够高效、准确地完成工作。

对于 Agent Skills 如果不太了解的，可以参考以下文章：

- [Introducing Agent Skills](https://www.anthropic.com/news/skills) - Anthropic 官方首次定义 Agent Skills 的新闻稿，最权威的原始资料
- [Equipping agents for the real world with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) - Anthropic 工程博客，详解技术实现与渐进式披露机制
- [Agent Skills Overview](https://console.anthropic.com/docs/en/agents-and-tools/agent-skills/overview) - Anthropic 官方 API 文档，详细说明工作原理与核心优势
- [Agent Skills Spec](https://github.com/anthropics/skills/blob/main/spec/agent-skills-spec.md) - Anthropic 官方 GitHub 技能标准规范，技术实现的权威指南
- [Agent Skills 终极指南:入门、精通、预测](https://www.163.com/dy/article/KILMQ9FB0556C3IR.html) - 全面指南，包含创建、组合、测试完整流程

## 可用插件

所有 Skills 都存放在 `plugins/` 目录下。每个插件包含多个 Skills，可单独使用。

## 快速使用

![](./assets/1.jpg)

### 1. 了解 Agent Skills

本仓库的设计理念是让 AI 帮你解决 AI 的问题。

#### 方式一：让 AI 帮你探索

1. **克隆仓库**：`git clone <仓库地址>`
2. **用 IDE 或 CLI 打开**：`cd agent-skills && code .` 或在终端中
3. **直接问 AI**：
   - "这个仓库有哪些 Skill？"
   - "code-review 主题下有哪些具体的 Skill？"
   - "如何贡献一个新的 Skill？"

AI 会读取 AGENTS.md 和目录结构，自动理解并回答你的问题。

#### 方式二：手动浏览

在 `plugins/` 目录下查看各插件的 README.md，了解该插件的功能和可用的 Skills。

### 2. 使用 Agent Skills

将 Skill 的路径（如 `plugins/qa-test/skills/test-case-generate/`）提供给智能体，智能体将根据 Skill 中的指令执行任务。

### 3. 贡献 Skill

参见 [AGENTS.md](./AGENTS.md) 了解贡献规范。

#### 💡 跨项目共享 Skills

如果需要在多个项目中使用 Skills，可以使用 `manage-skills.sh` 脚本将 Skill 安装到全局目录 `~/.kwaipilot/skills/`：

```bash
# 查看所有可用的 Skill
bash scripts/manage-skills.sh list

# 安装指定 Skill
bash scripts/manage-skills.sh install commit-msg

# 安装所有 Skill
bash scripts/manage-skills.sh install --all

# 卸载指定 Skill
bash scripts/manage-skills.sh uninstall commit-msg

# 卸载所有 Skill
bash scripts/manage-skills.sh uninstall --all

# 查看已安装状态
bash scripts/manage-skills.sh status
```

**注意**：

- 安装后的 Skill 不会自动更新，需手动重新安装以同步最新版本
- 脚本通过查找 `SKILL.md` 文件自动定位 Skill 目录

## 目录结构

```
agent-skills/
├── README.md              # 仓库主说明
├── AGENTS.md              # 智能体和用户指南
├── .githooks/             # Git Hook
│   └── pre-push
├── scripts/               # 工具脚本
│   ├── setup.sh                   # 环境初始化脚本（检查+配置）
│   ├── manage-skills.sh           # Skill 安装/卸载管理
│   └── validate-structure.sh      # 目录结构验证
├── docs/                  # 技术设计文档
│   └── 2025-01-18-repo-structure/
└── plugins/               # 插件集合
    └── [插件名称]/        # 例如 qa-test
        ├── README.md      # 必填：插件说明
        └── skills/        # 必填：技能目录
            └── [技能]/    # 例如 test-case-generate
                └── SKILL.md  # 必填：Skill 行为规范
                ├── examples/    # 可选：示例
                └── references/  # 可选：参考文档
```

## Git Hook

本仓库使用 `.githooks/` 目录管理 Git Hook，在 `git push` 时自动检查目录结构规范。

首次使用或需要验证环境时，运行：

```bash
source scripts/setup.sh
```

## 文档索引

- [README.md](./README.md) - 仓库说明
- [AGENTS.md](./AGENTS.md) - 使用与贡献指南
